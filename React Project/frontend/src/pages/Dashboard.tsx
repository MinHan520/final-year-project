import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Image as ImageIcon, Video, FileText, Mic, XCircle, File as FileIcon } from 'lucide-react';
import { UploadDropzone } from '../components/scan/UploadDropzone';
import { ActiveScanPanel } from '../components/scan/ActiveScanPanel';
import { useChatStore } from '../stores/chat-store';

const CAPABILITIES = [
  { label: 'IMAGE SCAN READY', icon: ImageIcon, ready: true },
  { label: 'VIDEO TEMPORAL BUFFERING', icon: Video, ready: false },
  { label: 'AUDIO PIPELINE', icon: Mic, ready: false },
  { label: 'TEXT/PDF', icon: FileText, ready: false },
];

export function Dashboard() {
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [activeFile, setActiveFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const { bindScan, reset } = useChatStore();
  const navigate = useNavigate();

  useEffect(() => {
    reset();
  }, [reset]);

  useEffect(() => {
    bindScan(activeScanId);
  }, [activeScanId, bindScan]);

  useEffect(() => {
    if (activeFile && activeFile.type.startsWith('image/')) {
      const url = URL.createObjectURL(activeFile);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
  }, [activeFile]);

  const handleScanCreated = (scanId: string, file: File) => {
    setActiveScanId(scanId);
    setActiveFile(file);
  };

  const handleClearProcess = () => {
    setActiveScanId(null);
    setActiveFile(null);
    setPreviewUrl(null);
    reset();
  };

  const handleScanComplete = (scanId: string) => {
    navigate(`/scan/${scanId}`);
    setActiveScanId(null);
    setActiveFile(null);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <header className="space-y-1">
        <div className="flex justify-between items-start">
          <div>
            <p className="font-display text-xs tracking-[0.25em] text-muted uppercase">
              Forensic Audit
            </p>
            <h1 className="font-display text-3xl font-semibold text-fg">
              Initialize Forensic Audit
            </h1>
            <p className="text-sm text-muted mt-1">
              Drop an image to run the multi-agent forensic pipeline. Results will
              appear in the live analysis panel below.
            </p>
          </div>
          {activeScanId && (
            <button
              onClick={handleClearProcess}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-danger/10 text-danger hover:bg-danger/20 transition-colors text-sm font-medium"
            >
              <XCircle className="size-4" />
              Clear Process
            </button>
          )}
        </div>
      </header>

      {!activeScanId ? (
        <>
          <UploadDropzone onScanCreated={handleScanCreated} />

          <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {CAPABILITIES.map(({ label, icon: Icon, ready }) => (
              <div
                key={label}
                className="flex items-center gap-3 px-4 py-3 rounded-md bg-card border border-border"
              >
                <span
                  className={
                    ready
                      ? 'size-2 rounded-full bg-success'
                      : 'size-2 rounded-full bg-muted-foreground'
                  }
                />
                <Icon className="size-4 text-muted" />
                <span className="text-[11px] tracking-[0.15em] font-medium text-muted">
                  {label}
                </span>
              </div>
            ))}
          </section>
        </>
      ) : (
        <section className="space-y-6">
          <div className="flex items-center gap-4 p-4 rounded-card border border-border bg-card/60">
            <div className="shrink-0 size-16 rounded-md bg-bg-elevated border border-border flex items-center justify-center overflow-hidden">
              {previewUrl ? (
                <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
              ) : (
                <FileIcon className="size-8 text-muted" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-fg truncate">
                {activeFile?.name || 'Uploaded File'}
              </p>
              <p className="text-xs text-muted mt-0.5">
                {activeFile ? (activeFile.size / 1024 / 1024).toFixed(2) : '0.00'} MB
              </p>
            </div>
          </div>
          
          <ActiveScanPanel scanId={activeScanId} onComplete={handleScanComplete} />
        </section>
      )}
    </div>
  );
}
