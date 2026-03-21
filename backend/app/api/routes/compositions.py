from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.composition import Composition, CompositionScene
from app.models.project import Project
from app.models.render_job import RenderJob
from app.models.scene import Scene
from app.models.user import User
from app.schemas.composition import ExportCompositionRequest
from app.schemas.job import QueueJobResponse
from app.services.rate_limit import assert_daily_render_quota, check_burst
from app.workers.celery_app import celery_app

router = APIRouter()


def _upsert_default_composition(db: Session, project: Project, title: str) -> Composition:
    composition = (
        db.query(Composition)
        .filter(Composition.project_id == project.id)
        .order_by(Composition.created_at.asc())
        .first()
    )
    if not composition:
        composition = Composition(project_id=project.id, title=title)
        db.add(composition)
        db.flush()
    else:
        composition.title = title

    db.query(CompositionScene).filter(CompositionScene.composition_id == composition.id).delete()
    scenes = db.query(Scene).filter(Scene.project_id == project.id).order_by(Scene.order_index.asc()).all()
    for idx, scene in enumerate(scenes):
        db.add(CompositionScene(composition_id=composition.id, scene_id=scene.id, order_index=idx))

    db.flush()
    return composition


@router.post("/{project_id}/export", response_model=QueueJobResponse, status_code=status.HTTP_202_ACCEPTED)
def export_project_composition(
    project_id: str,
    payload: ExportCompositionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueueJobResponse:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    check_burst(current_user.id, "export", max_per_minute=2)
    assert_daily_render_quota(db, current_user.id, job_type="export", daily_max=15)

    composition = _upsert_default_composition(db, project, payload.title)
    job = RenderJob(
        user_id=current_user.id,
        project_id=project.id,
        composition_id=composition.id,
        job_type="export",
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    celery_app.send_task(
        "app.workers.tasks.export_composition_job",
        args=[job.id],
        queue="export",
    )
    return QueueJobResponse(job_id=job.id, status=job.status)
