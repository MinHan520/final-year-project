import { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, Loader2, AlertTriangle, X } from 'lucide-react';
import { useUpload } from '../../hooks/useUpload';

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
    } catch (err) {
      // error is handled by hook
    }
  }, [upload, onScanCreated]);

  const onDropRejected = useCallback((fileRejections: any[]) => {
    const rejection = fileRejections[0];
    if (rejection?.errors?.[0]?.code === 'file-too-large') {
      setRejectionError('File size exceeds the 25MB limit. Please upload a smaller file.');
    } else {
      setRejectionError(rejection?.errors?.[0]?.message || 'File rejected. Please try another file.');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    maxSize: 25 * 1024 * 1024,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif'],
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'],
      'audio/*': ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'],
      'text/plain': ['.txt', '.md', '.csv', '.log'],
      'application/pdf': ['.pdf'],
    },
    disabled: isPending,
  });

  return (
    <>
      {rejectionError && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="bg-danger border border-danger-foreground/20 shadow-lg shadow-danger/20 rounded-lg px-4 py-3 flex items-center gap-3 text-white">
            <AlertTriangle className="size-5 shrink-0" />
            <span className="text-sm font-medium">{rejectionError}</span>
            <button onClick={() => setRejectionError(null)} className="ml-2 hover:bg-black/20 p-1 rounded-md transition-colors" aria-label="Close">
              <X className="size-4" />
            </button>
          </div>
        </div>
      )}
      
      <div
        {...getRootProps()}
        className={`
          rounded-card border-2 border-dashed border-border-strong/80
          bg-card/40 transition-colors cursor-pointer
          p-10 grid place-items-center text-center
          ${isDragActive ? 'bg-primary/10 border-primary' : 'hover:bg-card/60'}
          ${isPending ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        <div className="space-y-4">
          <div className="size-14 mx-auto grid place-items-center rounded-full bg-primary/10 text-primary">
            {isPending ? <Loader2 className="size-7 animate-spin" /> : <UploadCloud className="size-7" />}
          </div>
          <div className="space-y-1">
            <p className="text-fg font-medium">
              {isPending ? 'Uploading...' : 'Drag & drop a file, or click to browse'}
            </p>
            <p className="text-xs text-muted">
              Supports Image, Video, Audio, PDF, Text up to 25MB
            </p>
          </div>
          {error && <p className="text-sm text-danger mt-2">{error}</p>}
          <button
            type="button"
            disabled={isPending}
            className="
              inline-flex items-center gap-2 h-9 px-4 rounded-md
              bg-primary/80 text-primary-foreground text-sm
            "
          >
            {isPending ? <Loader2 className="size-4 animate-spin" /> : <UploadCloud className="size-4" />}
            Initialize Audit
          </button>
        </div>
      </div>
    </>
  );
}
