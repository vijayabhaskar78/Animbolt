from datetime import datetime

from pydantic import BaseModel, Field


class SceneGenerateRequest(BaseModel):
    project_id: str
    prompt: str = Field(min_length=3, max_length=4000)
    style_preset: str = Field(default="default", max_length=64)
    max_duration_sec: int = Field(default=30, ge=1, le=60)
    aspect_ratio: str = Field(default="16:9", pattern=r"^\d+:\d+$")
    llm_provider: str | None = Field(default=None, description="Override LLM: 'groq' or 'ollama'")


class SceneRegenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)
    style_preset: str = Field(default="default", max_length=64)
    max_duration_sec: int = Field(default=30, ge=1, le=60)
    aspect_ratio: str = Field(default="16:9", pattern=r"^\d+:\d+$")


class SceneRefineRequest(BaseModel):
    feedback: str = Field(min_length=5, max_length=1000)
    llm_provider: str | None = Field(default=None, description="Override LLM: 'groq' or 'ollama'")


class SceneVersionResponse(BaseModel):
    id: str
    scene_id: str
    version_no: int
    prompt: str
    manim_code: str
    validation_status: str
    error_log: str
    style_preset: str
    max_duration_sec: int
    aspect_ratio: str
    created_at: datetime


class SceneResponse(BaseModel):
    id: str
    title: str
    order_index: int
    created_at: datetime
    versions: list[SceneVersionResponse]
    thumbnail_path: str | None = None
    video_preview_path: str | None = None


class SceneGenerateResponse(BaseModel):
    scene_id: str
    scene_version_id: str
    preview_job_id: str
    validation_status: str

