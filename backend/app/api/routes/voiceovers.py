import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.asset import Asset
from app.models.project import Project
from app.models.user import User
from app.schemas.voiceover import VoiceoverTTSRequest, VoiceoverTTSResponse
from app.services.object_store import upload as object_store_upload
from app.services.rate_limit import assert_daily_asset_quota, check_burst
from app.services.storage import ensure_job_dir, sha256_file, to_storage_path
from app.services.tts import synthesize_tts

router = APIRouter()

try:
    import python_multipart  # noqa: F401

    MULTIPART_ENABLED = True
except Exception:  # noqa: BLE001
    MULTIPART_ENABLED = False


@router.post("/tts", response_model=VoiceoverTTSResponse, status_code=status.HTTP_201_CREATED)
def tts_voiceover(
    payload: VoiceoverTTSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoiceoverTTSResponse:
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    check_burst(current_user.id, "tts", max_per_minute=3)
    assert_daily_asset_quota(db, current_user.id, asset_type="audio_tts", daily_max=20)

    tmp_dir = ensure_job_dir(f"tts-{project.id}")
    output_path = tmp_dir / f"{current_user.id}-{project.id}-{uuid.uuid4().hex[:8]}.mp3"
    synthesize_tts(text=payload.text, voice=payload.voice, output_path=output_path)
    object_store_upload(output_path)

    asset = Asset(
        user_id=current_user.id,
        project_id=project.id,
        scene_id=None,
        composition_id=None,
        render_job_id=None,
        asset_type="audio_tts",
        mime_type="audio/mpeg",
        storage_path=to_storage_path(output_path),
        duration_ms=0,
        checksum_sha256=sha256_file(output_path),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return VoiceoverTTSResponse(
        asset_id=asset.id,
        storage_path=asset.storage_path,
        mime_type=asset.mime_type,
        duration_ms=asset.duration_ms,
    )


if MULTIPART_ENABLED:
    @router.post("/upload", response_model=VoiceoverTTSResponse, status_code=status.HTTP_201_CREATED)
    def upload_voiceover(
        project_id: str,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> VoiceoverTTSResponse:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == current_user.id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        assert_daily_asset_quota(db, current_user.id, asset_type="audio_upload", daily_max=50)

        suffix = Path(file.filename or "voiceover.wav").suffix or ".wav"
        output_dir = ensure_job_dir(f"upload-{project.id}")
        output_path = output_dir / f"{current_user.id}-{project.id}-{uuid.uuid4().hex[:8]}{suffix}"
        content = file.file.read()
        output_path.write_bytes(content)
        object_store_upload(output_path)

        asset = Asset(
            user_id=current_user.id,
            project_id=project.id,
            scene_id=None,
            composition_id=None,
            render_job_id=None,
            asset_type="audio_upload",
            mime_type=file.content_type or "audio/wav",
            storage_path=to_storage_path(output_path),
            duration_ms=0,
            checksum_sha256=sha256_file(output_path),
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        return VoiceoverTTSResponse(
            asset_id=asset.id,
            storage_path=asset.storage_path,
            mime_type=asset.mime_type,
            duration_ms=asset.duration_ms,
        )
else:
    @router.post("/upload", response_model=VoiceoverTTSResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
    def upload_voiceover_unavailable(
        project_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> VoiceoverTTSResponse:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Voiceover upload unavailable: python-multipart is not installed",
        )
