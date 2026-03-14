from pydantic import BaseModel, Field
from app.models.common import QCScore

class VideoQCDimension(BaseModel):
    score: int = Field(ge=0, le=10)
    reasoning: str

class VideoQCReport(BaseModel):
    """Unified QC report with 7 scoring dimensions."""
    model_config = {"extra": "ignore"}

    technical_distortion: VideoQCDimension | None = None
    cinematic_imperfections: VideoQCDimension | None = None
    avatar_consistency: VideoQCDimension | None = None
    product_consistency: VideoQCDimension | None = None
    temporal_coherence: VideoQCDimension | None = None
    hand_body_integrity: VideoQCDimension | None = None
    brand_text_accuracy: VideoQCDimension | None = None
    overall_verdict: str = ""
    debate_log: list[dict] = []
