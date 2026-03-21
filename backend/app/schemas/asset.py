from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    asset_type: str
    mime_type: str
    storage_path: str
    duration_ms: int
    checksum_sha256: str

