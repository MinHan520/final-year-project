"""Conflict Resolution Agent.

Evaluates all rules simultaneously and escalates to the highest severity
found rather than returning on first match.

Rules:
  A — False Negative  (HIGH):   AIDE < 30% but SynthID watermark detected
  B — False Positive  (MEDIUM): AIDE > 80%, SynthID not AI, no OpenCV anomalies
  C — Inconclusive    (LOW):    AIDE in [40%, 60%]
  E — SynthID Ambiguity (MEDIUM): SynthID confidence in [40%, 70%]
"""

from __future__ import annotations

from ..schemas import ConflictResult, ConflictSeverity


class ConflictResolutionAgent:
    """Pure logic agent — no LLM required."""

    INCONCLUSIVE_LOWER      = 0.40
    INCONCLUSIVE_UPPER      = 0.60
    SYNTHID_AMBIGUITY_LOWER = 0.40
    SYNTHID_AMBIGUITY_UPPER = 0.70

    SEVERITY_ORDER = [
        ConflictSeverity.HIGH,
        ConflictSeverity.MEDIUM,
        ConflictSeverity.LOW,
    ]

    @staticmethod
    def evaluate(
        aide_score: float,
        synthid_result,
        opencv_anomalies: bool,
    ) -> ConflictResult:
        triggered_rules: list[tuple] = []

        # ── Rule A: False Negative ───────────────────────────────────────────
        if aide_score < 0.30 and synthid_result.watermark_found:
            triggered_rules.append((
                "A",
                ConflictSeverity.HIGH,
                "Model predicts authentic but cryptographic watermark detected.",
                ["aide_score", "synthid_watermark"],
            ))

        # ── Rule B: False Positive ───────────────────────────────────────────
        if aide_score > 0.80 and not synthid_result.watermark_found and not opencv_anomalies:
            triggered_rules.append((
                "B",
                ConflictSeverity.MEDIUM,
                "High AI score but no corroborating artifact evidence from SynthID or OpenCV.",
                ["aide_score", "synthid_watermark", "opencv"],
            ))

        # ── Rule C: Inconclusive Zone ────────────────────────────────────────
        if ConflictResolutionAgent.INCONCLUSIVE_LOWER <= aide_score <= ConflictResolutionAgent.INCONCLUSIVE_UPPER:
            triggered_rules.append((
                "C",
                ConflictSeverity.LOW,
                "AIDE score in inconclusive range — insufficient confidence to auto-proceed.",
                ["aide_score"],
            ))

        # ── Rule E: SynthID Ambiguity Zone ───────────────────────────────────
        if (
            ConflictResolutionAgent.SYNTHID_AMBIGUITY_LOWER
            <= synthid_result.confidence
            <= ConflictResolutionAgent.SYNTHID_AMBIGUITY_UPPER
        ):
            triggered_rules.append((
                "E",
                ConflictSeverity.MEDIUM,
                "SynthID returned a partial watermark confidence score — result is silently ambiguous.",
                ["synthid_confidence"],
            ))

        if not triggered_rules:
            return ConflictResult(has_conflict=False, action_required="proceed")

        # Escalate to highest severity found
        worst = next(
            rule
            for sev in ConflictResolutionAgent.SEVERITY_ORDER
            for rule in triggered_rules
            if rule[1] == sev
        )

        action_map = {
            ConflictSeverity.HIGH:   "human_review",
            ConflictSeverity.MEDIUM: "human_review",
            ConflictSeverity.LOW:    "proceed",
        }

        all_signals = list({sig for rule in triggered_rules for sig in rule[3]})

        return ConflictResult(
            has_conflict        = True,
            severity            = worst[1],
            conflicting_signals = all_signals,
            rule_triggered      = worst[0],
            reason              = worst[2],
            action_required     = action_map[worst[1]],
            confidence_gap      = abs(aide_score - synthid_result.confidence),
        )


# Backward-compat alias used by existing imports
ConflictAgent = ConflictResolutionAgent
