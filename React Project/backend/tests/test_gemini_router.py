from app.agents.gemini_router import GeminiRouterAgent, detect_media_type


def test_detect_media_type_recognizes_extensions():
    assert detect_media_type("photo.JPG") == "image"
    assert detect_media_type("clip.mp4") == "video"
    assert detect_media_type("voice.wav") == "audio"
    assert detect_media_type("report.pdf") == "text"
    assert detect_media_type("blob.xyz") == "unknown"
    assert detect_media_type(None) == "none"
    assert detect_media_type("") == "none"


def test_classify_falls_back_to_extension_when_no_project_id():
    result = GeminiRouterAgent.classify(
        text="Is this real?",
        filename="suspicious.jpg",
        project_id="",
        location="us-central1",
    )
    assert result.media_type == "image"
    assert result.action == "deepfake_analysis"
    assert result.router == "extension-fallback"


def test_classify_text_only_turn_without_file():
    result = GeminiRouterAgent.classify(
        text="hello there",
        filename=None,
        project_id="",
        location="us-central1",
    )
    assert result.media_type == "text"
    assert result.router == "extension-fallback"


def test_build_eval_prompt_includes_score_and_signals():
    from app.schemas import OpenCVComments, SynthIDResult

    prompt = GeminiRouterAgent.build_eval_prompt(
        score=0.92,
        synthid=SynthIDResult(
            is_ai=True,
            synth_id_detected=True,
            watermark_found=True,
            confidence=0.9,
        ),
        opencv=OpenCVComments(
            noise="Looks artificially smooth.",
            edges="Edges are unnaturally crisp.",
            compression="Inconsistent compression patches.",
        ),
    )
    assert "92.0%" in prompt
    assert "SynthID Watermark DETECTED" in prompt
    assert "artificially smooth" in prompt
