import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, ShieldAlert, Clock, CheckCircle2, Info } from 'lucide-react';
import { resolveConflict } from '../../api/client';
import type { ConflictResult, ConflictSeverity } from '../../api/types';

const REVIEW_TIMEOUT = 300; // seconds

interface ConflictAlertProps {
  conflict: ConflictResult;
  scanId: string;
  onDecision?: (decision: 'proceed' | 'reclassify', reason: string) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

const severityConfig: Record<
  ConflictSeverity,
  { border: string; bg: string; text: string; label: string }
> = {
  high:   { border: 'border-danger/40',  bg: 'bg-danger/10',  text: 'text-danger',  label: 'HIGH'   },
  medium: { border: 'border-warning/40', bg: 'bg-warning/10', text: 'text-warning', label: 'MEDIUM' },
  low:    { border: 'border-primary/30', bg: 'bg-primary/10', text: 'text-primary', label: 'LOW'    },
};

const signalLabels: Record<string, string> = {
  aide_score:       'AIDE Score',
  synthid_watermark:'SynthID Watermark',
  synthid_confidence:'SynthID Confidence',
  opencv:           'OpenCV Artifacts',
};

export function ConflictAlert({ conflict, scanId, onDecision }: ConflictAlertProps) {
  const [timeLeft, setTimeLeft]   = useState(REVIEW_TIMEOUT);
  const [decision, setDecision]   = useState<'proceed' | 'reclassify' | null>(null);
  const [reason, setReason]       = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(timerRef.current!);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current!);
  }, []);

  // Auto-proceed on timeout
  useEffect(() => {
    if (timeLeft === 0 && !submitted) {
      handleSubmit('proceed', 'Auto-proceeded after timeout.');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  const severity = conflict.severity ?? 'medium';
  const cfg = severityConfig[severity];

  async function handleSubmit(
    dec: 'proceed' | 'reclassify',
    overrideReason?: string,
  ) {
    const finalReason = overrideReason ?? reason.trim();
    if (!finalReason) return;
    setSubmitting(true);
    setError(null);
    try {
      await resolveConflict(scanId, dec, finalReason);
      setSubmitted(true);
      clearInterval(timerRef.current!);
      onDecision?.(dec, finalReason);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-2 mt-3 text-sm text-success">
        <CheckCircle2 className="size-4 shrink-0" />
        <span>Decision submitted — pipeline resuming.</span>
      </div>
    );
  }

  return (
    <div className={`mt-3 rounded-lg border ${cfg.border} ${cfg.bg} p-4 space-y-3`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className={`flex items-center gap-2 font-semibold text-sm ${cfg.text}`}>
          <ShieldAlert className="size-4 shrink-0" />
          <span>
            Conflict Detected &mdash; Severity:{' '}
            <span className="font-bold">{cfg.label}</span>
            {conflict.rule_triggered && (
              <span className="ml-1 font-normal opacity-75">
                (Rule {conflict.rule_triggered})
              </span>
            )}
          </span>
        </div>
        {/* Countdown */}
        <div
          className={`flex items-center gap-1 text-xs font-mono tabular-nums ${
            timeLeft < 60 ? 'text-danger animate-pulse' : 'text-muted'
          }`}
        >
          <Clock className="size-3" />
          {formatTime(timeLeft)}
        </div>
      </div>

      {/* Reason */}
      {conflict.reason && (
        <p className="text-sm text-fg">{conflict.reason}</p>
      )}

      {/* Signals */}
      {conflict.conflicting_signals.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {conflict.conflicting_signals.map(sig => (
            <span
              key={sig}
              className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full
                         bg-card border border-border text-muted"
            >
              <Info className="size-3" />
              {signalLabels[sig] ?? sig}
            </span>
          ))}
          {conflict.confidence_gap != null && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full
                             bg-card border border-border text-muted">
              Gap: {(conflict.confidence_gap * 100).toFixed(1)}%
            </span>
          )}
        </div>
      )}

      {/* Human input */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-muted uppercase tracking-wider">
          Your reasoning <span className="text-danger">*</span>
        </label>
        <textarea
          rows={2}
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="Explain your decision before overriding the automated analysis…"
          disabled={submitting}
          className="w-full text-sm rounded-md border border-border bg-card px-3 py-2
                     text-fg placeholder:text-muted resize-none focus:outline-none
                     focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
        />
      </div>

      {/* Decisions */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => { setDecision('proceed'); handleSubmit('proceed'); }}
          disabled={submitting || !reason.trim()}
          className="flex-1 min-w-[120px] text-sm font-medium px-4 py-2 rounded-md
                     bg-success/20 border border-success/40 text-success
                     hover:bg-success/30 disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors"
        >
          {submitting && decision === 'proceed' ? 'Submitting…' : 'Proceed to Verdict'}
        </button>
        <button
          onClick={() => { setDecision('reclassify'); handleSubmit('reclassify'); }}
          disabled={submitting || !reason.trim()}
          className="flex-1 min-w-[120px] text-sm font-medium px-4 py-2 rounded-md
                     bg-warning/20 border border-warning/40 text-warning
                     hover:bg-warning/30 disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors"
        >
          {submitting && decision === 'reclassify' ? 'Submitting…' : 'Re-classify'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-xs text-danger">
          <AlertTriangle className="size-3 shrink-0" />
          {error}
        </div>
      )}

      <p className="text-xs text-muted">
        Pipeline paused. Auto-proceeds in{' '}
        <span className="font-mono">{formatTime(timeLeft)}</span> if no action is taken.
      </p>
    </div>
  );
}
