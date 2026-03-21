from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.render_job import RenderJob
from app.models.user import User
from app.schemas.job import JobResponse
from app.services.serializers import to_job_response

router = APIRouter()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    job = (
        db.query(RenderJob)
        .options(joinedload(RenderJob.assets))
        .filter(RenderJob.id == job_id, RenderJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return to_job_response(job)

