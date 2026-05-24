"""Unit tests for ObjectClassificationAgent.

With no GCP_PROJECT_ID the agent falls back to extension-based detection
via detect_media_type, so these tests run without any network calls.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def tmp_files(tmp_path: Path):
    """Return a helper that creates a temp file with a given name and content."""
    def _make(name: str, content: bytes = b"data") -> Path:
        p = tmp_path / name
        p.write_bytes(content)
        return p
    return _make


def _png_bytes() -> bytes:
    rng = np.random.default_rng(seed=42)
    arr = rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def test_image_extension_classified_as_image(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    result = ObjectClassificationAgent.classify(tmp_files("photo.jpg", _png_bytes()), "", "")
    assert result.media_type == "image"
    assert result.filename == "photo.jpg"


def test_png_extension_classified_as_image(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    result = ObjectClassificationAgent.classify(tmp_files("scan.png", _png_bytes()), "", "")
    assert result.media_type == "image"


def test_audio_extension_classified_as_audio(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    result = ObjectClassificationAgent.classify(tmp_files("track.mp3"), "", "")
    assert result.media_type == "audio"


def test_video_extension_classified_as_video(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    result = ObjectClassificationAgent.classify(tmp_files("clip.mp4"), "", "")
    assert result.media_type == "video"


def test_text_extension_classified_as_text(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    result = ObjectClassificationAgent.classify(tmp_files("notes.txt"), "", "")
    assert result.media_type == "text"


def test_pdf_extension_classified_as_text(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    result = ObjectClassificationAgent.classify(tmp_files("report.pdf"), "", "")
    assert result.media_type == "text"


def test_returns_objectclassificationresult_schema(tmp_files):
    from app.agents.classification_agent import ObjectClassificationAgent
    from app.schemas import ObjectClassificationResult
    result = ObjectClassificationAgent.classify(tmp_files("img.webp", _png_bytes()), "", "")
    assert isinstance(result, ObjectClassificationResult)
