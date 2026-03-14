from pydantic import BaseModel, Field

from app.models.common import QCScore
from app.models.script import Scene
from app.models.qc import VideoQCDimension


class StoryboardRequest(BaseModel):
    run_id: str
    scenes: list[Scene]
    image_model: str | None = None
    aspect_ratio: str = "9:16"
    image_size: str = "2K"
    qc_threshold: int = Field(default=60, ge=0, le=100)
    max_regen_attempts: int = Field(default=3, ge=0, le=10)
    include_composition_qc: bool = True
    custom_prompts: dict[int, str] | None = None


class StoryboardQCReport(BaseModel):
    """Storyboard QC report aligned with Video QC 'War Room' schema."""
    model_config = {"extra": "ignore"}

    technical_distortion: VideoQCDimension | None = Field(default=None, alias="technical_distortion")
    cinematic_imperfections: VideoQCDimension | None = Field(default=None, alias="cinematic_imperfections")
    avatar_consistency: VideoQCDimension | None = Field(default=None, alias="avatar_consistency")
    product_consistency: VideoQCDimension | None = Field(default=None, alias="product_consistency")
    temporal_coherence: VideoQCDimension | None = Field(default=None, alias="temporal_coherence")
    hand_body_integrity: VideoQCDimension | None = Field(default=None, alias="hand_body_integrity")
    brand_text_accuracy: VideoQCDimension | None = Field(default=None, alias="brand_text_accuracy")
    overall_verdict: str = "PASS"
    debate_log: list[dict] = []

    # Backward compatibility fields (deprecated)
    avatar_validation: QCScore | None = None
    product_validation: QCScore | None = None
    composition_quality: QCScore | None = None


class StoryboardResult(BaseModel):
    scene_number: int
    image_path: str
    qc_report: StoryboardQCReport
    regen_attempts: int = 0
    prompt_used: str = ""


class StoryboardRegenRequest(BaseModel):
    run_id: str
    scene_number: int
    scene: Scene
    image_model: str | None = None
    aspect_ratio: str = "9:16"
    image_size: str = "2K"
    qc_threshold: int = Field(default=60, ge=0, le=100)
    max_regen_attempts: int = Field(default=3, ge=0, le=10)
    include_composition_qc: bool = True
    custom_prompt: str = ""


class StoryboardResponse(BaseModel):
    status: str = "success"
    results: list[StoryboardResult]
