from pydantic import BaseModel, Field


class VoiceoverTTSRequest(BaseModel):
    project_id: str
    text: str = Field(min_length=1, max_length=5000)
    voice: str = Field(default="en-US-ChristopherNeural", max_length=64)


class VoiceoverTTSResponse(BaseModel):
    asset_id: str
    storage_path: str
    mime_type: str
    duration_ms: int

