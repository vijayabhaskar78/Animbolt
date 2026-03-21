"""
Rate-limiting helpers.

Burst limits  — Redis INCR/EXPIRE per (user, action, minute).
Daily limits  — DB COUNT per (user, action type, UTC day).

Both degrade gracefully: if Redis is unreachable the burst check is skipped;
if the DB query fails the daily check raises a plain 500.

Usage
-----
from app.services.rate_limit import check_burst, assert_daily_render_quota, assert_daily_asset_quota

check_burst(user_id, "scene_generate", max_per_minute=5)
assert_daily_render_quota(db, user_id, job_type="preview", daily_max=50)
assert_daily_asset_quota(db, user_id, asset_type="audio_tts", daily_max=20)
"""
import time
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# Burst limiter (Redis-backed)
# ---------------------------------------------------------------------------

def check_burst(user_id: str, action: str, max_per_minute: int) -> None:
    """
    Raise HTTP 429 if the user has exceeded *max_per_minute* requests for
    *action* within the current clock-minute window.

    Silently skips the check when Redis is unavailable.
    """
    settings = get_settings()
    minute_bucket = int(time.time()) // 60
    key = f"rl:{user_id}:{action}:{minute_bucket}"
    try:
        from redis import Redis
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        try:
            count = client.incr(key)
            if count == 1:
                # 90 s covers the full minute plus a little boundary slack.
                client.expire(key, 90)
        finally:
            client.close()

        if count > max_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Burst limit exceeded: max {max_per_minute} "
                    f"'{action}' requests per minute. Please slow down."
                ),
            )
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        # Redis unavailable — skip the check rather than blocking the user.
        pass


# ---------------------------------------------------------------------------
# Daily quota helpers (DB-backed)
# ---------------------------------------------------------------------------

def _utc_day_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def assert_daily_render_quota(
    db: Session,
    user_id: str,
    job_type: str,
    daily_max: int,
) -> None:
    """
    Raise HTTP 429 if the user has created >= *daily_max* RenderJobs of
    *job_type* today (UTC).
    """
    from app.models.render_job import RenderJob

    day_start = _utc_day_start()
    count = (
        db.query(func.count(RenderJob.id))
        .filter(
            and_(
                RenderJob.user_id == user_id,
                RenderJob.job_type == job_type,
                RenderJob.created_at >= day_start,
            )
        )
        .scalar()
    ) or 0

    if count >= daily_max:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily quota reached: max {daily_max} '{job_type}' jobs per day.",
        )


def assert_daily_asset_quota(
    db: Session,
    user_id: str,
    asset_type: str,
    daily_max: int,
) -> None:
    """
    Raise HTTP 429 if the user has created >= *daily_max* Assets of
    *asset_type* today (UTC).
    """
    from app.models.asset import Asset

    day_start = _utc_day_start()
    count = (
        db.query(func.count(Asset.id))
        .filter(
            and_(
                Asset.user_id == user_id,
                Asset.asset_type == asset_type,
                Asset.created_at >= day_start,
            )
        )
        .scalar()
    ) or 0

    if count >= daily_max:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily quota reached: max {daily_max} '{asset_type}' operations per day.",
        )


# ---------------------------------------------------------------------------
# Usage summary (for the /usage endpoint)
# ---------------------------------------------------------------------------

def get_usage_summary(db: Session, user_id: str) -> dict:
    """Return today's usage counts and limits for all tracked actions."""
    from app.models.asset import Asset
    from app.models.render_job import RenderJob

    day_start = _utc_day_start()

    def _job_count(job_type: str) -> int:
        return (
            db.query(func.count(RenderJob.id))
            .filter(
                and_(
                    RenderJob.user_id == user_id,
                    RenderJob.job_type == job_type,
                    RenderJob.created_at >= day_start,
                )
            )
            .scalar()
        ) or 0

    def _asset_count(asset_type: str) -> int:
        return (
            db.query(func.count(Asset.id))
            .filter(
                and_(
                    Asset.user_id == user_id,
                    Asset.asset_type == asset_type,
                    Asset.created_at >= day_start,
                )
            )
            .scalar()
        ) or 0

    return {
        "preview_renders": {"used": _job_count("preview"), "limit": 50},
        "hd_renders": {"used": _job_count("hd"), "limit": 30},
        "exports": {"used": _job_count("export"), "limit": 15},
        "tts_generations": {"used": _asset_count("audio_tts"), "limit": 20},
        "voiceover_uploads": {"used": _asset_count("audio_upload"), "limit": 50},
        "reset": "UTC midnight",
    }
