/** Thin fetch wrapper. Vite proxies /api and /health to the backend in dev. */

import type { ScanRow } from './types';

export interface ScanCreatedResponse {
  scan_id: string;
  stream_url: string;
  result_url: string;
}

export async function createScan(file: File): Promise<ScanCreatedResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/scan', { method: 'POST', body: form });
  if (!res.ok) {
    throw new Error(`POST /api/scan failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getScan(scanId: string): Promise<ScanRow> {
  const res = await fetch(`/api/scan/${scanId}`);
  if (!res.ok) throw new Error(`GET /api/scan/${scanId} failed: ${res.status}`);
  return res.json();
}

export async function listScans(): Promise<ScanRow[]> {
  const res = await fetch('/api/sessions/current/scans');
  if (!res.ok) throw new Error(`GET /api/sessions/current/scans failed: ${res.status}`);
  return res.json();
}

export async function deleteScan(scanId: string): Promise<void> {
  const res = await fetch(`/api/scans/${scanId}`, { method: 'DELETE' });
  if (!res.ok && res.status !== 404) {
    throw new Error(`DELETE /api/scans/${scanId} failed: ${res.status}`);
  }
}

export async function getHealth(): Promise<{
  status: string;
  detector_loaded: boolean;
  gcp_configured: boolean;
}> {
  const res = await fetch('/health');
  if (!res.ok) throw new Error(`GET /health failed: ${res.status}`);
  return res.json();
}

export async function runShap(scanId: string): Promise<ScanRow> {
  const res = await fetch(`/api/scan/${scanId}/shap`, { method: 'POST' });
  if (!res.ok) throw new Error(`shap failed: ${res.status}`);
  return res.json();
}

export async function resolveConflict(
  scanId: string,
  decision: 'proceed' | 'reclassify',
  reason: string,
): Promise<{ status: string; decision: string }> {
  const res = await fetch(`/api/scan/${scanId}/resolve_conflict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason }),
  });
  if (!res.ok) throw new Error(`resolve_conflict failed: ${res.status}`);
  return res.json();
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  ts: number;
}

export interface ChatRequest {
  scan_id: string | null;
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  used_scan_id: string | null;
}

export async function postChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`POST /api/chat failed: ${res.status}`);
  return res.json();
}
