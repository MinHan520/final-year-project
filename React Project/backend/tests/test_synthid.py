import pytest

from app.agents.synthid import SynthIDAgent, _coerce_gen_ai_tool


def test_check_returns_neutral_result_without_project_id(sample_image_path):
    result = SynthIDAgent.check(sample_image_path, project_id="")
    assert result.is_ai is None
    assert result.synth_id_detected is False
    assert result.watermark_found is False
    assert result.gen_ai_tool == "Unknown"
    assert "unavailable" in result.reasoning.lower()


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Google AI", "Google AI"),
        ("OpenAI", "OpenAI"),
        ("Kakao", "Kakao"),
        ("ElevenLabs", "ElevenLabs"),
        ("Others", "Others"),
        ("Unknown", "Unknown"),
        ("  OpenAI  ", "OpenAI"),
    ],
)
def test_coerce_gen_ai_tool_accepts_allowed_labels(raw, expected):
    assert _coerce_gen_ai_tool(raw) == expected


@pytest.mark.parametrize("raw", ["Midjourney", "google ai", "", None, 42, {}])
def test_coerce_gen_ai_tool_falls_back_to_unknown(raw):
    assert _coerce_gen_ai_tool(raw) == "Unknown"
