/** Mirror of backend Pydantic schemas (app/schemas.py) — keep in sync. */

export type RiskLabel =
  | 'HIGH_RISK'
  | 'AI_GENERATED'
  | 'INCONCLUSIVE'
  | 'AUTHENTIC';

export type ScanStatus = 'queued' | 'running' | 'complete' | 'failed';

export interface ScanRow {
  scan_id: string;
  filename: string;
  media_type: string;
  status: ScanStatus;
  score: number | null;
  risk_label: RiskLabel | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  result: ScanSummary | null;
}

export interface AIDEStageResult {
  score: number;
  success: boolean;
  error: string | null;
}

export interface ForensicMaps {
  noise_png_b64: string;
  edge_png_b64: string;
  ela_png_b64: string;
}

export interface OpenCVComments {
  noise: string;
  edges: string;
  compression: string;
}

export interface SynthIDResult {
  is_ai: boolean | null;
  confidence: number;
  reasoning: string;
  synth_id_detected: boolean;
  watermark_found: boolean;
}

export interface GreetingResult {
  text: string;
  success: boolean;
}

export interface EvalResult {
  text: string;
  success: boolean;
  error: string | null;
}

export interface SHAPResult {
  heatmap_png_b64: string;
  max_evals: number;
  success: boolean;
  error: string | null;
}

export interface ObjectClassificationResult {
  media_type: string;
  filename: string;
}

export type ConflictSeverity = 'low' | 'medium' | 'high';
export type ConflictAction   = 'proceed' | 'human_review' | 'reclassify';

export interface ConflictResult {
  has_conflict:        boolean;
  severity:            ConflictSeverity | null;
  conflicting_signals: string[];
  rule_triggered:      string | null;
  reason:              string | null;
  action_required:     ConflictAction | null;
  confidence_gap:      number | null;
}

export interface ScanSummary {
  scan_id: string;
  object_classification?: ObjectClassificationResult;
  aide?: AIDEStageResult;
  opencv_maps?: ForensicMaps;
  opencv_commentary?: OpenCVComments;
  synthid?: SynthIDResult;
  conflict?: ConflictResult;
  greeting?: GreetingResult;
  eval?: EvalResult;
  shap?: SHAPResult;
}

export type StageEventName =
  | 'stage_start'
  | 'stage_result'
  | 'stage_chunk'
  | 'stage_error'
  | 'complete'
  | 'error';

export interface StageEvent {
  event: StageEventName;
  data: Record<string, unknown>;
}
