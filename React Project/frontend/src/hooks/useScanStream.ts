import { useEffect, useState } from 'react';
import type { ScanSummary } from '../api/types';

export type StageState = 'pending' | 'running' | 'complete' | 'error';

export interface StageData {
  state: StageState;
  result?: any;
  error?: string;
  streamText?: string;
}

export function useScanStream(scanId: string | null) {
  const [stages, setStages] = useState<Record<string, StageData>>({});
  const [status, setStatus] = useState<'running' | 'complete' | 'failed'>('running');
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;

    setStages({
      object_classification: { state: 'pending' },
      aide: { state: 'pending' },
      opencv_maps: { state: 'pending' },
      opencv_commentary: { state: 'pending' },
      synthid: { state: 'pending' },
      conflict: { state: 'pending' },
      eval: { state: 'pending' },
    });
    setStatus('running');
    setSummary(null);
    setError(null);

    const source = new EventSource(`/api/scan/${scanId}/events`);

    const handleStart = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.agent) {
        setStages(s => ({ ...s, [data.agent]: { ...s[data.agent], state: 'running' } }));
      }
    };

    const handleResult = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.agent) {
        setStages(s => ({ ...s, [data.agent]: { state: 'complete', result: data.result } }));
      }
    };

    const handleChunk = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.agent) {
        setStages(s => ({
          ...s,
          [data.agent]: {
            ...s[data.agent],
            state: 'running',
            streamText: (s[data.agent]?.streamText || '') + data.text,
          }
        }));
      }
    };

    const handleError = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.agent) {
        setStages(s => ({ ...s, [data.agent]: { state: 'error', error: data.message } }));
      }
    };

    const handleComplete = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setSummary(data.summary);
      setStatus('complete');
      source.close();
    };

    const handleFatalError = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      setError(data.message);
      setStatus('failed');
      source.close();
    };

    source.addEventListener('stage_start', handleStart);
    source.addEventListener('stage_result', handleResult);
    source.addEventListener('stage_chunk', handleChunk);
    source.addEventListener('stage_error', handleError);
    source.addEventListener('complete', handleComplete);
    source.addEventListener('error', handleFatalError);

    return () => {
      source.close();
    };
  }, [scanId]);

  return { stages, status, summary, error };
}
