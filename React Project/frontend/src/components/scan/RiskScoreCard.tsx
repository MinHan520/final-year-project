import type { AIDEStageResult } from '../../api/types';

export function RiskScoreCard({ aide }: { aide: AIDEStageResult }) {
  if (!aide.success) return null;
  const score = aide.score;
  const pct = (score * 100).toFixed(1);

  let label = 'AUTHENTIC';
  let colorClass =
    'bg-green-50 text-green-700 border border-green-200 dark:bg-green-950/40 dark:text-green-400 dark:border-green-800/60';
  let glow = '';

  if (score >= 0.8) {
    label = '⚠ HIGH RISK';
    colorClass =
      'bg-red-100 text-red-800 border border-red-300 dark:bg-red-950/60 dark:text-red-300 dark:border-red-700/60 shadow-[0_0_30px_rgba(220,38,38,0.45)]';
    glow = 'animate-pulse';
  } else if (score >= 0.5) {
    label = 'AI GENERATED';
    colorClass =
      'bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-800/60 shadow-[0_0_20px_rgba(239,68,68,0.35)]';
  } else if (score >= 0.3) {
    label = 'INCONCLUSIVE';
    colorClass =
      'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800/60 shadow-[0_0_20px_rgba(245,158,11,0.25)]';
  }

  return (
    <div className={`rounded-2xl p-6 flex flex-col items-center justify-center gap-2 ${colorClass} ${glow}`}>
      <div className="text-sm font-medium tracking-widest">{label}</div>
      <div className="text-4xl font-display font-bold">{pct}%</div>
      <div className="text-xs opacity-70">AI Probability</div>
    </div>
  );
}
