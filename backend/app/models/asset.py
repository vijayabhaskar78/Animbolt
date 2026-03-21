from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Asset(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True, index=True)
    scene_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenes.id"), nullable=True, index=True)
    composition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("compositions.id"),
        nullable=True,
        index=True,
    )
    render_job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("render_jobs.id"),
        nullable=True,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    user = relationship("User", back_populates="assets")
    project = relationship("Project", back_populates="assets")
    scene = relationship("Scene", back_populates="assets")
    composition = relationship("Composition", back_populates="assets")
    render_job = relationship("RenderJob", back_populates="assets")

