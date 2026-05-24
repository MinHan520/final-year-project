import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2, AlertTriangle, Brain, Shield, Layers, FileSearch } from 'lucide-react';
import { useState, useEffect } from 'react';
import { getScan } from '../api/client';
import { ActiveScanPanel } from '../components/scan/ActiveScanPanel';
import { SHAPPanel } from '../components/scan/SHAPPanel';
import { RiskScoreCard } from '../components/scan/RiskScoreCard';
import { ForensicMapTrio } from '../components/scan/ForensicMapTrio';
import { useChatStore } from '../stores/chat-store';
import type { ScanRow } from '../api/types';

const TABS = [
  { id: 'overview', label: 'AIDE Detection', icon: Brain },
  { id: 'forensics', label: 'Low-Level Artifacts', icon: Layers },
  { id: 'synthid', label: 'SynthID', icon: Shield },
  { id: 'evaluation', label: 'Agentic Evaluation', icon: FileSearch },
] as const;

type TabId = typeof TABS[number]['id'];

export function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>();
  const { bindScan, reset } = useChatStore();
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  useEffect(() => {
    bindScan(scanId || null);
    return () => reset();
  }, [scanId, bindScan, reset]);

  const { data: scan, isLoading, error } = useQuery<ScanRow>({
    queryKey: ['scan', scanId],
    queryFn: () => getScan(scanId!),
    enabled: !!scanId,
    refetchInterval: (query) => {
      // Keep polling while the scan is still running
      const status = query.state.data?.status;
      return status === 'running' || status === 'queued' ? 2000 : false;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-8 text-primary animate-spin" />
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="p-6 bg-danger/10 border border-danger/20 rounded-card flex items-center gap-3 text-danger max-w-6xl mx-auto">
        <AlertTriangle className="size-6" />
        <div>
          <h2 className="font-medium">Failed to load scan</h2>
          <p className="text-sm opacity-80">{error instanceof Error ? error.message : 'Unknown error'}</p>
        </div>
      </div>
    );
  }

  if (scan.status === 'running' || scan.status === 'queued') {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-fg transition-colors">
          <ArrowLeft className="size-4" /> Back to Dashboard
        </Link>
        <ActiveScanPanel scanId={scan.scan_id} />
      </div>
    );
  }

  const summary = scan.result;
  const detectedType = summary?.object_classification?.media_type || scan.media_type;
  const isImage = detectedType === 'image' || detectedType?.startsWith('image/');

  if (!isImage) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-fg transition-colors">
          <ArrowLeft className="size-4" /> Back to Dashboard
        </Link>

        <div className="flex justify-between items-end">
          <div>
            <h1 className="font-display text-3xl font-semibold text-fg mb-1">Forensic Report</h1>
            <p className="text-sm text-muted font-mono">{scan.filename}</p>
          </div>
          <div className="text-xs text-muted uppercase tracking-wider font-bold">
            Status:{' '}
            <span className={scan.status === 'failed' ? 'text-danger' : 'text-success'}>
              {scan.status}
            </span>
          </div>
        </div>

        <div className="rounded-card border border-border bg-card overflow-hidden p-16 flex flex-col items-center justify-center text-center space-y-4 mt-8">
          <div className="size-16 rounded-full bg-primary/10 flex items-center justify-center mb-2">
            <AlertTriangle className="size-8 text-primary" />
          </div>
          <h2 className="font-display text-xl font-semibold text-fg capitalize">{detectedType} Detected</h2>
          <p className="text-muted max-w-md">
            Features for {detectedType} forensics are coming soon. Please come again next time.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-fg transition-colors">
        <ArrowLeft className="size-4" /> Back to Dashboard
      </Link>

      <div className="flex justify-between items-end">
        <div>
          <h1 className="font-display text-3xl font-semibold text-fg mb-1">Forensic Report</h1>
          <p className="text-sm text-muted font-mono">{scan.filename}</p>
        </div>
        <div className="text-xs text-muted uppercase tracking-wider font-bold">
          Status:{' '}
          <span className={scan.status === 'failed' ? 'text-danger' : 'text-success'}>
            {scan.status}
          </span>
        </div>
      </div>

      {scan.error && scan.status === 'failed' && (
        <div className="p-4 bg-danger/10 border border-danger/20 rounded-card flex items-center gap-3 text-danger">
          <AlertTriangle className="size-5" />
          <p className="text-sm font-medium">{scan.error}</p>
        </div>
      )}

      {summary?.greeting?.text && (
        <div className="p-4 rounded-card border border-border bg-card/60">
          <p className="text-sm text-muted italic">{summary.greeting.text}</p>
        </div>
      )}

      <div className="flex gap-1 p-1 rounded-lg bg-bg-elevated border border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`
              flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md
              text-xs font-medium tracking-wide uppercase transition-all
              ${activeTab === id
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'text-muted hover:text-fg hover:bg-card/60'
              }
            `}
          >
            <Icon className="size-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      <div className="rounded-card border border-border bg-card overflow-hidden">
        {activeTab === 'overview' && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="font-display text-lg font-semibold text-fg mb-1">AIDE Mixture-of-Experts Detection</h2>
              <p className="text-sm text-muted">
                The AIDE model uses a 5-stream architecture (4 DCT frequency bands + spatial) with ResNet-50 and ConvNeXt backbones
                to classify whether this image was generated by AI.
              </p>
            </div>

            {summary?.aide?.success ? (
              <div className="flex flex-col items-center gap-6 py-6">
                <div className="max-w-[280px] w-full">
                  <RiskScoreCard aide={summary.aide} />
                </div>
                <p className="text-xs text-muted text-center max-w-md">
                  Score ≥ 80% = HIGH RISK · 50–80% = AI GENERATED · 30–50% = INCONCLUSIVE · &lt;30% = AUTHENTIC
                </p>
              </div>
            ) : (
              <div className="p-4 bg-warning/10 border border-warning/20 rounded-md text-sm text-warning">
                AIDE detection was not available for this scan.
                {summary?.aide?.error && <span className="block mt-1 opacity-80">{summary.aide.error}</span>}
              </div>
            )}
          </div>
        )}

        {activeTab === 'forensics' && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="font-display text-lg font-semibold text-fg mb-1">Low-Level Artifact Analysis</h2>
              <p className="text-sm text-muted">
                OpenCV-based forensic maps expose artifacts invisible to the naked eye: noise residuals from camera sensors,
                edge gradient anomalies, and compression (ELA) inconsistencies.
              </p>
            </div>

            {summary?.opencv_maps ? (
              <ForensicMapTrio maps={summary.opencv_maps} comments={summary.opencv_commentary} />
            ) : (
              <div className="p-4 bg-muted/10 border border-border rounded-md text-sm text-muted">
                Forensic maps were not generated for this scan.
              </div>
            )}
          </div>
        )}

        {activeTab === 'synthid' && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="font-display text-lg font-semibold text-fg mb-1">SynthID Watermark Detection</h2>
              <p className="text-sm text-muted">
                SynthID is Google's imperceptible watermarking system embedded in AI-generated images.
                If detected, it provides cryptographic proof of AI origin.
              </p>
            </div>

            {summary?.synthid ? (
              <div className="space-y-4">
                <div className="flex items-center gap-6 p-6 rounded-lg bg-bg-elevated border border-border">
                  <div className={`
                    size-16 rounded-full flex items-center justify-center text-2xl
                    ${summary.synthid.watermark_found
                      ? 'bg-danger/20 text-danger'
                      : 'bg-success/20 text-success'
                    }
                  `}>
                    {summary.synthid.watermark_found ? '⚠' : '✓'}
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-fg">
                      Watermark {summary.synthid.watermark_found ? 'Detected' : 'Not Detected'}
                    </p>
                    {summary.synthid.synth_id_detected && (
                      <p className="text-sm text-danger font-medium">
                        SynthID confirmed — this image was generated by a Google AI model.
                      </p>
                    )}
                  </div>
                </div>

                {summary.synthid.reasoning && (
                  <div className="p-4 rounded-md bg-card/60 border border-border">
                    <p className="text-xs uppercase tracking-wider text-muted font-medium mb-2">Analysis</p>
                    <p className="text-sm text-fg leading-relaxed">{summary.synthid.reasoning}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-muted/10 border border-border rounded-md text-sm text-muted">
                SynthID analysis was not available for this scan.
              </div>
            )}
          </div>
        )}

        {activeTab === 'evaluation' && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="font-display text-lg font-semibold text-fg mb-1">Agentic Forensic Evaluation</h2>
              <p className="text-sm text-muted">
                Gemini synthesizes all detection signals into a plain-English forensic verdict,
                identifying specific visual clues and educating the user on what to look for.
              </p>
            </div>

            {summary?.eval?.text ? (
              <div className="p-6 rounded-lg bg-bg-elevated border border-border">
                <div className="text-sm text-fg whitespace-pre-wrap leading-relaxed">
                  {summary.eval.text.split(/(\*\*.*?\*\*)/g).map((part, i) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                      return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
                    }
                    return <span key={i}>{part}</span>;
                  })}
                </div>
              </div>
            ) : (
              <div className="p-4 bg-muted/10 border border-border rounded-md text-sm text-muted">
                Agentic evaluation was not available for this scan.
                {summary?.eval?.error && <span className="block mt-1 opacity-80">{summary.eval.error}</span>}
              </div>
            )}
          </div>
        )}
      </div>

      <SHAPPanel scanId={scan.scan_id} summary={summary} />
    </div>
  );
}
