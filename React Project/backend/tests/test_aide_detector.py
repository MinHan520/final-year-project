"""Optional integration test for the AIDE detector.

Skipped unless AIDE_CHECKPOINT_PATH points at a usable checkpoint, since
the model + pre-trained backbones are large and CI shouldn't pull them.
"""

import pytest


def test_aide_predict_runs_when_checkpoint_available(
    aide_checkpoint_path, sample_image_path
):
    if aide_checkpoint_path is None or not aide_checkpoint_path.exists():
        pytest.skip("AIDE_CHECKPOINT_PATH not set; skipping detector integration test.")

    from app.agents.aide_detector import AIDEDetectorAgent

    agent = AIDEDetectorAgent(
        checkpoint_path=aide_checkpoint_path,
        device="cpu",
    )
    result = agent.predict(sample_image_path)
    assert result.success is True
    assert 0.0 <= result.score <= 1.0
