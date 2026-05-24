import { useState } from 'react';
import { createScan } from '../api/client';

export function useUpload() {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File) => {
    setIsPending(true);
    setError(null);
    try {
      const res = await createScan(file);
      return res.scan_id;
    } catch (err: any) {
      setError(err.message || 'Upload failed');
      throw err;
    } finally {
      setIsPending(false);
    }
  };

  return { upload, isPending, error };
}
