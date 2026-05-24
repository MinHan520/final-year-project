import base64

from app.agents.opencv_forensics import OpenCVForensicsAgent
from app.schemas import ForensicMaps


def test_compute_maps_returns_three_b64_pngs(sample_image_path):
    maps = OpenCVForensicsAgent.compute_maps(sample_image_path)
    assert isinstance(maps, ForensicMaps)
    for field in (maps.noise_png_b64, maps.edge_png_b64, maps.ela_png_b64):
        assert field, "expected non-empty base64 PNG"
        decoded = base64.b64decode(field)
        # PNG magic header — sanity check we produced a real image.
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


def test_explain_with_vlm_falls_back_without_project_id(sample_image_path):
    comments = OpenCVForensicsAgent.explain_with_vlm(sample_image_path, project_id="")
    assert comments.noise == "Check Your Gemini API"
    assert comments.edges == "Check Your Gemini API"
    assert comments.compression == "Check Your Gemini API"
