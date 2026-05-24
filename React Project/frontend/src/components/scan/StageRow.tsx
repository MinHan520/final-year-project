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
  return (
    <div className={`p-4 border-b border-border last:border-0 ${state === 'error' ? 'bg-danger/10' : ''}`}>
      <div className="flex items-start gap-4">
        <div className="mt-1">
          {state === 'pending' && <Clock className="size-5 text-muted" />}
          {state === 'running' && <Loader2 className="size-5 text-primary animate-spin" />}
          {state === 'complete' && <CheckCircle2 className="size-5 text-success" />}
          {state === 'error' && <AlertCircle className="size-5 text-danger" />}
        </div>
        <div className="flex-1 space-y-2">
          <h3 className="text-sm font-medium text-fg">{label}</h3>
          {state === 'running' && !children && (
            <div className="h-4 w-1/2 bg-muted/20 animate-pulse rounded" />
          )}
          {error && <p className="text-sm text-danger">{error}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}
