import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { runShap } from '../../api/client';
import type { ScanSummary } from '../../api/types';

interface SHAPPanelProps {
  scanId: string;
  summary: ScanSummary | null;
}

export function SHAPPanel({ scanId, summary }: SHAPPanelProps) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const handleRunShap = async () => {
    setIsPending(true);
    setError(null);
    try {
      const updatedRow = await runShap(scanId);
      queryClient.setQueryData(['scan', scanId], updatedRow);
    } catch (err: any) {
      setError(err.message || 'Failed to compute SHAP heatmap');
    } finally {
      setIsPending(false);
    }
  };

  const shap = summary?.shap;

  return (
    <div className="mt-6 rounded-2xl bg-card overflow-hidden shadow-[0_0_40px_rgba(168,85,247,0.12),_0_0_80px_rgba(236,72,153,0.06)]">
      <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-950/40 dark:to-pink-950/30 border-b border-purple-500/15">
        <div className="flex items-center gap-2 mb-0.5">
          <div className="h-0.5 w-5 rounded-full bg-gradient-to-r from-purple-500 to-cyan-400" />
          <h3 className="font-display font-semibold text-fg">SHAP Explainability</h3>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Pixel-level attribution showing which regions pushed the model's decision.</p>
      </div>
      <div className="p-6">
        {shap?.heatmap_png_b64 ? (
          <div className="space-y-4">
            <img
              src={`data:image/png;base64,${shap.heatmap_png_b64}`}
              alt="SHAP Heatmap"
              className="max-w-full rounded-2xl mx-auto shadow-[0_0_30px_rgba(168,85,247,0.25),_0_0_60px_rgba(236,72,153,0.12)]"
            />
            {shap.success && <p className="text-xs text-muted text-center">Computed with {shap.max_evals} evaluations.</p>}
            {!shap.success && <p className="text-sm text-danger text-center">{shap.error}</p>}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 space-y-4 text-center">
            <p className="text-sm text-muted max-w-md">
              SHAP computation is expensive and can take 5–30 seconds depending on image size.
              Run it on-demand to see a pixel-level attribution heatmap.
            </p>
            {error && <p className="text-sm text-danger">{error}</p>}
            <button
              onClick={handleRunShap}
              disabled={isPending}
              className="inline-flex items-center gap-2 h-9 px-5 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 text-white text-sm font-semibold hover:from-purple-500 hover:to-pink-500 shadow-[0_0_20px_rgba(168,85,247,0.4)] hover:shadow-[0_0_30px_rgba(236,72,153,0.5)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending && <Loader2 className="size-4 animate-spin" />}
              {isPending ? 'Computing SHAP...' : 'Run SHAP Explainability'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
