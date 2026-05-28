"""SynthID watermark detection agent.

Sends the image to Gemini with a strict-JSON prompt asking for an AI/real
verdict, confidence, and SynthID/watermark presence flags. Falls back to
a sentinel result with ``is_ai = None`` when Gemini is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from ..schemas import SynthIDResult

logger = logging.getLogger(__name__)


_SYNTHID_PROMPT = (
    "You are a world-class forensic AI image analyst specialising in detecting AI-generated images. "
    "Your task is to determine whether this image was created by an AI system. "
    "Be rigorous, unbiased, and apply the most up-to-date knowledge of AI image generation capabilities.\n\n"

    "## ⚠️ CRITICAL ANTI-BIAS WARNINGS — READ BEFORE ANALYSING\n"
    "These are the most common mistakes analysts make. Avoid them:\n"
    "  1. **The Authenticity Fallacy**: Do NOT assume an image is real just because it looks realistic. "
    "Modern AI models (Gemini, DALL-E 3, Midjourney v6, Stable Diffusion XL) produce photorealistic images "
    "that are indistinguishable from photographs to the naked eye. Realism is NOT evidence of authenticity.\n"
    "  2. **The Perfect Text Fallacy**: Do NOT assume an image is authentic because the text is perfectly "
    "legible, correctly spelled, and logically placed. Modern AI (especially Google Gemini Image) has "
    "specifically solved text generation — perfect, readable text in an image is now a STRONG RED FLAG "
    "for AI generation, not a sign of authenticity. AI renders fonts with pixel-perfect consistency; "
    "real photos of printed documents show micro-variations in ink density, paper texture bleeding, "
    "and sub-pixel rendering artifacts.\n"
    "  3. **The Anatomy Fallacy**: Do NOT focus only on finger counts or facial features. These are "
    "old heuristics from 2022. Current AI handles human anatomy very well.\n"
    "  4. **The Conservative Bias**: Do NOT default to low confidence scores out of caution. "
    "If evidence leans toward AI, report that honestly with an appropriate high score.\n\n"

    "## STEP 1 — Watermark Detection (Highest Priority)\n"
    "Scan the image for ANY watermarks indicating AI generation. This includes:\n"
    "  1. **Visible Watermarks**: Look carefully at ALL corners (especially the bottom-right and bottom-left) "
    "for the Google Imagen/Gemini 'sparkle' icon (4-pointed star/asterisk), OpenAI DALL-E coloured "
    "square blocks, Adobe Firefly icon, Midjourney logo, or any AI tool text/logos.\n"
    "  2. **Invisible/Metadata Markers**: Note any signs of SynthID or other steganographic markers.\n"
    "If ANY watermark is detected, that is DEFINITIVE proof. Set synthIdDetected and watermarkFound to true.\n\n"

    "## STEP 2 — Document & Receipt Forensics (Critical for document images)\n"
    "If the image contains a document, receipt, bank statement, ID card, or any printed material, apply "
    "these SPECIFIC document forensics checks — these are HIGH-VALUE AI indicators:\n"
    "  - **Ink/print consistency**: Real thermal receipt paper has variations in ink darkness, "
    "smudging at edges, and slight misalignment. AI-generated receipts have perfectly uniform ink density.\n"
    "  - **Paper texture authenticity**: Real paper photographed up close shows fibre grain, "
    "micro-embossing, and ink bleed-through. AI paper looks smooth and uniform.\n"
    "  - **Font rendering**: Real photos of printed text show slight blur from camera depth-of-field, "
    "noise from JPEG compression, and ink spread. AI text is pixel-perfect with clean, sharp edges.\n"
    "  - **Logical coherence vs. suspicious perfection**: Real documents have minor imperfections "
    "(slight skew, uneven margins, practical formatting quirks). AI documents are suspiciously perfect.\n"
    "  - **Contextual plausibility**: Check if all values, codes, dates, and IDs are internally "
    "consistent and realistic (e.g. reference numbers matching expected formats for that bank/country).\n"
    "  - **Hand-document interaction**: In real photos, fingers casting shadows on paper create soft "
    "penumbra. AI-generated hand-document interaction often has too-clean shadow edges or mismatched "
    "grip/paper deformation.\n\n"

    "## STEP 3 — General Visual Artifact Analysis\n"
    "Also examine for standard AI-generation artifacts:\n"
    "  - **Texture over-smoothing**: Skin looks plastic, surfaces unnaturally uniform.\n"
    "  - **Lighting micro-inconsistencies**: Subtle mismatches between object highlights that suggest "
    "composite or synthetic illumination models rather than a single real light source.\n"
    "  - **Background coherence**: AI backgrounds often have unnaturally smooth bokeh, "
    "repeated texture tiles, or depth-of-field that doesn't follow optical physics.\n"
    "  - **Over-perfection paradox**: When EVERY element in a scene (skin, paper, wood grain, "
    "lighting, text) is simultaneously perfect with no flaws, that level of combined perfection "
    "is statistically implausible for a real photograph and is itself an AI indicator.\n"
    "  - **Wood/surface textures**: AI wood grain (e.g. tables) is often too regular and repeating.\n\n"

    "## STEP 4 — Source Attribution\n"
    "Based on watermark or style, categorize the likely generative source into exactly one of: "
    '"Google AI", "OpenAI", "Kakao", "ElevenLabs", "Others" (AI-generated but unknown), '
    'or "Unknown" (cannot be determined).\n\n'

    "## CONFIDENCE SCORING RULES\n"
    "The confidence value = probability (0.0–1.0) that the image IS AI-generated.\n\n"
    "**If a SynthID/AI watermark is confirmed (Step 1):** Set confidence = 0.99.\n\n"
    "**If NO watermark is found (Steps 2–3 — visual evaluation):** Perform a thorough assessment. "
    "Do NOT default to low scores. Base your score on the CUMULATIVE weight of all evidence:\n"
    "  - Strong indicators: perfect document text, over-perfection paradox across multiple elements, "
    "AI-style bokeh/lighting → score HIGH (0.70–0.98)\n"
    "  - Moderate indicators: some perfection cues but genuine photo characteristics also present "
    "→ score MEDIUM (0.40–0.69)\n"
    "  - Weak indicators: mostly looks like a real photo with minor ambiguities → score LOW (0.15–0.39)\n"
    "  - Virtually no indicators: strong evidence of being a real photo → score VERY LOW (0.02–0.14)\n"
    "IMPORTANT: A document image with perfectly legible, pixel-perfect text and flawless formatting "
    "should score at LEAST 0.65 even if you cannot find other artifacts, because modern AI "
    "specifically excels at this and real document photos rarely achieve this level of perfection.\n\n"

    "## EVIDENCE REQUIREMENT\n"
    "In your reasoning, cite SPECIFIC observations with precise locations "
    "(e.g. 'The thermal paper shows perfectly uniform ink density with no smudging at character edges', "
    "'The wood grain on the table repeats with a 47px tile pattern', "
    "'The hand shadow on the receipt has unnaturally sharp edges for ambient indoor lighting'). "
    "DO NOT use generic statements. DO NOT argue that good text quality proves authenticity.\n\n"

    "Return the result in this exact JSON format:\n"
    "{\n"
    '  "isAI": boolean,\n'
    '  "confidence": number,\n'
    '  "genAITool": string,\n'
    '  "reasoning": "specific evidence-backed explanation with precise location observations",\n'
    '  "metadata": {\n'
    '    "synthIdDetected": boolean,\n'
    '    "watermarkFound": boolean\n'
    "  }\n"
    "}"
)


_ALLOWED_GEN_AI_TOOLS = {
    "Google AI",
    "OpenAI",
    "Kakao",
    "ElevenLabs",
    "Others",
    "Unknown",
}


def _coerce_gen_ai_tool(value) -> str:
    """Map Gemini's free-text source to an allowed label, defaulting to Unknown."""
    if isinstance(value, str) and value.strip() in _ALLOWED_GEN_AI_TOOLS:
        return value.strip()
    return "Unknown"

_MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def _coerce_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return default


def _compute_confidence(
    synth_id_detected: bool,
    watermark_found: bool,
    is_ai: bool | None,
    raw_confidence: float,
) -> float:
    """
    Compute the final SynthID confidence score.

    Priority:
      1. Watermark confirmed (synth_id_detected or watermark_found) → 0.99 (definitive)
      2. No watermark → trust Gemini's raw visual evaluation score entirely.
         No floors, no caps, no adjustments. Gemini's prompt instructs it to
         use the full 0.0–1.0 range based solely on visual evidence.
    """
    if synth_id_detected or watermark_found:
        # Definitive watermark hit — maximum confidence
        return 0.99

    # No watermark: pass Gemini's raw score through as-is (clamped to valid range only)
    clamped = max(0.0, min(1.0, raw_confidence))
    return round(clamped, 4)



class SynthIDAgent:
    """Stateless: each ``check`` call is an independent Gemini request."""

    @staticmethod
    def check(
        image_path: str | Path,
        project_id: str,
        location: str = "global",
    ) -> SynthIDResult:
        if not project_id:
            return SynthIDResult(
                is_ai=None,
                reasoning="SynthID analysis unavailable (no GCP_PROJECT_ID).",
            )

        try:
            from google import genai
            from google.genai import types

            from .gemini_router import call_gemini_with_retry

            client = genai.Client(vertexai=True, project=project_id, location=location)
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            ext = os.path.splitext(str(image_path))[1].lower()
            mime_type = _MIME_BY_EXT.get(ext, "image/jpeg")

            logger.info(
                "[SynthID] Analyzing image: %s (mime: %s)", image_path, mime_type
            )
            logger.info("[SynthID] Sending prompt to Gemini:\n%s", _SYNTHID_PROMPT)
            response = call_gemini_with_retry(
                client,
                model="gemini-2.5-pro",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    _SYNTHID_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            logger.info("[SynthID] Raw Gemini response:\n%s", response.text)

            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]
            payload = json.loads(raw.strip())
            logger.info(
                "[SynthID] Parsed JSON payload:\n%s",
                json.dumps(payload, indent=2),
            )

            metadata = payload.get("metadata", {}) or {}
            synth_id_detected = _coerce_bool(metadata.get("synthIdDetected"))
            watermark_found = _coerce_bool(metadata.get("watermarkFound"))
            is_ai = (
                _coerce_bool(payload.get("isAI"), default=False)
                if payload.get("isAI") is not None
                else None
            )
            raw_confidence = float(payload.get("confidence", 0) or 0)

            confidence = _compute_confidence(
                synth_id_detected=synth_id_detected,
                watermark_found=watermark_found,
                is_ai=is_ai,
                raw_confidence=raw_confidence,
            )

            result = SynthIDResult(
                is_ai=is_ai,
                confidence=confidence,
                reasoning=str(payload.get("reasoning", "") or ""),
                synth_id_detected=synth_id_detected,
                watermark_found=watermark_found,
                gen_ai_tool=_coerce_gen_ai_tool(payload.get("genAITool")),
            )
            logger.info(
                "[SynthID] Final SynthIDResult:\n%s",
                json.dumps(result.model_dump(), indent=2),
            )
            return result
        except Exception as e:
            logger.exception("SynthID check failed")
            return SynthIDResult(
                is_ai=None,
                reasoning=f"SynthID analysis failed: {e}",
            )
