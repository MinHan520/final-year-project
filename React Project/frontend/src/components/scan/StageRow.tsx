import type { ReactNode } from 'react';
import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import type { StageState } from '../../hooks/useScanStream';

interface StageRowProps {
  label: string;
  state: StageState;
  children?: ReactNode;
  error?: string;
}

export function StageRow({ label, state, children, error }: StageRowProps) {
  const isPending  = state === 'pending';
  const isRunning  = state === 'running';
  const isComplete = state === 'complete';
  const isError    = state === 'error';

  return (
    <div
      className={[
        'p-4 rounded-xl transition-all duration-500',
        isPending  ? 'bg-slate-50/50 dark:bg-slate-900/20 opacity-40' : '',
        isRunning  ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/40' : '',
        isComplete ? 'bg-slate-50 dark:bg-slate-800/40 text-slate-900 dark:text-slate-100' : '',
        isError    ? 'bg-danger/10 text-danger' : '',
      ].join(' ')}
    >
      <div className="flex items-start gap-4">
        {/* State icon */}
        <div className="mt-0.5 shrink-0">
          {isPending && <Clock className="size-5 text-muted" />}

          {isRunning && (
            <div className="relative size-5">
              <Loader2 className="size-5 text-white animate-spin relative z-10" />
              <span className="absolute inset-0 rounded-full bg-white/25 animate-ping" />
            </div>
          )}

          {isComplete && (
            <CheckCircle2
              className="size-5 text-success"
              style={{ filter: 'drop-shadow(0 0 7px rgba(16,185,129,0.7))' }}
            />
          )}

          {isError && <AlertCircle className="size-5 text-danger" />}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-2">
          <h3
            className={[
              'text-sm font-medium transition-all duration-300',
              isPending  ? 'text-muted'                  : '',
              isRunning  ? 'text-white font-semibold'    : '',
              isComplete ? 'text-slate-900 dark:text-slate-100' : '',
              isError    ? 'text-danger'                 : '',
            ].join(' ')}
          >
            {label}
          </h3>

          {/* Running: shimmer progress bar */}
          {isRunning && !children && (
            <div className="h-1 w-2/5 rounded-full bg-white/20 overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/60 to-transparent animate-shimmer" />
            </div>
          )}

          {error && <p className="text-sm text-danger font-mono">{error}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}
