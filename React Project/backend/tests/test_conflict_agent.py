"""Unit tests for the ConflictResolutionAgent — no LLM, no checkpoints required."""

from __future__ import annotations

import pytest

from app.agents.conflict_agent import ConflictResolutionAgent
from app.schemas import ConflictSeverity, SynthIDResult


def _synth(
    watermark_found: bool = False,
    confidence: float = 0.0,
    is_ai: bool | None = None,
) -> SynthIDResult:
    return SynthIDResult(
        watermark_found=watermark_found,
        confidence=confidence,
        is_ai=is_ai,
    )


# ── Rule A ────────────────────────────────────────────────────────────────────

def test_rule_a_fires_when_aide_low_and_watermark_found():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.10,
        synthid_result=_synth(watermark_found=True, confidence=0.90),
        opencv_anomalies=False,
    )
    assert result.has_conflict
    assert result.rule_triggered == "A"
    assert result.severity == ConflictSeverity.HIGH
    assert result.action_required == "human_review"
    assert "aide_score" in result.conflicting_signals
    assert "synthid_watermark" in result.conflicting_signals


def test_rule_a_does_not_fire_when_aide_borderline():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.30,  # exactly at threshold — NOT < 0.30
        synthid_result=_synth(watermark_found=True, confidence=0.95),
        opencv_anomalies=False,
    )
    assert result.rule_triggered != "A"


# ── Rule B ────────────────────────────────────────────────────────────────────

def test_rule_b_fires_when_high_aide_no_corroboration():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.90,
        synthid_result=_synth(watermark_found=False, confidence=0.10),
        opencv_anomalies=False,
    )
    assert result.has_conflict
    assert result.rule_triggered == "B"
    assert result.severity == ConflictSeverity.MEDIUM
    assert result.action_required == "human_review"


def test_rule_b_does_not_fire_when_opencv_has_anomalies():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.90,
        synthid_result=_synth(watermark_found=False, confidence=0.10),
        opencv_anomalies=True,
    )
    # Rule B requires no opencv anomalies; without it, should not trigger B
    assert result.rule_triggered != "B"


def test_rule_b_does_not_fire_when_synthid_found_watermark():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.90,
        synthid_result=_synth(watermark_found=True, confidence=0.10),
        opencv_anomalies=False,
    )
    assert result.rule_triggered != "B"


# ── Rule C ────────────────────────────────────────────────────────────────────

def test_rule_c_fires_in_inconclusive_zone():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.50,
        synthid_result=_synth(watermark_found=False, confidence=0.10),
        opencv_anomalies=False,
    )
    assert result.has_conflict
    assert "C" in (result.rule_triggered or "")
    assert result.severity == ConflictSeverity.LOW
    assert result.action_required == "proceed"  # LOW → pipeline continues


def test_rule_c_fires_at_lower_boundary():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.40,
        synthid_result=_synth(watermark_found=False, confidence=0.10),
        opencv_anomalies=False,
    )
    assert result.has_conflict


def test_rule_c_does_not_fire_below_zone():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.39,
        synthid_result=_synth(watermark_found=False, confidence=0.10),
        opencv_anomalies=False,
    )
    # 0.39 is below the inconclusive range
    assert result.rule_triggered != "C"


# ── Rule E ────────────────────────────────────────────────────────────────────

def test_rule_e_fires_in_synthid_ambiguity_zone():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.20,  # clear — no other rules
        synthid_result=_synth(watermark_found=False, confidence=0.55),
        opencv_anomalies=False,
    )
    assert result.has_conflict
    assert result.rule_triggered == "E"
    assert result.severity == ConflictSeverity.MEDIUM
    assert result.action_required == "human_review"


def test_rule_e_does_not_fire_outside_ambiguity_zone():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.20,
        synthid_result=_synth(watermark_found=False, confidence=0.90),
        opencv_anomalies=False,
    )
    assert result.rule_triggered != "E"


# ── Severity escalation ───────────────────────────────────────────────────────

def test_high_severity_wins_over_low():
    """Rule A (HIGH) + Rule C (LOW) active simultaneously → HIGH wins."""
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.20,          # in Rule A range AND below Rule C lower bound (0.40)
        synthid_result=_synth(watermark_found=True, confidence=0.90),
        opencv_anomalies=False,
    )
    assert result.rule_triggered == "A"
    assert result.severity == ConflictSeverity.HIGH


def test_medium_severity_wins_over_low_when_coexist():
    """Rule E (MEDIUM) + Rule C (LOW) simultaneously → MEDIUM wins."""
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.50,          # Rule C zone
        synthid_result=_synth(watermark_found=False, confidence=0.55),  # Rule E zone
        opencv_anomalies=False,
    )
    assert result.severity == ConflictSeverity.MEDIUM
    assert result.action_required == "human_review"
    # Both signals should be present
    assert "aide_score" in result.conflicting_signals
    assert "synthid_confidence" in result.conflicting_signals


# ── No conflict ───────────────────────────────────────────────────────────────

def test_no_conflict_when_clear_authentic():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.10,
        synthid_result=_synth(watermark_found=False, confidence=0.10),
        opencv_anomalies=False,
    )
    assert not result.has_conflict
    assert result.action_required == "proceed"
    assert result.severity is None


def test_no_conflict_when_clear_ai_with_corroboration():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.95,
        synthid_result=_synth(watermark_found=True, confidence=0.95),
        opencv_anomalies=True,
    )
    assert not result.has_conflict


# ── confidence_gap ────────────────────────────────────────────────────────────

def test_confidence_gap_computed_on_conflict():
    result = ConflictResolutionAgent.evaluate(
        aide_score=0.10,
        synthid_result=_synth(watermark_found=True, confidence=0.90),
        opencv_anomalies=False,
    )
    assert result.confidence_gap is not None
    assert abs(result.confidence_gap - 0.80) < 1e-9
