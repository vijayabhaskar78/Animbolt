import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.asset import Asset
from app.models.project import Project
from app.models.scene import Scene
from app.models.user import User
from app.schemas.project import ProjectCreateRequest, ProjectDetailResponse, ProjectResponse, ReorderScenesRequest
from app.services.serializers import to_project_detail_response, to_project_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    project = Project(
        user_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return to_project_response(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [to_project_response(item) for item in projects]


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetailResponse:
    project = (
        db.query(Project)
        .options(
            joinedload(Project.scenes).joinedload(Scene.versions),
            joinedload(Project.scenes).joinedload(Scene.assets),
        )
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return to_project_detail_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    project = (
        db.query(Project)
        .options(
            joinedload(Project.scenes).joinedload(Scene.assets),
            joinedload(Project.assets),
        )
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Collect every asset file path before touching the DB
    artifacts_dir = get_settings().artifacts_dir
    paths_to_delete: list[Path] = []
    all_assets: list[Asset] = list(project.assets)
    for scene in project.scenes:
        all_assets.extend(scene.assets)
    for asset in all_assets:
        paths_to_delete.append(artifacts_dir / asset.storage_path)

    # Delete asset DB rows explicitly (no cascade defined on Asset relationships)
    for asset in all_assets:
        db.delete(asset)

    # Delete project — cascade removes scenes, versions, compositions
    db.delete(project)
    db.commit()

    # Remove files from disk (best-effort; never block the response)
    for path in paths_to_delete:
        try:
            if path.exists():
                path.unlink()
                logger.info("Deleted asset file: %s", path)
        except Exception as exc:
            logger.warning("Could not delete file %s: %s", path, exc)


@router.put("/{project_id}/reorder-scenes", response_model=ProjectDetailResponse)
def reorder_scenes(
    project_id: str,
    payload: ReorderScenesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetailResponse:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    scenes = db.query(Scene).filter(Scene.project_id == project.id).all()
    scene_map = {s.id: s for s in scenes}
    for new_idx, scene_id in enumerate(payload.scene_ids):
        if scene_id in scene_map:
            scene_map[scene_id].order_index = new_idx

    db.commit()

    # Re-query to return fresh data with all relationships.
    project = (
        db.query(Project)
        .options(
            joinedload(Project.scenes).joinedload(Scene.versions),
            joinedload(Project.scenes).joinedload(Scene.assets),
        )
        .filter(Project.id == project_id)
        .first()
    )
    return to_project_detail_response(project)
