"""Unit tests for ScanStore + risk classifier."""

from pathlib import Path

import pytest

from app.storage import ScanStore, classify_risk


@pytest.fixture
def store(tmp_path: Path) -> ScanStore:
    return ScanStore(tmp_path / "test.db")


def test_create_and_get_scan(store: ScanStore):
    store.create("scan-1", "photo.jpg")
    record = store.get("scan-1")
    assert record is not None
    assert record["filename"] == "photo.jpg"
    assert record["status"] == "queued"
    assert record["score"] is None


def test_finalize_persists_summary_and_score(store: ScanStore):
    store.create("scan-2", "photo.jpg")
    store.finalize(
        "scan-2",
        "complete",
        result={"verdict": "AI"},
        score=0.92,
        risk_label="HIGH_RISK",
    )
    record = store.get("scan-2")
    assert record["status"] == "complete"
    assert record["score"] == pytest.approx(0.92)
    assert record["risk_label"] == "HIGH_RISK"
    assert record["result"] == {"verdict": "AI"}


def test_list_recent_returns_newest_first(store: ScanStore):
    store.create("a", "a.jpg")
    store.create("b", "b.jpg")
    rows = store.list_recent()
    assert rows[0]["scan_id"] == "b"
    assert rows[1]["scan_id"] == "a"


def test_delete(store: ScanStore):
    store.create("doomed", "x.jpg")
    assert store.delete("doomed") is True
    assert store.get("doomed") is None
    assert store.delete("doomed") is False


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.95, "HIGH_RISK"),
        (0.65, "AI_GENERATED"),
        (0.42, "INCONCLUSIVE"),
        (0.10, "AUTHENTIC"),
    ],
)
def test_classify_risk_thresholds(score: float, expected: str):
    assert classify_risk(score) == expected
