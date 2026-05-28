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
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {CAPABILITIES.map(({ label, icon: Icon, ready }) => (
              <div
                key={label}
                className={cn(
                  'group agent-card flex flex-col justify-between h-32 p-5 rounded-2xl border transition-all duration-300 relative bg-white/60 dark:bg-slate-900/60 backdrop-blur-md cursor-pointer overflow-hidden',
                  ready 
                    ? 'border-purple-500/30 shadow-[0_8px_30px_rgba(168,85,247,0.12)] hover:shadow-[0_12px_40px_rgba(168,85,247,0.2)] hover:-translate-y-1' 
                    : 'border-slate-200/50 dark:border-slate-800/50 shadow-sm hover:border-purple-500/20 hover:shadow-[0_8px_30px_rgba(168,85,247,0.08)] hover:-translate-y-1 opacity-90'
                )}
                onMouseMove={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  e.currentTarget.style.setProperty('--mx', `${((e.clientX - r.left) / r.width) * 100}%`);
                  e.currentTarget.style.setProperty('--my', `${((e.clientY - r.top) / r.height) * 100}%`);
                }}
              >
                {/* Top edge active/hover accent line */}
                <div className={cn(
                  "absolute top-0 left-0 right-0 h-1 bg-gradient-to-r transition-all duration-500 pointer-events-none",
                  ready 
                    ? "from-purple-500 to-pink-500 opacity-100" 
                    : "from-slate-400 to-slate-500 opacity-0 group-hover:opacity-40 group-hover:from-purple-400 group-hover:to-pink-400"
                )} />
                
                <div className="flex items-center justify-between w-full relative z-10">
                  <div className={cn(
                    "p-2 rounded-xl transition-colors duration-300",
                    ready ? "bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400" : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 group-hover:bg-purple-50 dark:group-hover:bg-purple-900/20 group-hover:text-purple-500"
                  )}>
                    <Icon className="size-5" />
                  </div>
                  <span
                    className={cn(
                      'font-sans text-[10px] font-bold tracking-widest uppercase px-3 py-1 rounded-full shadow-inner transition-colors duration-300',
                      ready
                        ? 'text-purple-700 dark:text-purple-300 bg-purple-100/80 dark:bg-purple-900/50'
                        : 'text-slate-500 dark:text-slate-400 bg-slate-100/80 dark:bg-slate-800/80'
                    )}
                  >
                    {ready ? 'Online' : 'Offline'}
                  </span>
                </div>
                
                <div className="mt-3 relative z-10 space-y-2">
                  <span className={cn(
                    "text-sm font-bold block transition-colors duration-300",
                    ready ? "text-slate-800 dark:text-slate-100" : "text-slate-600 dark:text-slate-300 group-hover:text-slate-800 dark:group-hover:text-slate-100"
                  )}>
                    {label}
                  </span>

                  {ready ? (
                    <div className="flex items-center">
                      <div className="flex-1 h-1.5 rounded-full bg-purple-100 dark:bg-purple-950 overflow-hidden relative">
                        <div className="absolute top-0 left-0 h-full w-[65%] bg-gradient-to-r from-purple-500 to-pink-500 animate-pulse rounded-full shadow-[0_0_10px_rgba(236,72,153,0.5)]" />
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <div className="flex-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden relative">
                        <div className="absolute top-0 left-0 h-full w-[30%] bg-slate-300 dark:bg-slate-700 rounded-full opacity-50 group-hover:w-[50%] transition-all duration-500" />
                      </div>
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
