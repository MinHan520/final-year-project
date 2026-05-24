"""OpenCV low-level forensics agent.

Two responsibilities:
  1. Compute the three forensic visualizations (noise residual, Laplacian
     edge gradient, Error-Level Analysis heatmap) — pure OpenCV, no LLM.
  2. Send the original image to Gemini Vision for plain-English commentary
     on those three signals.

The compute step is fast and deterministic; the VLM commentary is slow and
needs a project_id. Callers should be able to render the maps as soon as
``compute_maps`` returns and stream the VLM commentary in afterwards.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ..schemas import ForensicMaps, OpenCVComments, OpenCVResult

logger = logging.getLogger(__name__)


_OPENCV_VLM_PROMPT = (
    "You are a friendly AI image forensics expert who explains complex technical findings "
    "in simple, everyday language that anyone can understand. "
    "Analyze the attached image for signs of AI generation across exactly three forensic criteria. "
    "For each criterion, write 2–3 clear sentences: first state what you found, then explain "
    "what it means in plain English, and end with a simple verdict (e.g. 'This suggests the image may be AI-generated.' "
    "or 'This looks consistent with a real photograph.').\n\n"
    "Criteria to analyze:\n\n"
    "1. NOISE RESIDUALS — Real cameras produce random, natural grain from light particles hitting the sensor. "
    "AI tools instead leave behind repeating patterns, overly smooth skin or surfaces, or a fine artificial texture. "
    "Look for: grid-like textures, unnatural smoothness in areas that should have grain, or diffusion-model grain patterns.\n\n"
    "2. EDGE SHARPNESS — Real photos blur gradually as objects move out of focus (like a portrait with a soft background). "
    "AI images often have impossible focus: backgrounds that are sharp where they should be blurry, "
    "or object edges that are unnaturally crisp with no gradual transition. "
    "Look for: focus boundaries that defy real optics, or edges that look 'cut out'.\n\n"
    "3. COMPRESSION CONSISTENCY — When a real photo is saved as a JPEG, every part of the image is compressed "
    "at the same level. AI-generated or edited images often have mismatched compression: "
    "some areas look freshly synthesised while others look heavily compressed, like puzzle pieces from different sources. "
    "Look for: patches of the image that appear inconsistently sharp, blurry, or artifact-heavy compared to neighbouring areas.\n\n"
    "Return your analysis as a JSON object with strictly these keys:\n"
    '{"noise": "...", "edges": "...", "compression": "..."}\n\n'
    "Each value must be written in plain English, suitable for a non-technical user. "
    "Avoid jargon. If you must use a technical term, immediately explain it in brackets. "
    "Return ONLY the JSON object, no markdown fences or extra text."
)


_FALLBACK_COMMENTS = OpenCVComments(
    noise="Check Your Gemini API",
    edges="Check Your Gemini API",
    compression="Check Your Gemini API",
)


def _rgb_to_b64_png(rgb: np.ndarray) -> str:
    """Encode an RGB ndarray as a base64 PNG string."""
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise RuntimeError("cv2.imencode failed for forensic map")
    return base64.b64encode(buf.tobytes()).decode("ascii")


class OpenCVForensicsAgent:
    """Stateless forensic feature extractor + optional Gemini commentary."""

    @staticmethod
    def compute_maps(image_path: str | Path) -> ForensicMaps:
        """Extract noise residual, Laplacian edge, and ELA heatmap as base64 PNGs."""
        img_bgr = cv2.imread(str(image_path))
        if img_bgr is None:
            raise FileNotFoundError(f"Could not read image: {image_path}")

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Noise residual: subtract a 5x5 median blur to isolate high-frequency content.
        blurred = cv2.medianBlur(gray, 5)
        noise = cv2.subtract(gray, blurred)
        noise_norm = cv2.normalize(noise, None, 0, 255, cv2.NORM_MINMAX)
        noise_rgb = cv2.cvtColor(noise_norm, cv2.COLOR_GRAY2RGB)

        # Laplacian edge gradient with INFERNO colormap.
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
        lap_abs = np.uint8(np.clip(np.abs(laplacian), 0, 255))
        edge_bgr = cv2.applyColorMap(lap_abs, cv2.COLORMAP_INFERNO)
        edge_rgb = cv2.cvtColor(edge_bgr, cv2.COLOR_BGR2RGB)

        # Error-Level Analysis: re-encode at JPEG quality 90, diff, amplify x20.
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        ok, enc_buf = cv2.imencode(".jpg", img_bgr, encode_param)
        if not ok:
            raise RuntimeError("Failed to JPEG-encode for ELA")
        recompressed = cv2.imdecode(enc_buf, cv2.IMREAD_COLOR)
        ela_diff = cv2.absdiff(img_bgr, recompressed)
        ela_amp = np.clip(ela_diff.astype(np.float32) * 20, 0, 255).astype(np.uint8)
        ela_gray = cv2.cvtColor(ela_amp, cv2.COLOR_BGR2GRAY)
        ela_bgr = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)
        ela_rgb = cv2.cvtColor(ela_bgr, cv2.COLOR_BGR2RGB)

        return ForensicMaps(
            noise_png_b64=_rgb_to_b64_png(noise_rgb),
            edge_png_b64=_rgb_to_b64_png(edge_rgb),
            ela_png_b64=_rgb_to_b64_png(ela_rgb),
        )

    @staticmethod
    def explain_with_vlm(
        image_path: str | Path,
        project_id: str,
        location: str = "us-central1",
    ) -> OpenCVComments:
        """Send the original image to Gemini Vision for plain-English commentary."""
        if not project_id:
            return _FALLBACK_COMMENTS

        try:
            from PIL import Image
            from google import genai

            from .gemini_router import call_gemini_with_retry

            client = genai.Client(vertexai=True, project=project_id, location=location)
            img = Image.open(image_path)

            response = call_gemini_with_retry(
                client,
                model="gemini-2.5-pro",
                contents=[img, _OPENCV_VLM_PROMPT],
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[: raw.rfind("```")]
            payload = json.loads(raw.strip())

            return OpenCVComments(
                noise=payload.get("noise", "Analysis unavailable."),
                edges=payload.get("edges", "Analysis unavailable."),
                compression=payload.get("compression", "Analysis unavailable."),
            )
        except Exception as e:
            logger.warning("OpenCV VLM analysis error: %s", e)
            return _FALLBACK_COMMENTS

    @classmethod
    def analyze(
        cls,
        image_path: str | Path,
        project_id: str,
        location: str = "us-central1",
    ) -> OpenCVResult:
        """Convenience: compute maps + VLM commentary in one call."""
        maps = cls.compute_maps(image_path)
        comments = cls.explain_with_vlm(image_path, project_id, location)
        return OpenCVResult(maps=maps, comments=comments)
