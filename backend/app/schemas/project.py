from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.scene import SceneResponse


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""


class ReorderScenesRequest(BaseModel):
    scene_ids: list[str] = Field(min_length=1, description="Scene IDs in the desired order (first = order_index 0)")


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    created_at: datetime


class ProjectDetailResponse(ProjectResponse):
    scenes: list[SceneResponse]

