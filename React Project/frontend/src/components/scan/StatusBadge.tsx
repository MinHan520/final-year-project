import type { ScanStatus, RiskLabel } from '../../api/types';

export function StatusBadge({ status, risk_label }: { status: ScanStatus; risk_label: RiskLabel | null }) {
  if (status === 'queued') return <span className="text-muted text-xs uppercase tracking-wider font-bold">QUEUED</span>;
  if (status === 'running') return <span className="text-primary text-xs uppercase tracking-wider font-bold animate-pulse">RUNNING</span>;
  if (status === 'failed') return <span className="text-danger text-xs uppercase tracking-wider font-bold">FAILED</span>;
  
  let colorClass = 'text-success';
  let labelText = 'AUTHENTIC';
  
  if (risk_label === 'HIGH_RISK') {
    colorClass = 'text-critical';
    labelText = 'HIGH PROBABILITY';
  } else if (risk_label === 'AI_GENERATED') {
    colorClass = 'text-danger';
    labelText = 'AI GENERATED';
  } else if (risk_label === 'INCONCLUSIVE') {
    colorClass = 'text-warning';
    labelText = 'INCONCLUSIVE';
  }

  return <span className={`${colorClass} text-xs uppercase tracking-wider font-bold`}>{labelText}</span>;
}
