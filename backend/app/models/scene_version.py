from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class SceneVersion(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "scene_versions"

    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    manim_code: Mapped[str] = mapped_column(Text, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    style_preset: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    max_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False, default="16:9")

    scene = relationship("Scene", back_populates="versions")

