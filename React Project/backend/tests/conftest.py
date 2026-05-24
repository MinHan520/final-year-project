"""Shared pytest fixtures.

We deliberately don't load the real AIDE checkpoint in unit tests — those
should run on any machine without GPU or downloaded weights. The agent
modules under test are designed so that:

  * ``OpenCVForensicsAgent.compute_maps`` runs purely on local CV2 — testable.
  * Gemini-backed agents short-circuit when ``project_id`` is empty — testable.
  * ``AIDEDetectorAgent`` requires the checkpoint; we test it only when an
    AIDE_CHECKPOINT_PATH env var is set (skipped otherwise).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope="session")
def sample_image_path(tmp_path_factory) -> Path:
    """A small synthetic 256x256 RGB JPEG suitable for forensic tests."""
    out_dir = tmp_path_factory.mktemp("samples")
    path = out_dir / "synthetic.jpg"

    rng = np.random.default_rng(seed=42)
    arr = rng.integers(0, 256, size=(256, 256, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path, format="JPEG", quality=95)
    return path


@pytest.fixture(scope="session")
def aide_checkpoint_path() -> Path | None:
    raw = os.environ.get("AIDE_CHECKPOINT_PATH")
    return Path(raw) if raw else None
