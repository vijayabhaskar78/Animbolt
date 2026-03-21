from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Scene(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "scenes"

    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    project = relationship("Project", back_populates="scenes")
    versions = relationship("SceneVersion", back_populates="scene", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="scene")
    composition_links = relationship("CompositionScene", back_populates="scene", cascade="all, delete-orphan")

