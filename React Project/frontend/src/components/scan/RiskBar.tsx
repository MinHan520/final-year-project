import type { RiskLabel } from '../../api/types';

export function RiskBar({ score, label }: { score: number | null; label: RiskLabel | null }) {
  if (score === null) return <span className="text-muted">-</span>;
  
  const pct = (score * 100).toFixed(0);
  let colorClass = 'bg-success';
  let textClass = 'text-success';
  
  if (label === 'HIGH_RISK') {
    colorClass = 'bg-critical';
    textClass = 'text-critical';
  } else if (label === 'AI_GENERATED') {
    colorClass = 'bg-danger';
    textClass = 'text-danger';
  } else if (label === 'INCONCLUSIVE') {
    colorClass = 'bg-warning';
    textClass = 'text-warning';
  }

  return (
    <div className="flex items-center gap-3 w-40">
      <div className="h-1.5 flex-1 bg-card rounded-full overflow-hidden">
        <div className={`h-full ${colorClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-bold w-10 ${textClass}`}>{pct}%</span>
    </div>
  );
}
