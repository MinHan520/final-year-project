import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Image as ImageIcon, Video, FileText, Mic, XCircle, File as FileIcon, Loader2, Timer } from 'lucide-react';
import { UploadDropzone } from '../components/scan/UploadDropzone';
import { ActiveScanPanel } from '../components/scan/ActiveScanPanel';
import { useChatStore } from '../stores/chat-store';
import { useScanStore } from '../stores/scan-store';
import { deleteScan } from '../api/client';
import { cn } from '@/lib/utils';

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  return `${String(Math.floor(totalSeconds / 60)).padStart(2, '0')}:${String(totalSeconds % 60).padStart(2, '0')}`;
}

const REAL_TITLE = 'AI-Generated Content Detection System';
const GLITCH_CHARS = '!<>-_\\/[]{}—=+*^?#01ABCDEF@$';

function scramble(progress: number): string {
  const revealed = Math.floor(progress * REAL_TITLE.length);
  return REAL_TITLE.split('').map((ch, i) => {
    if (i < revealed) return ch;
    if (ch === ' ') return ' ';
    return GLITCH_CHARS[Math.floor(Math.random() * GLITCH_CHARS.length)];
  }).join('');
}

const CAPABILITIES = [
  { label: 'Image Detection',         icon: ImageIcon, ready: true  },
  { label: 'Video Detection',         icon: Video,     ready: false },
  { label: 'Audio Detection',         icon: Mic,       ready: false },
  { label: 'Text / Document',         icon: FileText,  ready: false },
];

const TICKER_MSGS = [
  '[SYS] Agent initialized — forensic pipeline ready',
  '[NET] Awaiting payload upload...',
  '[AI]  AIDE model loaded — MoE inference engine online',
  '[CV]  OpenCV artifact analyzers initialized',
  '[WM]  SynthID watermark verifier ready',
  '[GEM] Gemini synthesis engine connected',
  '[CNF] Conflict resolution agent on standby',
  '[SYS] All 6 forensic stages operational',
];

export function Dashboard() {
  const { activeScanId, activeFileName, activeFileSize, previewUrl, scanStartTime, setActiveScan, clearActiveScan } = useScanStore();
  const { bindScan, reset } = useChatStore();
  const navigate  = useNavigate();

  const [elapsed,      setElapsed]      = useState<number>(0);
  const [scanFinished, setScanFinished] = useState(false);
  const [titleText,    setTitleText]    = useState(() => scramble(0));
  const [tickerIdx,    setTickerIdx]    = useState(0);
  const [tickerKey,    setTickerKey]    = useState(0);
  const rafRef = useRef<number>(0);

  // Cryptographic decode animation on mount
  useEffect(() => {
    const start = Date.now();
    const duration = 1500;
    const tick = () => {
      const progress = Math.min((Date.now() - start) / duration, 1);
      setTitleText(progress < 1 ? scramble(progress) : REAL_TITLE);
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  // Activity ticker rotation
  useEffect(() => {
    const id = setInterval(() => {
      setTickerIdx(i => (i + 1) % TICKER_MSGS.length);
      setTickerKey(k => k + 1);
    }, 3200);
    return () => clearInterval(id);
  }, []);

  // Stopwatch
  useEffect(() => {
    if (!scanStartTime || scanFinished) return;
    setElapsed(Date.now() - scanStartTime);
    const id = setInterval(() => setElapsed(Date.now() - scanStartTime!), 100);
    return () => clearInterval(id);
  }, [scanStartTime, scanFinished]);

  useEffect(() => { bindScan(activeScanId); }, [activeScanId, bindScan]);

  const handleScanCreated = (scanId: string, file: File) => {
    setActiveScan(scanId, file.name, file.size, file.type.startsWith('image/') ? URL.createObjectURL(file) : null);
  };

  const handleClearProcess = async () => {
    if (activeScanId) {
      try { await deleteScan(activeScanId); } catch (e) { console.error('Failed to abort scan:', e); }
    }
    clearActiveScan();
    reset();
  };

  const handleScanComplete = (scanId: string) => {
    setScanFinished(true);
    setTimeout(() => {
      navigate(`/scan/${scanId}`);
      clearActiveScan();
      setScanFinished(false);
      setElapsed(0);
    }, 1500);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* ── Hero header ──────────────────────────────────────────────── */}
      <header className="space-y-2">
        <div className="flex justify-between items-start">
          <div className="space-y-1">
            <p className="font-sans text-[11px] font-semibold tracking-wider text-primary">
              Forensic Analysis System v2.0
            </p>
            <h1 className="font-sans text-4xl md:text-5xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-purple-800 to-violet-500 dark:from-primary dark:via-purple-400 dark:to-indigo-500 animate-glitch-decode tracking-tight mt-2">
              {titleText}
            </h1>
            <p className="text-sm text-slate-700 dark:text-slate-300 mt-1">
              Drop a file to run the multi-agent forensic pipeline. Results appear in the live analysis panel below.
            </p>
          </div>
          {activeScanId && (
            <div className="flex items-center gap-3 shrink-0 ml-4">
              {scanStartTime && (
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gradient-to-r from-purple-500/10 to-pink-500/10 dark:from-purple-500/20 dark:to-pink-500/20 shadow-sm">
                  {!scanFinished ? (
                    <Loader2 className="size-4 text-primary animate-spin" />
                  ) : (
                    <Timer className="size-4 text-success" />
                  )}
                  <span className={`font-mono text-sm font-semibold tabular-nums ${
                    scanFinished ? 'text-success' : 'text-primary'
                  }`}>
                    {formatElapsed(elapsed)}
                  </span>
                </div>
              )}
              <button
                onClick={handleClearProcess}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-950/40 dark:text-red-400 dark:hover:bg-red-900/60 shadow-sm transition-all text-sm font-medium"
              >
                <XCircle className="size-4" />
                Clear Process
              </button>
            </div>
          )}
        </div>
      </header>

      {!activeScanId ? (
        <>
          {/* ── Activity ticker ─────────────────────────────────────── */}
          <div className="flex items-center gap-3 px-4 py-2 border-b border-slate-200 dark:border-slate-800 text-[10px] font-mono w-full mb-6 mt-2 bg-transparent">
            <div className="flex items-center gap-2 text-primary font-bold tracking-wider">
              <span className="size-1.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_var(--color-primary)]" />
              LIVE
            </div>
            <span className="text-border-strong">|</span>
            <span key={tickerKey} className="text-muted opacity-80 uppercase tracking-widest animate-ticker-fade">
              {activeScanId && scanStartTime
                ? !scanFinished
                  ? `[NET] SCAN IN PROGRESS: ${formatElapsed(elapsed)}`
                  : `[NET] SCAN COMPLETE: ${formatElapsed(elapsed)}`
                : TICKER_MSGS[tickerIdx]}
            </span>
          </div>

          {/* ── File Upload / Scan Dropzone ──────────────────────────── */}
          <UploadDropzone onScanCreated={handleScanCreated} />

          {/* ── Agent capability cards ───────────────────────────────── */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {CAPABILITIES.map(({ label, icon: Icon, ready }) => (
              <div
                key={label}
                className={cn(
                  'group agent-card flex flex-col justify-between h-28 p-4 rounded-none border transition-all duration-300 relative bg-white dark:bg-slate-900 cursor-pointer',
                  ready 
                    ? 'border-slate-200 dark:border-slate-800/60 shadow-[0_0_25px_rgba(168,85,247,0.2)]' 
                    : 'border-slate-200 dark:border-slate-800/60 hover:shadow-[0_0_25px_rgba(168,85,247,0.2)]'
                )}
                onMouseMove={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  e.currentTarget.style.setProperty('--mx', `${((e.clientX - r.left) / r.width) * 100}%`);
                  e.currentTarget.style.setProperty('--my', `${((e.clientY - r.top) / r.height) * 100}%`);
                }}
              >
                {/* Top edge active/hover accent line */}
                <div className={cn(
                  "absolute top-0 left-0 right-0 h-[2px] bg-purple-600 transition-opacity duration-300 pointer-events-none",
                  ready ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                )} />
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'size-1.5 rounded-full',
                        ready ? 'bg-success shadow-[0_0_8px_var(--color-success)]' : 'bg-muted-foreground'
                      )}
                    />
                    <Icon className="size-4 text-muted" />
                  </div>
                  <span
                    className={cn(
                      'font-mono text-[8px] tracking-widest uppercase px-1.5 py-0.5 border rounded-none',
                      ready
                        ? 'text-success border-success/30 bg-success/5'
                        : 'text-muted-foreground border-border bg-bg-elevated/40'
                    )}
                  >
                    {ready ? '[READY]' : '[OFFLINE]'}
                  </span>
                </div>
                
                <div className="mt-2 space-y-1.5">
                  <span className="text-xs font-semibold text-fg block">
                    {label}
                  </span>

                  {ready ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[7px] font-mono text-primary/75">INF: 98.2ms</span>
                      <span className="text-[7px] font-mono text-muted-foreground">|</span>
                      <div className="flex-1 h-[2px] bg-border-strong overflow-hidden relative">
                        <div className="absolute top-0 left-0 h-full w-[65%] bg-primary animate-pulse" />
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 opacity-40">
                      <span className="text-[7px] font-mono text-muted">SIG: INACTIVE</span>
                      <span className="text-[7px] font-mono text-muted-foreground">|</span>
                      <div className="flex-1 h-[2px] bg-border" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </section>
        </>
      ) : (
        <section className="space-y-6">
          {/* Active file card */}
          <div className="flex items-center gap-4 p-4 bg-slate-50/50 dark:bg-slate-900/40 rounded-2xl shadow-[0_0_30px_rgba(168,85,247,0.08)]">
            <div className="shrink-0 size-16 bg-bg-elevated rounded-xl flex items-center justify-center overflow-hidden shadow-sm">
              {previewUrl
                ? <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
                : <FileIcon className="size-8 text-muted" />
              }
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-fg truncate">{activeFileName || 'Uploaded File'}</p>
              <p className="text-xs text-muted font-mono mt-0.5">
                {activeFileSize ? (activeFileSize / 1024 / 1024).toFixed(2) : '0.00'} MB
              </p>
            </div>
          </div>

          <ActiveScanPanel scanId={activeScanId} onComplete={handleScanComplete} />
        </section>
      )}
    </div>
  );
}
