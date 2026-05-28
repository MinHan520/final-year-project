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
import { cn } from '../lib/utils';
import type { ScanRow } from '../api/types';

const TABS = [
  {
    id: 'evaluation',
    label: 'Agentic Evaluation',
    icon: FileSearch,
    activeClass: 'bg-pink-600/90 text-white shadow-[0_0_20px_rgba(219,39,119,0.55)]',
    hoverClass: 'hover:bg-pink-500/10 hover:text-pink-300',
  },
  {
    id: 'overview',
    label: 'AIDE Detection',
    icon: Brain,
    activeClass: 'bg-purple-600/90 text-white shadow-[0_0_20px_rgba(147,51,234,0.55)]',
    hoverClass: 'hover:bg-purple-500/10 hover:text-purple-300',
  },
  {
    id: 'forensics',
    label: 'Low-Level Artifacts',
    icon: Layers,
    activeClass: 'bg-cyan-600/90 text-white shadow-[0_0_20px_rgba(8,145,178,0.55)]',
    hoverClass: 'hover:bg-cyan-500/10 hover:text-cyan-300',
  },
  {
    id: 'synthid',
    label: 'SynthID',
    icon: Shield,
    activeClass: 'bg-emerald-600/90 text-white shadow-[0_0_20px_rgba(5,150,105,0.55)]',
    hoverClass: 'hover:bg-emerald-500/10 hover:text-emerald-300',
  },
] as const;

type TabId = typeof TABS[number]['id'];

export function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>();
  const { bindScan } = useChatStore();
  const [activeTab, setActiveTab] = useState<TabId>('evaluation');

  useEffect(() => {
    bindScan(scanId || null);
    return () => bindScan(null);
  }, [scanId, bindScan]);

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

  // Verdict banner config — used in the Agentic Evaluation tab
  const verdictScore = scan.score ?? summary?.aide?.score ?? null;
  const elapsedSeconds = ((new Date(scan.updated_at).getTime() - new Date(scan.created_at).getTime()) / 1000).toFixed(1);
  const VERDICT_CONFIGS = {
    HIGH_RISK:           { label: 'Highly Likely AI-Generated',             bg: 'bg-red-500/10 border border-red-500/25 shadow-[0_0_25px_rgba(220,38,38,0.2)]',                text: 'text-red-700 dark:text-red-300',       pulse: true  },
    AI_GENERATED:        { label: 'AI-Generated',                           bg: 'bg-red-500/10 border border-red-500/20',                                                        text: 'text-red-600 dark:text-red-400',       pulse: false },
    WATERMARK_CONFIRMED: { label: 'AI-Generated (Watermark Confirmed)',      bg: 'bg-purple-500/10 border border-purple-500/30 shadow-[0_0_25px_rgba(168,85,247,0.25)]',         text: 'text-purple-700 dark:text-purple-300', pulse: true  },
    HIGH_CHANCES_AI:     { label: 'High Chances AI-Generated',              bg: 'bg-orange-500/10 border border-orange-500/20 shadow-[0_0_20px_rgba(249,115,22,0.15)]',         text: 'text-orange-600 dark:text-orange-400', pulse: false },
    INCONCLUSIVE:        { label: 'Inconclusive — Likely Not AI-Generated', bg: 'bg-amber-500/10 border border-amber-500/20',                                                    text: 'text-amber-600 dark:text-amber-400',   pulse: false },
    AUTHENTIC:           { label: 'Authentic (Not AI-Generated)',            bg: 'bg-green-500/10 border border-green-500/20 shadow-[0_0_20px_rgba(16,185,129,0.15)]',           text: 'text-green-700 dark:text-green-400',   pulse: false },
  } as const;
  const verdictCfg = scan.risk_label ? VERDICT_CONFIGS[scan.risk_label] : null;

  if (!isImage) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-fg transition-colors">
          <ArrowLeft className="size-4" /> Back to Dashboard
        </Link>

        <div className="flex justify-between items-end">
          <div>
            <h1 className="font-display text-3xl font-semibold mb-1 text-gradient-futuristic">Forensic Report</h1>
            <p className="text-sm text-muted font-mono">{scan.filename}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted uppercase tracking-wider font-bold">Status</span>
            <span className={cn(
              'text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border',
              scan.status === 'failed'
                ? 'bg-red-500/15 text-red-400 border-red-500/30'
                : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.35)]',
            )}>
              {scan.status}
            </span>
          </div>
        </div>

        <div className="rounded-3xl bg-gradient-to-br from-purple-50/50 to-pink-50/50 dark:from-purple-950/20 dark:to-pink-950/20 p-16 flex flex-col items-center justify-center text-center space-y-4 mt-8 shadow-[0_0_40px_rgba(168,85,247,0.15)]">
          <div className="size-16 rounded-full bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center mb-2 shadow-[inset_0_0_20px_rgba(236,72,153,0.2),_0_0_20px_rgba(168,85,247,0.2)]">
            <AlertTriangle className="size-8 text-purple-500" />
          </div>
          <h2 className="font-display text-xl font-semibold capitalize bg-clip-text text-transparent bg-gradient-to-r from-purple-700 to-pink-500 dark:from-purple-400 dark:to-pink-400">
            {detectedType} Detected
          </h2>
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
          <h1 className="font-display text-3xl font-semibold mb-1 text-gradient-futuristic">Forensic Report</h1>
          <p className="text-sm text-muted font-mono">{scan.filename}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted uppercase tracking-wider font-bold">Status</span>
          <span className={cn(
            'text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border',
            scan.status === 'failed'
              ? 'bg-red-500/15 text-red-400 border-red-500/30'
              : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.35)]',
          )}>
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

      <div className="flex gap-1 p-1 rounded-xl bg-gradient-to-r from-purple-950/30 via-pink-950/20 to-slate-900/40 dark:from-purple-950/30 dark:via-pink-950/20 dark:to-slate-900/40 border border-purple-500/10 shadow-[0_0_20px_rgba(168,85,247,0.08)]">
        {TABS.map(({ id, label, icon: Icon, activeClass, hoverClass }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-md',
              'text-xs font-medium tracking-wide uppercase transition-all duration-200',
              activeTab === id
                ? activeClass
                : cn('text-muted', hoverClass),
            )}
          >
            <Icon className="size-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      <div className="rounded-2xl bg-card overflow-hidden shadow-[0_0_40px_rgba(168,85,247,0.12),_0_0_80px_rgba(236,72,153,0.06)]">
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

            {summary?.synthid ? (() => {
                const conf = summary.synthid.confidence ?? 0;
                const wmFound = summary.synthid.watermark_found;
                // High AI confidence (≥ 0.95) or watermark → full red alert
                const isHighAI = wmFound || conf >= 0.95;
                const confLabel = conf >= 0.95 ? 'AI-GEN CONFIDENCE' : 'CONFIDENCE';

                const bannerBg = isHighAI
                  ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900/50'
                  : 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900/50';
                const iconBg = isHighAI
                  ? 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400'
                  : 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400';
                const titleColor = isHighAI
                  ? 'text-red-700 dark:text-red-400'
                  : 'text-green-700 dark:text-green-400';
                const confColor = isHighAI
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-green-700 dark:text-green-400';
                const barColor = conf >= 0.85 ? 'bg-red-500' : conf >= 0.50 ? 'bg-amber-400' : 'bg-green-500';
                const tierLabel = conf >= 0.85 ? 'HIGH' : conf >= 0.50 ? 'MEDIUM' : 'LOW';

                return (
                  <div className="space-y-4">
                    {/* Status + Confidence Banner */}
                    <div className={`flex items-center gap-6 p-6 rounded-2xl shadow-sm border ${bannerBg}`}>
                      <div className={`size-16 rounded-full flex items-center justify-center text-2xl shadow-inner shrink-0 ${iconBg}`}>
                        {wmFound ? '⚠' : isHighAI ? '⚠' : '✓'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xl font-bold ${titleColor}`}>
                          Watermark {wmFound ? 'Detected' : 'Not Detected'}
                        </p>
                        {summary.synthid.synth_id_detected && (
                          <p className="text-sm text-red-600 dark:text-red-400 font-medium mt-1">
                            SynthID confirmed — this image was generated by a Google AI model.
                          </p>
                        )}
                        {!wmFound && conf >= 0.95 && (
                          <p className="text-sm text-red-600 dark:text-red-400 font-medium mt-1">
                            No watermark found, but visual analysis indicates very high AI generation probability.
                          </p>
                        )}
                      </div>
                      {/* Confidence Badge */}
                      {summary.synthid.confidence !== undefined && (
                        <div className="text-right shrink-0">
                          <p className="text-xs font-bold uppercase tracking-widest text-muted mb-0.5">{confLabel}</p>
                          <p className={`text-3xl font-mono font-bold tabular-nums ${confColor}`}>
                            {(conf * 100).toFixed(1)}%
                          </p>
                          <p className={`text-xs mt-0.5 font-semibold ${isHighAI ? 'text-red-500' : 'text-muted'}`}>
                            {tierLabel}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Confidence Bar */}
                    {summary.synthid.confidence !== undefined && (
                      <div className="px-1">
                        <div className="flex justify-between text-xs text-muted mb-1.5">
                          <span className={isHighAI ? 'text-red-500 font-semibold' : ''}>
                            {conf >= 0.95 ? 'AI-Gen Probability' : 'AI Probability'}
                          </span>
                          <span className={isHighAI ? 'text-red-500 font-semibold' : ''}>
                            {(conf * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted/20 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-700 ${barColor}`}
                            style={{ width: `${(conf * 100).toFixed(1)}%` }}
                          />
                        </div>
                      </div>
                    )}


                {summary.synthid.reasoning && (
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50 shadow-sm">
                    <p className="text-xs uppercase tracking-wider text-muted font-medium mb-2">Analysis</p>
                    <p className="text-sm text-fg leading-relaxed">{summary.synthid.reasoning}</p>
                  </div>
                )}
                  </div>
                );
              })() : (
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

            {/* ── Final Verdict Banner ── */}
            {verdictCfg && (
              <div className={cn(
                'rounded-2xl p-5 flex items-center gap-5 transition-all',
                verdictCfg.bg,
                verdictCfg.pulse && 'animate-pulse',
              )}>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono uppercase tracking-widest text-muted mb-1">Final Verdict</p>
                  <p className={cn('text-xl font-bold font-display leading-tight', verdictCfg.text)}>
                    {verdictCfg.label}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs font-mono uppercase tracking-widest text-muted mb-1">Processing Time</p>
                  <p className={cn('text-4xl font-display font-bold tabular-nums', verdictCfg.text)}>
                    {elapsedSeconds}s
                  </p>
                </div>
                {verdictScore !== null && (
                  <div className="text-right shrink-0">
                    <p className="text-xs font-mono uppercase tracking-widest text-muted mb-1">AI Probability</p>
                    <p className={cn('text-4xl font-display font-bold tabular-nums', verdictCfg.text)}>
                      {(verdictScore * 100).toFixed(1)}%
                    </p>
                  </div>
                )}
              </div>
            )}

            {summary?.eval?.text ? (
              <div className="p-6 rounded-xl bg-gradient-to-br from-purple-950/40 via-fuchsia-950/30 to-slate-950/50 border border-purple-500/20 shadow-[0_0_30px_rgba(168,85,247,0.15),_0_0_60px_rgba(236,72,153,0.08)]">
                <div className="flex items-center gap-2 mb-4">
                  <div className="h-0.5 w-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500" />
                  <span className="text-xs uppercase tracking-wider text-purple-400 font-semibold">AI Forensic Verdict</span>
                  <div className="h-0.5 flex-1 rounded-full bg-gradient-to-r from-pink-500/40 to-transparent" />
                </div>
                <div className="text-sm text-fg whitespace-pre-wrap leading-relaxed">
                  {summary.eval.text.split(/(\*\*.*?\*\*)/g).map((part, i) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                      return (
                        <strong key={i} className="font-bold text-gradient-bold">
                          {part.slice(2, -2)}
                        </strong>
                      );
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
