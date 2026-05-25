import { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Loader2, AlertTriangle, X } from 'lucide-react';
import { useUpload } from '../../hooks/useUpload';
import { cn } from '@/lib/utils';

export function UploadDropzone({ onScanCreated }: { onScanCreated: (scanId: string, file: File) => void }) {
  const { upload, isPending, error } = useUpload();
  const [rejectionError, setRejectionError] = useState<string | null>(null);

  useEffect(() => {
    if (rejectionError) {
      const timer = setTimeout(() => setRejectionError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [rejectionError]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    try {
      const scanId = await upload(acceptedFiles[0]);
      onScanCreated(scanId, acceptedFiles[0]);
    } catch { /* error surfaced by hook */ }
  }, [upload, onScanCreated]);

  const onDropRejected = useCallback((fileRejections: any[]) => {
    const r = fileRejections[0];
    setRejectionError(
      r?.errors?.[0]?.code === 'file-too-large'
        ? 'File size exceeds the 25 MB limit. Please upload a smaller file.'
        : r?.errors?.[0]?.message || 'File rejected. Please try another file.',
    );
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    maxSize: 25 * 1024 * 1024,
    accept: {
      'image/*':        ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif'],
      'video/*':        ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'],
      'audio/*':        ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'],
      'text/plain':     ['.txt', '.md', '.csv', '.log'],
      'application/pdf':['.pdf'],
    },
    disabled: isPending,
  });

  return (
    <>
      {/* Rejection toast */}
      {rejectionError && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="bg-danger border border-danger-foreground/20 shadow-lg shadow-danger/20 px-4 py-3 flex items-center gap-3 text-white">
            <AlertTriangle className="size-5 shrink-0" />
            <span className="text-sm font-medium">{rejectionError}</span>
            <button onClick={() => setRejectionError(null)} className="ml-2 hover:bg-black/20 p-1 transition-colors" aria-label="Close">
              <X className="size-4" />
            </button>
          </div>
        </div>
      )}

      <div
        className={cn(
          'group relative w-full max-w-2xl mx-auto rounded-2xl transition-all duration-300 border',
          'bg-slate-50 dark:bg-slate-900/50 min-h-[300px] flex flex-col items-center justify-center py-12 px-8',
          isDragActive
            ? 'bg-primary/5 shadow-[0_0_40px_rgba(168,85,247,0.4)] border-primary'
            : 'shadow-[0_0_30px_rgba(168,85,247,0.15)] cursor-pointer hover:shadow-[0_0_40px_rgba(168,85,247,0.25)] border-transparent hover:border-primary/50',
          isPending ? 'opacity-50 cursor-not-allowed' : ''
        )}
        {...getRootProps()}
      >
        <input {...getInputProps()} />
        <div className="absolute inset-0 pointer-events-none" />

        {/* Laser scan line when dragging */}
        {isDragActive && (
          <div className="absolute left-0 w-full h-[2px] bg-primary/70 shadow-[0_0_12px_var(--color-primary)] pointer-events-none animate-scan-line z-30" />
        )}

        <section className="relative z-20 flex flex-col items-center justify-center space-y-6 text-center">
          <div className={cn(
            "p-4 rounded-full transition-all duration-300 flex items-center justify-center",
            isDragActive 
              ? "bg-purple-200 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300 scale-110 shadow-[0_0_15px_rgba(168,85,247,0.3)]" 
              : "bg-purple-100 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 border border-purple-200/50 dark:border-purple-800/40 group-hover:bg-purple-200/80 group-hover:text-purple-700"
          )}>
            {isPending ? <Loader2 className="size-8 animate-spin" /> : <Upload className="size-8" />}
          </div>
          
          <div className="space-y-2">
            <p className="text-sm font-semibold text-fg">
              {isDragActive ? (
                <span className="text-primary font-bold">Initializing Scan Sequence...</span>
              ) : isPending ? (
                'Uploading Payload...'
              ) : (
                'Drop file to begin analysis'
              )}
            </p>
            <p className="text-[10px] text-muted font-mono tracking-[0.2em] opacity-70 uppercase">
              {isDragActive ? '[ RELEASE TO SUBMIT ]' : 'IMAGE · VIDEO · AUDIO · PDF · TEXT · MAX 25 MB'}
            </p>
          </div>

          {!isDragActive && !isPending && (
            <button
              type="button"
              className="inline-flex items-center gap-2 h-10 px-6 rounded-sm bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium transition-all duration-300 shadow-sm hover:shadow-[0_0_20px_rgba(168,85,247,0.4)] cursor-pointer"
              onClick={(e) => {
                // Ensure the click doesn't bubble if we just want it to trigger the dropzone's built-in click
                // Dropzone handles clicks on the container, but button makes it explicit.
                e.stopPropagation(); 
                (document.querySelector('input[type="file"]') as HTMLInputElement | null)?.click();
              }}
            >
              <Upload className="size-4 text-white" />
              Select File
            </button>
          )}

          {error && <p className="text-xs text-danger font-mono mt-2">{error}</p>}
        </section>
      </div>
    </>
  );
}
