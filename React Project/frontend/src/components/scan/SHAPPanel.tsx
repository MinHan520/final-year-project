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
    <div className="mt-6 border border-border rounded-card bg-card overflow-hidden">
      <div className="p-4 border-b border-border bg-card/80">
        <h3 className="font-display font-medium text-fg">SHAP Explainability</h3>
        <p className="text-xs text-muted mt-1">Pixel-level attribution showing which regions pushed the model's decision.</p>
      </div>
      <div className="p-6">
        {shap?.heatmap_png_b64 ? (
          <div className="space-y-4">
            <img 
              src={`data:image/png;base64,${shap.heatmap_png_b64}`} 
              alt="SHAP Heatmap" 
              className="max-w-full rounded-md border border-border bg-black mx-auto"
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
              className="inline-flex items-center gap-2 h-9 px-4 rounded-md bg-primary/80 text-primary-foreground text-sm font-medium hover:bg-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
