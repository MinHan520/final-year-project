from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings
from ..schemas import ObjectClassificationResult
from .gemini_router import call_gemini_with_retry, _strip_code_fences

logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_INSTRUCTION = """
You are the Object Classification Agent for TruthLens. 
Your goal is to decide which path the forensic pipeline should take based on the provided file.

You must classify the file into exactly one of these 4 categories:
1. "image" (Photos, digital art, scans)
2. "video" (Moving images, MP4, WebM, etc.)
3. "audio" (Sound files, MP3, WAV, etc.)
4. "text" (Documents, PDFs, text files)

Return your verdict in strict JSON format:
{
  "media_type": "image" | "video" | "audio" | "text",
  "reasoning": "short explanation of your classification"
}
"""

class ObjectClassificationAgent:
    """Agentic file classifier using Gemini to route forensic analysis."""

    @staticmethod
    def classify(
        file_path: Path, 
        project_id: str, 
        location: str
    ) -> ObjectClassificationResult:
        """Determines media type using Gemini multimodal capabilities."""
        if not project_id:
            # Fallback to extension-based if no API key
            from .gemini_router import detect_media_type
            media_type = detect_media_type(file_path.name)
            return ObjectClassificationResult(
                media_type=media_type, 
                filename=file_path.name
            )

        try:
            from google import genai
            from google.genai import types
            from PIL import Image

            client = genai.Client(vertexai=True, project=project_id, location=location)
            
            # Preparation for multimodal if it's an image
            contents = [f"Please classify this file: {file_path.name}"]
            
            # Try to load as image for Gemini inspection if possible
            try:
                img = Image.open(file_path)
                contents.append(img)
            except Exception:
                # If not an image, Gemini will use the filename and context
                pass

            logger.info(
                "[ClassificationAgent] Classifying file: %s | Prompt: %s",
                file_path.name, contents[0],
            )

            response = call_gemini_with_retry(
                client,
                model=get_settings().classification_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=CLASSIFICATION_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                ),
            )

            logger.info("[ClassificationAgent] Raw Gemini response:\n%s", response.text)
            data = json.loads(_strip_code_fences(response.text))
            media_type = data.get("media_type", "unknown")
            logger.info(
                "[ClassificationAgent] Parsed JSON response:\n%s",
                json.dumps(data, indent=2),
            )
            logger.info("[ClassificationAgent] %s -> %s (%s)", file_path.name, media_type, data.get('reasoning'))
            
            return ObjectClassificationResult(
                media_type=media_type,
                filename=file_path.name
            )

        except Exception as e:
            logger.exception("Object Classification Agent failed")
            from .gemini_router import detect_media_type
            return ObjectClassificationResult(
                media_type=detect_media_type(file_path.name),
                filename=file_path.name
            )
