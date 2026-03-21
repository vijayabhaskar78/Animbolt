import hashlib
from pathlib import Path

from app.core.config import get_settings


def ensure_job_dir(job_id: str) -> Path:
    settings = get_settings()
    path = settings.artifacts_dir / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def to_storage_path(path: Path) -> str:
    settings = get_settings()
    try:
        return str(path.relative_to(settings.artifacts_dir)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")
