from app.agents.synthid import SynthIDAgent


def test_check_returns_neutral_result_without_project_id(sample_image_path):
    result = SynthIDAgent.check(sample_image_path, project_id="")
    assert result.is_ai is None
    assert result.synth_id_detected is False
    assert result.watermark_found is False
    assert "unavailable" in result.reasoning.lower()
