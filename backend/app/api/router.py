from fastapi import APIRouter

from app.api.routes import auth, chat, compositions, jobs, projects, scenes, usage, voiceovers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(chat.router, prefix="/projects", tags=["chat"])
api_router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
api_router.include_router(voiceovers.router, prefix="/voiceovers", tags=["voiceovers"])
api_router.include_router(compositions.router, prefix="/compositions", tags=["compositions"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])

