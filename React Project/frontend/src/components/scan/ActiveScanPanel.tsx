import { useEffect, useState, useRef } from 'react';
import { useScanStream } from '../../hooks/useScanStream';
import { StageRow } from './StageRow';
import { RiskScoreCard } from './RiskScoreCard';
import { ForensicMapTrio } from './ForensicMapTrio';
import { ConflictAlert } from './ConflictAlert';
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';
import type { ConflictResult } from '../../api/types';

interface ActiveScanPanelProps {
  scanId: string;
  onComplete?: (scanId: string) => void;
}

/** Simple read-only banner for LOW-severity / no-conflict outcomes. */
function ConflictBanner({ conflict }: { conflict: ConflictResult }) {
  if (!conflict.has_conflict) {
    return (
      <div className="flex items-start gap-2 text-sm text-success mt-2">
        <CheckCircle2 className="size-4 mt-0.5 shrink-0" />
        <p>Detectors consistent — no conflict found.</p>
      </div>
    );
  }

  // LOW severity: pipeline continues, show informational notice only.
  return (
    <div className="flex items-start gap-2 text-sm mt-2 p-3 rounded-md border
                    bg-primary/10 border-primary/30 text-primary">
      <ShieldAlert className="size-4 mt-0.5 shrink-0" />
      <div>
        {conflict.rule_triggered && (
          <p className="font-semibold mb-1">
            Rule {conflict.rule_triggered} — {conflict.severity?.toUpperCase()} conflict
          </p>
        )}
        <p>{conflict.reason}</p>
      </div>
    </div>
  );
}

export function ActiveScanPanel({ scanId, onComplete }: ActiveScanPanelProps) {
  const { stages, status, error } = useScanStream(scanId);
  const [conflictResolved, setConflictResolved] = useState(false);
  const hasCompletedRef = useRef(false);

  // Reset the guard when the scanId changes (new scan)
  useEffect(() => {
    hasCompletedRef.current = false;
  }, [scanId]);

  useEffect(() => {
    if (status === 'complete' && !hasCompletedRef.current) {
      hasCompletedRef.current = true;

      // Notify the top header bell to glow + chime (fires exactly once)
      window.dispatchEvent(new CustomEvent('scan-completed', { detail: { scanId } }));

      // Notify the parent (Dashboard) immediately — let Dashboard handle the delay
      if (onComplete) {
        onComplete(scanId);
      }
    }
  }, [status, scanId, onComplete]);

  // Reset conflict resolution state if the backend loops and starts conflict evaluation again
  useEffect(() => {
    if (stages.conflict?.state === 'running') {
      setConflictResolved(false);
    }
  }, [stages.conflict?.state]);

  // "Low Level Artifact Analysis" row is complete only after commentary finishes.
  const artifactState =
    stages.opencv_commentary?.state === 'complete'
      ? 'complete'
      : stages.opencv_commentary?.state === 'error'
      ? 'error'
      : stages.opencv_maps?.state === 'running' || stages.opencv_commentary?.state === 'running'
      ? 'running'
      : stages.opencv_maps?.state === 'complete'
      ? 'running'
      : 'pending';

  const conflictResult = stages.conflict?.result as ConflictResult | undefined;
  const needsHumanInput =
    conflictResult?.action_required === 'human_review' && !conflictResolved;

  return (
    <div className="rounded-2xl bg-card overflow-hidden mt-6 shadow-sm">
      <div className="p-4 bg-card/80 flex items-center justify-between">
        <div>
          <h2 className="font-display font-medium text-fg">Live Analysis</h2>
          <div className="text-xs text-muted mt-1 uppercase tracking-wider">
            Status:{' '}
            <span
              className={
                status === 'failed'
                  ? 'text-danger'
                  : status === 'complete'
                  ? 'text-success'
                  : needsHumanInput
                  ? 'text-warning'
                  : 'text-primary'
              }
            >
              {needsHumanInput ? 'awaiting review' : status}
            </span>
          </div>
        </div>
      </div>

      {error && status === 'failed' && (
        <div className="p-4 bg-danger/10 border-b border-danger/20 flex items-center gap-3 text-danger">
          <AlertTriangle className="size-5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      <div className="flex flex-col gap-2 p-2">
        <StageRow
          label="Object Classification"
          state={stages.object_classification?.state || 'pending'}
          error={stages.object_classification?.error}
        >
          {stages.object_classification?.result && (
            <p className="text-sm text-muted capitalize">
              Media type detected:{' '}
              <strong className="text-fg">
                {stages.object_classification.result.media_type}
              </strong>
            </p>
          )}
        </StageRow>

        <StageRow
          label="AIDE Detection"
          state={stages.aide?.state || 'pending'}
          error={stages.aide?.error}
        >
          {stages.aide?.result && (
            <div className="mt-4 max-w-[200px]">
              <RiskScoreCard aide={stages.aide.result} />
            </div>
          )}
        </StageRow>

        <StageRow
          label="Low Level Artifact Analysis"
          state={artifactState}
          error={stages.opencv_maps?.error || stages.opencv_commentary?.error}
        >
          {stages.opencv_maps?.result && (
            <ForensicMapTrio
              maps={stages.opencv_maps.result}
              comments={stages.opencv_commentary?.result}
            />
          )}
          {stages.opencv_maps?.state === 'complete' &&
            stages.opencv_commentary?.state === 'running' && (
              <p className="text-sm text-muted mt-4 animate-pulse">
                Generating expert commentary...
              </p>
            )}
        </StageRow>

        <StageRow
          label="SynthID Detection"
          state={stages.synthid?.state || 'pending'}
          error={stages.synthid?.error}
        >
          {stages.synthid?.result && (
            <div className="text-sm text-muted mt-2">
              <p>
                Watermark Found:{' '}
                <strong
                  className={
                    stages.synthid.result.watermark_found
                      ? 'text-danger'
                      : 'text-success'
                  }
                >
                  {stages.synthid.result.watermark_found ? 'Yes' : 'No'}
                </strong>
              </p>
              {stages.synthid.result.reasoning && (
                <p className="mt-1">{stages.synthid.result.reasoning}</p>
              )}
            </div>
          )}
        </StageRow>

        <StageRow
          label="Conflict Resolution"
          state={stages.conflict?.state || 'pending'}
          error={stages.conflict?.error}
        >
          {conflictResult && needsHumanInput && (
            <ConflictAlert
              conflict={conflictResult}
              scanId={scanId}
              onDecision={() => setConflictResolved(true)}
            />
          )}
          {conflictResult && !needsHumanInput && (
            <ConflictBanner conflict={conflictResult} />
          )}
        </StageRow>

        <StageRow
          label="Final Verdict"
          state={stages.eval?.state || 'pending'}
          error={stages.eval?.error}
        >
          {(stages.eval?.streamText || stages.eval?.result?.text) && (
            <div className="text-sm text-fg mt-2 whitespace-pre-wrap leading-relaxed">
              {stages.eval?.result?.text || stages.eval?.streamText}
            </div>
          )}
        </StageRow>
      </div>
    </div>
  );
}
