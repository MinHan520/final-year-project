import type { AIDEStageResult } from '../../api/types';

export function RiskScoreCard({ aide }: { aide: AIDEStageResult }) {
  if (!aide.success) return null;
  const score = aide.score;
  const pct = (score * 100).toFixed(1);

  let label = 'AUTHENTIC';
  let colorClass = 'bg-success text-success-foreground border-success';
  let glow = '';

  if (score >= 0.8) {
    label = '⚠ HIGH RISK';
    colorClass = 'bg-critical text-primary-foreground border-critical';
    glow = 'animate-pulse shadow-[0_0_20px_rgba(220,38,38,0.5)]';
  } else if (score >= 0.5) {
    label = 'AI GENERATED';
    colorClass = 'bg-danger text-primary-foreground border-danger';
  } else if (score >= 0.3) {
    label = 'INCONCLUSIVE';
    colorClass = 'bg-warning text-primary-foreground border-warning';
  }

  return (
    <div className={`rounded-xl border p-6 flex flex-col items-center justify-center gap-2 ${colorClass} ${glow}`}>
      <div className="text-sm font-medium tracking-widest">{label}</div>
      <div className="text-4xl font-display font-bold">{pct}%</div>
      <div className="text-xs opacity-80">AI Probability</div>
    </div>
  );
}
