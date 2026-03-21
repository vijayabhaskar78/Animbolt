from pydantic import BaseModel, Field


class ExportCompositionRequest(BaseModel):
    title: str = Field(default="Main Composition", max_length=255)

