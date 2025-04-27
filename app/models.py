
from pydantic import BaseModel, Field

class VideoRequest(BaseModel):
    video_id: str = Field(..., description="La URL o el ID del video de YouTube.", example="dQw4w9WgXcQ")

class TranscriptResponse(BaseModel):
    transcript: str
    language: str
    language_code: str
    is_generated: bool

class ErrorResponse(BaseModel):
    detail: str
