import asyncio
import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from app.api.router import api_router
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services import object_store

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


_in_prod = settings.environment == "production"
app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    # Disable interactive API docs in production — they expose all endpoints
    docs_url=None if _in_prod else "/docs",
    redoc_url=None if _in_prod else "/redoc",
    openapi_url=None if _in_prod else "/openapi.json",
)

_all_cors_origins = settings.cors_origins + [
    o.strip() for o in settings.extra_cors_origins.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if object_store.is_configured():
    @app.get("/artifacts/{path:path}", include_in_schema=False)
    async def serve_artifact_s3(path: str) -> RedirectResponse:
        url = object_store.get_presigned_url(path)
        if not url:
            raise HTTPException(status_code=404, detail="Asset not found")
        return RedirectResponse(url, status_code=302)
else:
    app.mount("/artifacts", StaticFiles(directory=settings.artifacts_dir), name="artifacts")


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.websocket("/ws/preview/{job_id}")
async def preview_ws(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()

    # If the job already completed, replay saved frames directly from disk.
    frames_dir = Path(settings.artifacts_dir) / job_id / "frames"
    if frames_dir.exists():
        frame_paths = sorted(frames_dir.glob("frame_*.png"))
        if frame_paths:
            total = len(frame_paths)
            try:
                for idx, fp in enumerate(frame_paths):
                    pct = 80 + int((idx + 1) / total * 12)
                    frame_b64 = base64.b64encode(fp.read_bytes()).decode()
                    await websocket.send_text(json.dumps({
                        "job_id": job_id,
                        "frame_index": idx,
                        "mime_type": "image/png",
                        "progress_pct": pct,
                        "payload_base64": frame_b64,
                    }))
                    await asyncio.sleep(0.05)
                await websocket.send_text(json.dumps({"type": "done", "job_id": job_id, "progress_pct": 100}))
            except WebSocketDisconnect:
                pass
            return

    # Live path: subscribe to Redis pub/sub while the job is still running.
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    channel_name = f"preview:{job_id}"
    await pubsub.subscribe(channel_name)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                payload = message["data"]
                if isinstance(payload, str):
                    await websocket.send_text(payload)
                else:
                    await websocket.send_text(json.dumps(payload))
            else:
                await websocket.send_text(json.dumps({"type": "heartbeat", "job_id": job_id}))
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.close()
        await redis.close()

