"""End-to-end test of the scan pipeline against the FastAPI app.

We run the orchestrator with detector=None (no checkpoint required) so the
test exercises every wiring path: file upload, BackgroundTasks dispatch,
SQLite persistence, SSE replay for late joiners, and the failure path
that fires when the detector is missing. The Gemini-backed stages all
short-circuit gracefully because GCP_PROJECT_ID is empty in the test env.
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("GCP_PROJECT_ID", "")
    monkeypatch.setenv("AIDE_CHECKPOINT_PATH", str(tmp_path / "missing.pth"))
    monkeypatch.chdir(tmp_path)

    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as tc:
        yield tc


def _png_bytes() -> bytes:
    rng = np.random.default_rng(seed=7)
    arr = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _wait_for_terminal(client: TestClient, scan_id: str, timeout_s: float = 10.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        resp = client.get(f"/api/scan/{scan_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if body["status"] in {"complete", "failed"}:
            return body
        time.sleep(0.05)
    raise AssertionError(f"scan {scan_id} did not terminate in {timeout_s}s")


def test_health_endpoint_reports_state(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["detector_loaded"] is False
    assert body["gcp_configured"] is False


def test_upload_runs_pipeline_and_records_failure_without_detector(client: TestClient):
    files = {"file": ("test.png", _png_bytes(), "image/png")}
    resp = client.post("/api/scan", files=files)
    assert resp.status_code == 202, resp.text
    scan_id = resp.json()["scan_id"]
    assert scan_id

    record = _wait_for_terminal(client, scan_id)
    # Without the detector loaded, the pipeline marks the scan as failed
    # — but the greeting stage already ran and is recorded.
    assert record["status"] == "failed"
    assert "AIDE detector not loaded" in (record.get("error") or "")
    assert record["filename"] == "test.png"


def test_list_scans_returns_recent(client: TestClient):
    files = {"file": ("a.png", _png_bytes(), "image/png")}
    client.post("/api/scan", files=files)
    files = {"file": ("b.png", _png_bytes(), "image/png")}
    client.post("/api/scan", files=files)

    resp = client.get("/api/sessions/current/scans")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 2
    assert {r["filename"] for r in rows} >= {"a.png", "b.png"}


def test_non_image_upload_short_circuits(client: TestClient):
    """Non-image files are accepted and classified, then short-circuit with a
    'coming soon' eval result rather than being rejected at the API layer."""
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    resp = client.post("/api/scan", files=files)
    assert resp.status_code == 202, resp.text
    scan_id = resp.json()["scan_id"]

    record = _wait_for_terminal(client, scan_id)
    assert record["status"] == "complete"
    result = record.get("result") or {}
    classification = result.get("object_classification") or {}
    assert classification.get("media_type") == "text"
    eval_text = (result.get("eval") or {}).get("text", "")
    assert "development" in eval_text or "soon" in eval_text


def test_get_scan_404_when_missing(client: TestClient):
    resp = client.get("/api/scan/does-not-exist")
    assert resp.status_code == 404


def test_delete_scan_removes_record(client: TestClient):
    files = {"file": ("c.png", _png_bytes(), "image/png")}
    scan_id = client.post("/api/scan", files=files).json()["scan_id"]
    _wait_for_terminal(client, scan_id)

    resp = client.delete(f"/api/scans/{scan_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/scan/{scan_id}").status_code == 404


def test_sse_replay_for_completed_scan(client: TestClient):
    files = {"file": ("d.png", _png_bytes(), "image/png")}
    scan_id = client.post("/api/scan", files=files).json()["scan_id"]
    _wait_for_terminal(client, scan_id)

    # After completion the bus has dropped the queue, so the SSE endpoint
    # should fall back to a single replay event from the persisted record.
    with client.stream("GET", f"/api/scan/{scan_id}/events") as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    # Either a "complete" or "error" terminal event must show up.
    assert "event: error" in body or "event: complete" in body
    assert scan_id in body
