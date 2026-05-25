"""Pydantic schemas shared across agents and (later) API routes.

Each agent module re-exports the schemas it produces, but they are defined
here so a single import site (`from app.schemas import ...`) is sufficient
for downstream consumers (FastAPI routes, tests, the React type generator).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AIDEResult(BaseModel):
    """Output of the AIDE mixture-of-experts deepfake detector."""

    score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Probability of AI generation (0.0–1.0). -1.0 indicates failure.",
    )
    success: bool
    error: Optional[str] = None


class ForensicMaps(BaseModel):
    """In-memory references to the three OpenCV forensic visualizations.

    Stored as base64-encoded PNG so they can be returned over JSON without
    a separate artifact endpoint. The orchestrator may swap this for URLs
    once a media-storage layer exists.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    noise_png_b64: str
    edge_png_b64: str
    ela_png_b64: str


class OpenCVComments(BaseModel):
    noise: str
    edges: str
    compression: str


class OpenCVResult(BaseModel):
    maps: ForensicMaps
    comments: OpenCVComments


GenAITool = Literal["Google AI", "OpenAI", "Kakao", "ElevenLabs", "Others", "Unknown"]


class SynthIDResult(BaseModel):
    is_ai: Optional[bool] = Field(
        default=None,
        description="Gemini's overall AI/real verdict; None if analysis failed.",
    )
    confidence: float = 0.0
    reasoning: str = ""
    synth_id_detected: bool = False
    watermark_found: bool = False
    gen_ai_tool: GenAITool = Field(
        default="Unknown",
        description="Detected generative-AI source, inferred from SynthID "
        "partner watermarks or visual/metadata analysis.",
    )


MediaType = Literal["image", "video", "audio", "text", "unknown", "none"]
RouterAction = Literal["deepfake_analysis", "follow_up", "small_talk", "other"]


class RouterResult(BaseModel):
    media_type: MediaType
    action: RouterAction
    reasoning: str = ""
    router: str = ""


class GreetingResult(BaseModel):
    text: str
    success: bool = True


class EvalResult(BaseModel):
    text: str
    success: bool = True
    error: Optional[str] = None


class SHAPResult(BaseModel):
    """SHAP heatmap rendered as a base64-encoded PNG."""

    heatmap_png_b64: str
    max_evals: int
    success: bool = True
    error: Optional[str] = None


class ObjectClassificationResult(BaseModel):
    media_type: str
    filename: str


class ConflictSeverity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class ConflictResult(BaseModel):
    has_conflict:        bool
    severity:            Optional[ConflictSeverity]                                  = None
    conflicting_signals: list[str]                                                   = []
    rule_triggered:      Optional[str]                                               = None
    reason:              Optional[str]                                               = None
    action_required:     Optional[Literal["proceed", "human_review", "reclassify"]] = None
    confidence_gap:      Optional[float]                                             = None
