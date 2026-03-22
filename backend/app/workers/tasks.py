import base64
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from celery import shared_task
except Exception:  # noqa: BLE001
    class _DummyRequest:
        def retry(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("Retry not available without Celery installed")

    class _DummyTask:
        def __init__(self, fn, bind: bool):
            self._fn = fn
            self._bind = bind

        def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            if self._bind:
                return self._fn(_DummyRequest(), *args, **kwargs)
            return self._fn(*args, **kwargs)

        def delay(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self.__call__(*args, **kwargs)

    def shared_task(*dargs, **dkwargs):  # type: ignore[no-untyped-def]
        bind = bool(dkwargs.get("bind", False))

        def decorator(fn):
            return _DummyTask(fn, bind=bind)

        return decorator

from sqlalchemy import and_

from app.core.config import get_settings
from app.db import session as _db_session
from app.models import asset, chat_message, composition, project, render_job, scene, scene_version, user  # noqa: F401
from app.models.asset import Asset
from app.models.composition import Composition
from app.models.project import Project
from app.models.render_job import RenderJob
from app.models.scene import Scene
from app.models.scene_version import SceneVersion
from app.services.preview_events import publish_preview_event
from app.services.object_store import upload as object_store_upload
from app.services.rendering import concat_videos, extract_frames, extract_thumbnail, merge_audio_video, run_render
from app.services.storage import ensure_job_dir, sha256_file, to_storage_path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _job_or_none(db, job_id: str) -> RenderJob | None:
    return db.query(RenderJob).filter(RenderJob.id == job_id).first()


def _start_job(job: RenderJob) -> None:
    job.status = "running"
    job.started_at = _now()
    job.attempt = (job.attempt or 0) + 1


def _finish_job(job: RenderJob, metrics: dict | None = None) -> None:
    job.status = "completed"
    job.finished_at = _now()
    job.metrics = metrics or {}


def _fail_job(job: RenderJob, error: str) -> None:
    job.status = "failed"
    job.finished_at = _now()
    job.error_message = error[:4000]


def _create_asset(
    db,
    *,
    user_id: str,
    project_id: str | None,
    scene_id: str | None,
    composition_id: str | None,
    render_job_id: str,
    asset_type: str,
    mime_type: str,
    path: Path,
    duration_ms: int = 0,
) -> Asset:
    new_asset = Asset(
        user_id=user_id,
        project_id=project_id,
        scene_id=scene_id,
        composition_id=composition_id,
        render_job_id=render_job_id,
        asset_type=asset_type,
        mime_type=mime_type,
        storage_path=to_storage_path(path),
        duration_ms=duration_ms,
        checksum_sha256=sha256_file(path),
    )
    db.add(new_asset)
    return new_asset


def _latest_scene_version(db, scene_id: str) -> SceneVersion | None:
    return (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id == scene_id)
        .order_by(SceneVersion.version_no.desc())
        .first()
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def render_preview_job(self, job_id: str) -> None:
    db = _db_session.SessionLocal()
    try:
        job = _job_or_none(db, job_id)
        if not job:
            return
        _start_job(job)
        db.commit()

        if not job.scene_id:
            raise ValueError("preview job missing scene_id")
        version = _latest_scene_version(db, job.scene_id)
        if not version:
            raise ValueError("missing scene version")

        job_dir = ensure_job_dir(job.id)
        script_path = job_dir / "generated_scene.py"
        preview_path = job_dir / "preview.mp4"
        script_path.write_text(version.manim_code, encoding="utf-8")

        start = time.time()
        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 5, "message": "Rendering preview"})
        run_render(script_path=script_path, output_path=preview_path, hd=False)

        # Extract real frames from the rendered video and stream them.
        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 80, "message": "Extracting preview frames"})
        frames_dir = job_dir / "frames"
        frame_paths = extract_frames(preview_path, frames_dir, n_frames=20)
        total_frames = len(frame_paths)
        for frame_idx, frame_path in enumerate(frame_paths):
            pct = 80 + int((frame_idx + 1) / max(total_frames, 1) * 12)
            frame_b64 = base64.b64encode(frame_path.read_bytes()).decode()
            event = {
                "job_id": job.id,
                "frame_index": frame_idx,
                "timestamp_ms": frame_idx * 66,
                "mime_type": "image/png",
                "progress_pct": pct,
                "payload_base64": frame_b64,
            }
            publish_preview_event(job.id, event)
            time.sleep(0.05)
        object_store_upload(preview_path)
        _create_asset(
            db,
            user_id=job.user_id,
            project_id=job.project_id,
            scene_id=job.scene_id,
            composition_id=None,
            render_job_id=job.id,
            asset_type="video_preview",
            mime_type="video/mp4",
            path=preview_path,
        )

        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 95, "message": "Generating thumbnail"})
        thumbnail_path = job_dir / "thumbnail.png"
        extract_thumbnail(preview_path, thumbnail_path)
        if thumbnail_path.exists():
            object_store_upload(thumbnail_path)
            _create_asset(
                db,
                user_id=job.user_id,
                project_id=job.project_id,
                scene_id=job.scene_id,
                composition_id=None,
                render_job_id=job.id,
                asset_type="thumbnail",
                mime_type="image/png",
                path=thumbnail_path,
            )

        elapsed_ms = int((time.time() - start) * 1000)
        _finish_job(job, metrics={"frames_streamed": total_frames, "real_frames": total_frames > 0, "elapsed_ms": elapsed_ms, "progress_pct": 100})
        db.commit()
        publish_preview_event(job.id, {"job_id": job.id, "type": "completed", "progress_pct": 100})
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = _job_or_none(db, job_id)
        if job:
            _fail_job(job, str(exc))
            db.commit()
            publish_preview_event(job.id, {"job_id": job.id, "type": "failed", "error": str(exc)})
        raise self.retry(exc=exc)
    finally:
        db.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def render_hd_job(self, job_id: str) -> None:
    db = _db_session.SessionLocal()
    try:
        job = _job_or_none(db, job_id)
        if not job:
            return
        _start_job(job)
        db.commit()

        if not job.scene_id:
            raise ValueError("hd job missing scene_id")
        version = _latest_scene_version(db, job.scene_id)
        if not version:
            raise ValueError("missing scene version")

        job_dir = ensure_job_dir(job.id)
        script_path = job_dir / "generated_scene.py"
        output_path = job_dir / "hd.mp4"
        script_path.write_text(version.manim_code, encoding="utf-8")

        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 10, "message": "Rendering at 720p"})
        run_render(script_path=script_path, output_path=output_path, hd=True)
        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 85, "message": "Uploading asset"})
        object_store_upload(output_path)
        _create_asset(
            db,
            user_id=job.user_id,
            project_id=job.project_id,
            scene_id=job.scene_id,
            composition_id=None,
            render_job_id=job.id,
            asset_type="video_hd",
            mime_type="video/mp4",
            path=output_path,
        )
        _finish_job(job, metrics={"quality": "720p", "progress_pct": 100})
        db.commit()
        publish_preview_event(job.id, {"job_id": job.id, "type": "completed", "progress_pct": 100})
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = _job_or_none(db, job_id)
        if job:
            _fail_job(job, str(exc))
            db.commit()
            publish_preview_event(job.id, {"job_id": job.id, "type": "failed", "error": str(exc)})
        raise self.retry(exc=exc)
    finally:
        db.close()


def _latest_scene_video_asset(db, scene_id: str) -> Asset | None:
    return (
        db.query(Asset)
        .filter(
            and_(
                Asset.scene_id == scene_id,
                Asset.asset_type.in_(["video_hd", "video_preview"]),
            )
        )
        .order_by(Asset.created_at.desc())
        .first()
    )


def _latest_project_audio(db, project_id: str) -> Asset | None:
    return (
        db.query(Asset)
        .filter(and_(Asset.project_id == project_id, Asset.asset_type.in_(["audio_tts", "audio_upload"])))
        .order_by(Asset.created_at.desc())
        .first()
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def export_composition_job(self, job_id: str) -> None:
    db = _db_session.SessionLocal()
    try:
        job = _job_or_none(db, job_id)
        if not job:
            return
        _start_job(job)
        db.commit()

        if not job.project_id:
            raise ValueError("export job missing project_id")
        project = db.query(Project).filter(Project.id == job.project_id).first()
        if not project:
            raise ValueError("project not found")

        scenes = db.query(Scene).filter(Scene.project_id == project.id).order_by(Scene.order_index.asc()).all()
        scene_videos: list[Path] = []
        settings = get_settings()
        n_scenes = len(scenes)
        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 5, "message": f"Collecting {n_scenes} scene(s)"})
        for idx, sc in enumerate(scenes):
            vid_asset = _latest_scene_video_asset(db, sc.id)
            if vid_asset:
                scene_videos.append(settings.artifacts_dir / vid_asset.storage_path)
            pct = 10 + int((idx + 1) / max(n_scenes, 1) * 50)
            publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": pct, "message": f"Loaded scene {idx + 1}/{n_scenes}"})

        job_dir = ensure_job_dir(job.id)
        composed_path = job_dir / "composed.mp4"
        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 65, "message": "Concatenating videos"})
        concat_videos(scene_videos, composed_path)

        audio = _latest_project_audio(db, project.id)
        final_path = job_dir / "final.mp4"
        if audio:
            publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 80, "message": "Merging audio"})
            merge_audio_video(
                video_path=composed_path,
                audio_path=settings.artifacts_dir / audio.storage_path,
                output_path=final_path,
            )
            output = final_path
        else:
            output = composed_path

        publish_preview_event(job.id, {"job_id": job.id, "type": "progress", "progress_pct": 90, "message": "Uploading export"})
        object_store_upload(output)
        _create_asset(
            db,
            user_id=job.user_id,
            project_id=project.id,
            scene_id=None,
            composition_id=job.composition_id,
            render_job_id=job.id,
            asset_type="video_export",
            mime_type="video/mp4",
            path=output,
        )
        _finish_job(job, metrics={"scene_count": len(scene_videos), "audio_attached": bool(audio), "progress_pct": 100})
        db.commit()
        publish_preview_event(job.id, {"job_id": job.id, "type": "completed", "progress_pct": 100})
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = _job_or_none(db, job_id)
        if job:
            _fail_job(job, str(exc))
            db.commit()
            publish_preview_event(job.id, {"job_id": job.id, "type": "failed", "error": str(exc)})
        raise self.retry(exc=exc)
    finally:
        db.close()
