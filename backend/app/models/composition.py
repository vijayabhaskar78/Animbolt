from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Composition(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "compositions"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Main Composition")

    project = relationship("Project", back_populates="compositions")
    scene_links = relationship("CompositionScene", back_populates="composition", cascade="all, delete-orphan")
    jobs = relationship("RenderJob", back_populates="composition")
    assets = relationship("Asset", back_populates="composition")


class CompositionScene(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "composition_scenes"

    composition_id: Mapped[str] = mapped_column(String(36), ForeignKey("compositions.id"), nullable=False, index=True)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    composition = relationship("Composition", back_populates="scene_links")
    scene = relationship("Scene", back_populates="composition_links")

