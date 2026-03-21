from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Project(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    user = relationship("User", back_populates="projects")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")
    compositions = relationship("Composition", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("RenderJob", back_populates="project")
    assets = relationship("Asset", back_populates="project")
    chat_messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")

