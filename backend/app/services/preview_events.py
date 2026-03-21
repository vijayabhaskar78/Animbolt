import json
from typing import Any

from redis import Redis

from app.core.config import get_settings


def publish_preview_event(job_id: str, event: dict[str, Any]) -> None:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.publish(f"preview:{job_id}", json.dumps(event))
    finally:
        client.close()

