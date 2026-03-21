from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.asset import AssetResponse


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    attempt: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str
    metrics: dict[str, Any]
    assets: list[AssetResponse]


class QueueJobResponse(BaseModel):
    job_id: str
    status: str

