"""
Object store abstraction for asset files.

When S3_BUCKET is set in config, files are uploaded to S3 (or any S3-compatible
endpoint such as MinIO/R2) and served via presigned redirect URLs.

When S3_BUCKET is empty (default), files stay on local disk and are served by
FastAPI's StaticFiles mount at /artifacts/.
"""
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError as _ClientError  # noqa: F401
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False

from app.core.config import get_settings
from app.services.storage import to_storage_path


def is_configured() -> bool:
    """Return True when S3 upload/redirect is active."""
    return bool(get_settings().s3_bucket) and _BOTO3_AVAILABLE


def _client():
    settings = get_settings()
    kwargs: dict = {
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "region_name": settings.aws_region,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)  # type: ignore[attr-defined]


def upload(local_path: Path) -> None:
    """
    Upload *local_path* to S3 using the storage-path as the S3 key.
    No-ops silently when S3 is not configured or boto3 is unavailable.
    """
    if not is_configured():
        return
    key = to_storage_path(local_path)
    try:
        _client().upload_file(str(local_path), get_settings().s3_bucket, key)
    except Exception:  # noqa: BLE001
        # Degrade gracefully — local file still exists for direct serving.
        pass


def get_presigned_url(key: str, expires_in: int = 3600) -> str | None:
    """
    Return a URL for *key*. Uses direct public URL when s3_public_base_url is set,
    otherwise falls back to a presigned URL. Returns None when S3 is not configured.
    """
    if not is_configured():
        return None
    settings = get_settings()
    # Public bucket — return direct URL (no expiry, no signing overhead)
    if settings.s3_public_base_url:
        return f"{settings.s3_public_base_url.rstrip('/')}/{key}"
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception:  # noqa: BLE001
        return None
