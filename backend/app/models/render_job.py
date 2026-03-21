from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class RenderJob(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "render_jobs"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenes.id"), nullable=True, index=True)
    composition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("compositions.id"),
        nullable=True,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    user = relationship("User", back_populates="jobs")
    project = relationship("Project", back_populates="jobs")
    composition = relationship("Composition", back_populates="jobs")
    assets = relationship("Asset", back_populates="render_job")

