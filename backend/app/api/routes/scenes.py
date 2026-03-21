from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.project import Project
from app.models.render_job import RenderJob
from app.models.scene import Scene
from app.models.scene_version import SceneVersion
from app.models.user import User
from app.schemas.job import QueueJobResponse
from app.schemas.scene import (
    SceneGenerateRequest,
    SceneGenerateResponse,
    SceneRegenerateRequest,
    SceneRefineRequest,
)
from app.services.presets import list_presets
from app.services.rate_limit import assert_daily_render_quota, check_burst
from app.services.repair import generate_with_repair
from app.services.groq_adapter import refine_manim_code
from app.services.manim_validator import validate_manim_code
from app.workers.celery_app import celery_app

router = APIRouter()


@router.get("/presets")
def get_presets() -> list[dict]:
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "description": p.description,
        }
        for p in list_presets()
    ]




def _latest_version_no(db: Session, scene_id: str) -> int:
    value = db.query(func.max(SceneVersion.version_no)).filter(SceneVersion.scene_id == scene_id).scalar()
    return int(value or 0)


def _enqueue_preview_job(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    scene_id: str,
) -> RenderJob:
    job = RenderJob(
        user_id=user_id,
        project_id=project_id,
        scene_id=scene_id,
        job_type="preview",
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    celery_app.send_task(
        "app.workers.tasks.render_preview_job",
        args=[job.id],
        queue="preview",
    )
    return job


@router.post("/generate", response_model=SceneGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_scene(
    payload: SceneGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SceneGenerateResponse:
    settings = get_settings()
    check_burst(current_user.id, "scene_generate", max_per_minute=5)
    assert_daily_render_quota(db, current_user.id, job_type="preview", daily_max=50)

    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if payload.max_duration_sec > settings.max_scene_duration_sec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duration exceeds limit")

    next_order = db.query(func.count(Scene.id)).filter(Scene.project_id == project.id).scalar() or 0
    scene = Scene(project_id=project.id, title=f"Scene {next_order + 1}", order_index=int(next_order))
    db.add(scene)
    db.flush()

    repair = generate_with_repair(prompt=payload.prompt, style_preset=payload.style_preset, max_attempts=3, llm_provider=payload.llm_provider, max_duration_sec=payload.max_duration_sec)
    version = SceneVersion(
        scene_id=scene.id,
        version_no=1,
        prompt=payload.prompt,
        manim_code=repair.code,
        validation_status="valid" if repair.validation.ok else "invalid",
        error_log=repair.validation.error,
        style_preset=payload.style_preset,
        max_duration_sec=payload.max_duration_sec,
        aspect_ratio=payload.aspect_ratio,
    )
    db.add(version)
    db.commit()
    db.refresh(scene)
    db.refresh(version)

    preview_job = _enqueue_preview_job(db, user_id=current_user.id, project_id=project.id, scene_id=scene.id)
    return SceneGenerateResponse(
        scene_id=scene.id,
        scene_version_id=version.id,
        preview_job_id=preview_job.id,
        validation_status=version.validation_status,
    )


@router.post("/{scene_id}/regenerate", response_model=SceneGenerateResponse)
def regenerate_scene(
    scene_id: str,
    payload: SceneRegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SceneGenerateResponse:
    check_burst(current_user.id, "scene_regenerate", max_per_minute=5)
    assert_daily_render_quota(db, current_user.id, job_type="preview", daily_max=50)
    scene = (
        db.query(Scene)
        .join(Project, Project.id == Scene.project_id)
        .filter(Scene.id == scene_id, Project.user_id == current_user.id)
        .first()
    )
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    version_no = _latest_version_no(db, scene.id) + 1
    repair = generate_with_repair(prompt=payload.prompt, style_preset=payload.style_preset, max_attempts=3, llm_provider=getattr(payload, "llm_provider", None), max_duration_sec=payload.max_duration_sec)
    version = SceneVersion(
        scene_id=scene.id,
        version_no=version_no,
        prompt=payload.prompt,
        manim_code=repair.code,
        validation_status="valid" if repair.validation.ok else "invalid",
        error_log=repair.validation.error,
        style_preset=payload.style_preset,
        max_duration_sec=payload.max_duration_sec,
        aspect_ratio=payload.aspect_ratio,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    preview_job = _enqueue_preview_job(db, user_id=current_user.id, project_id=scene.project_id, scene_id=scene.id)
    return SceneGenerateResponse(
        scene_id=scene.id,
        scene_version_id=version.id,
        preview_job_id=preview_job.id,
        validation_status=version.validation_status,
    )


@router.post("/{scene_id}/refine", response_model=SceneGenerateResponse)
def refine_scene(
    scene_id: str,
    payload: SceneRefineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SceneGenerateResponse:
    check_burst(current_user.id, "scene_regenerate", max_per_minute=5)
    assert_daily_render_quota(db, current_user.id, job_type="preview", daily_max=50)
    scene = (
        db.query(Scene)
        .join(Project, Project.id == Scene.project_id)
        .filter(Scene.id == scene_id, Project.user_id == current_user.id)
        .first()
    )
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Get the latest version's code to refine
    latest = (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id == scene_id)
        .order_by(SceneVersion.version_no.desc())
        .first()
    )
    if not latest:
        raise HTTPException(status_code=404, detail="No scene version found")

    refined_code = refine_manim_code(
        existing_code=latest.manim_code,
        feedback=payload.feedback,
        llm_provider=payload.llm_provider,
    )
    validation = validate_manim_code(refined_code)
    version_no = _latest_version_no(db, scene.id) + 1
    version = SceneVersion(
        scene_id=scene.id,
        version_no=version_no,
        prompt=latest.prompt,
        manim_code=refined_code,
        validation_status="valid" if validation.ok else "invalid",
        error_log=validation.error,
        style_preset=latest.style_preset,
        max_duration_sec=latest.max_duration_sec,
        aspect_ratio=latest.aspect_ratio,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    preview_job = _enqueue_preview_job(db, user_id=current_user.id, project_id=scene.project_id, scene_id=scene.id)
    return SceneGenerateResponse(
        scene_id=scene.id,
        scene_version_id=version.id,
        preview_job_id=preview_job.id,
        validation_status=version.validation_status,
    )


@router.post("/{scene_id}/render-hd", response_model=QueueJobResponse, status_code=status.HTTP_202_ACCEPTED)
def render_hd(
    scene_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueueJobResponse:
    check_burst(current_user.id, "render_hd", max_per_minute=3)
    assert_daily_render_quota(db, current_user.id, job_type="hd", daily_max=30)
    scene = (
        db.query(Scene)
        .join(Project, Project.id == Scene.project_id)
        .filter(Scene.id == scene_id, Project.user_id == current_user.id)
        .first()
    )
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    job = RenderJob(
        user_id=current_user.id,
        project_id=scene.project_id,
        scene_id=scene.id,
        job_type="hd",
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    celery_app.send_task(
        "app.workers.tasks.render_hd_job",
        args=[job.id],
        queue="export",
    )
    return QueueJobResponse(job_id=job.id, status=job.status)
