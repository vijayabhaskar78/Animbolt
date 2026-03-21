try:
    from celery import Celery
except Exception:  # noqa: BLE001
    class Celery:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            self.conf = {}

        def conf_update(self, **kwargs):  # type: ignore[no-untyped-def]
            self.conf.update(kwargs)

        def send_task(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cursor2d",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

if hasattr(celery_app.conf, "update"):
    celery_app.conf.update(
        task_track_started=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        worker_prefetch_multiplier=1,
        # Use solo pool by default — avoids prefork spawn issues on Windows + Python 3.13
        worker_pool="solo",
        broker_connection_retry_on_startup=True,
        task_routes={
            "app.workers.tasks.render_preview_job": {"queue": "preview"},
            "app.workers.tasks.render_hd_job": {"queue": "export"},
            "app.workers.tasks.export_composition_job": {"queue": "export"},
        },
    )
