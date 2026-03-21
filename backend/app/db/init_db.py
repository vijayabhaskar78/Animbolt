from app.db.base import Base
from app.db.session import engine
from app.models import asset, chat_message, composition, project, render_job, scene, scene_version, user  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

