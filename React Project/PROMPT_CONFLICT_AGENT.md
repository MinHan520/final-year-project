# FutureLens — Conflict Resolution Agent Implementation Prompt

> **Paste this entire document into Claude along with read/write access to the working tree.**
> The prompt is self-contained: it provides the exact logic, schema, and UI code required to implement the Conflict Resolution Agent.

---

## Role and Goal
You are an expert Full-Stack engineer working on the **FutureLens** forensic deepfake detection system. Your task is to implement the **Conflict Resolution Agent**, a critical piece of the system architecture that sits between the SynthID stage and the Explanatory Agent. 

The agent's job is to evaluate signals from previous stages simultaneously and escalate to the highest severity found. If a high-severity conflict is found, it pauses the orchestration pipeline and requires immediate human input (Human-in-the-Loop).

**Constraint:** Do not break existing orchestrator logic. Integrate this cleanly into the existing FastAPI + React stack.

---

## 1. Conflict Logic (Rule Design)

A conflict occurs when highly confident but opposing signals are detected. The agent evaluates **all** rules simultaneously and escalates to the highest severity found, rather than returning on the first match.

### Conflict Rules
*   **Rule A — False Negative Model (HIGH severity)**
    AIDE score indicates Authentic (< 30%), BUT SynthID watermark is explicitly detected (100% AI).
*   **Rule B — False Positive Model (MEDIUM severity)**
    AIDE score indicates High Risk (> 80%), BUT SynthID is confident it is NOT AI-generated, AND OpenCV artifact analysis reports no anomalies.
*   **Rule C — Inconclusive Threshold (LOW severity)**
    AIDE score sits in the inconclusive boundary (40–60%) where automated confidence is too low to proceed without review. Pipeline continues but flags ambiguity downstream.
*   **Rule E — SynthID Ambiguity Zone (MEDIUM severity)**
    SynthID returns a partial watermark match (40–70% confidence) rather than a binary found/not-found. Silently ambiguous results are treated as a conflict requiring review.

### Severity Behaviour
| Severity | Pipeline Action |
| :--- | :--- |
| **HIGH** | Block pipeline, require immediate human input |
| **MEDIUM** | Flag for human review, pause pipeline |
| **LOW** | Log conflict, continue to Explanatory Agent with metadata |

---

## 2. Backend Implementation

### A. Updated Schema (`backend/app/schemas.py`)
Add the following models:
```python
from enum import Enum
from typing import Literal
from pydantic import BaseModel

class ConflictSeverity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"

class ConflictResult(BaseModel):
    has_conflict:        bool
    severity:            ConflictSeverity | None          = None
    conflicting_signals: list[str]                        = []
    rule_triggered:      str | None                       = None
    reason:              str | None                       = None
    action_required:     Literal["proceed", "human_review", "reclassify"] | None = None
    confidence_gap:      float | None                    = None
```

### B. Conflict Agent (`backend/app/agents/conflict_agent.py`)
Create the new agent class:
```python
from app.schemas import ConflictResult, ConflictSeverity

class ConflictResolutionAgent:
    """
    Pure logic agent — no LLM required.
    Evaluates ALL rules simultaneously and escalates
    to the highest severity triggered.
    """

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
    def evaluate(aide_score: float, synthid_result, opencv_anomalies: bool) -> ConflictResult:
        triggered_rules = []

        # ── Rule A: False Negative ───────────────────────────────
        if aide_score < 0.30 and synthid_result.watermark_found:
            triggered_rules.append((
                "A", ConflictSeverity.HIGH,
                "Model predicts authentic but cryptographic watermark detected.",
                ["aide_score", "synthid_watermark"],
            ))

        # ── Rule B: False Positive ───────────────────────────────
        if aide_score > 0.80 and not synthid_result.watermark_found and not opencv_anomalies:
            triggered_rules.append((
                "B", ConflictSeverity.MEDIUM,
                "High AI score but no corroborating artifact evidence from SynthID or OpenCV.",
                ["aide_score", "synthid_watermark", "opencv"],
            ))

        # ── Rule C: Inconclusive Zone ────────────────────────────
        if ConflictResolutionAgent.INCONCLUSIVE_LOWER <= aide_score <= ConflictResolutionAgent.INCONCLUSIVE_UPPER:
            triggered_rules.append((
                "C", ConflictSeverity.LOW,
                "AIDE score in inconclusive range — insufficient confidence to auto-proceed.",
                ["aide_score"],
            ))

        # ── Rule E: SynthID Ambiguity Zone ───────────────────────
        if ConflictResolutionAgent.SYNTHID_AMBIGUITY_LOWER <= synthid_result.confidence <= ConflictResolutionAgent.SYNTHID_AMBIGUITY_UPPER:
            triggered_rules.append((
                "E", ConflictSeverity.MEDIUM,
                "SynthID returned a partial watermark confidence score — result is silently ambiguous.",
                ["synthid_confidence"],
            ))

        # ── No conflicts ─────────────────────────────────────────
        if not triggered_rules:
            return ConflictResult(has_conflict=False, action_required="proceed")

        # ── Escalate to highest severity found ───────────────────
        worst = next(rule for sev in ConflictResolutionAgent.SEVERITY_ORDER for rule in triggered_rules if rule[1] == sev)

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
```

### C. Updated Orchestrator (`backend/app/orchestrator.py`)
Modify the `run_scan` loop to handle the conflict evaluation, loop guard, and pausing via `asyncio.Event`. Reference the provided logic outline for implementation details (using `HUMAN_REVIEW_TIMEOUT_SECONDS = 300` and `MAX_RECLASSIFICATION_ATTEMPTS = 2`). Make sure `conflict_result` is passed into the Explanatory Agent.

### D. New Endpoint — Human Decision (`backend/app/api/routes_scan.py`)
Add the `POST /api/scan/{scan_id}/resolve_conflict` endpoint as outlined to unblock the `asyncio.Event` pending review in the orchestrator.

---

## 3. Frontend Implementation

### A. Updated Types (`frontend/src/api/types.ts`)
Add the new types:
```typescript
export type ConflictSeverity = 'low' | 'medium' | 'high';
export type ConflictAction   = 'proceed' | 'human_review' | 'reclassify';

export interface ConflictResult {
  has_conflict:         boolean;
  severity:             ConflictSeverity | null;
  conflicting_signals:  string[];
  rule_triggered:       string | null;
  reason:               string | null;
  action_required:      ConflictAction | null;
  confidence_gap:       number | null;
}

// Add conflict_result to the existing ScanSummary interface
```

### B. Updated Scan Panel (`frontend/src/components/scan/ActiveScanPanel.tsx`)
Render the `ConflictAlert` if a conflict exists:
```tsx
{conflict_result?.has_conflict && (
  <ConflictAlert
    conflict={conflict_result}
    scanId={scanId}
    onDecision={handleConflictDecision}
  />
)}
```

### C. Conflict Alert Component (`frontend/src/components/scan/ConflictAlert.tsx`)
Implement the `ConflictAlert` UI component using the provided React implementation. Ensure the countdown timer correctly limits the human-in-the-loop review window to 300 seconds and forces the user to provide a required reason before overriding or re-classifying.

---
## Exit Criteria
- Uploading an image that triggers Rule A, B, C, or E correctly populates the Conflict Agent's output.
- The pipeline physically pauses on the backend when `action_required == "human_review"`.
- The frontend renders the alert component with a live countdown.
- Choosing a decision from the frontend successfully hits the resolve endpoint and resumes the pipeline.
- Running `pytest` and `npx tsc -b` succeeds with no errors.
