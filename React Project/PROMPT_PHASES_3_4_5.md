# FutureLens — Phases 3, 4, 5 Implementation Prompt

> **Paste this entire document into Gemini Pro (or Claude / GPT-4) along with
> read access to the working tree at `/Users/laiminhan/Desktop/FYP/React Project/`.**
> The prompt is self-contained: every architectural fact, type definition,
> API contract, and design token your assistant needs is below.

---

## Role and Goal

You are an expert Full-Stack engineer. Your job is to implement **Phases 3, 4,
and 5** of the FutureLens migration — a multi-agent forensic deepfake
detection system that is moving from Streamlit to a Vite + React + TypeScript
frontend talking to a FastAPI + Pydantic backend.

Phases 0, 1, and 2 are already complete and verified:

- **Phase 0** — pure Python agent modules under `backend/app/agents/` with
  Pydantic schemas in `backend/app/schemas.py`. No Streamlit imports.
- **Phase 1** — FastAPI app with multi-stage scan orchestration, SQLite
  persistence, and Server-Sent Events for live stage updates.
- **Phase 2** — Vite + React + TypeScript shell with Tailwind v4, shadcn
  foundations (`cn` helper, `components.json`), TanStack Query mounted,
  Zustand chat store, layout components rendering empty placeholders.

**Constraint:** do not break Phases 0–2. Phase 3+ extends; it does not
rewrite. If you must change an existing file, justify it in a comment.

---

## Repository Layout (current, end of Phase 2)

```
React Project/
├── README.md
├── PROMPT_PHASES_3_4_5.md       ← this file
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, CORS, /health
│   │   ├── config.py            # pydantic-settings
│   │   ├── schemas.py           # Pydantic models (see below)
│   │   ├── event_bus.py         # asyncio.Queue per scan_id
│   │   ├── storage.py           # ScanStore (sqlite3) + classify_risk
│   │   ├── orchestrator.py      # run_scan, emits SSE events
│   │   ├── agents/
│   │   │   ├── aide_detector.py
│   │   │   ├── opencv_forensics.py
│   │   │   ├── synthid.py
│   │   │   ├── gemini_router.py # incl. SYSTEM_INSTRUCTION + conversational_reply
│   │   │   └── shap_explainer.py
│   │   └── api/
│   │       ├── routes_scan.py
│   │       └── routes_session.py
│   └── tests/
│       ├── test_event_bus.py
│       ├── test_storage.py
│       ├── test_api_scan.py
│       ├── test_opencv_forensics.py
│       ├── test_synthid.py
│       ├── test_gemini_router.py
│       └── test_aide_detector.py
└── frontend/
    ├── package.json
    ├── components.json
    ├── tsconfig*.json
    ├── vite.config.ts            # proxies /api and /health to :8000
    └── src/
        ├── App.tsx               # QueryClientProvider + <Layout>
        ├── main.tsx
        ├── index.css             # Tailwind v4 + @theme tokens
        ├── lib/utils.ts          # cn() helper
        ├── stores/chat-store.ts  # zustand: { isOpen, toggle, open, close }
        ├── api/
        │   ├── client.ts         # createScan, getScan, listScans, deleteScan, getHealth
        │   └── types.ts
        └── components/layout/
            ├── Layout.tsx
            ├── Sidebar.tsx
            ├── TopHeader.tsx
            ├── MainContent.tsx          ← needs heavy expansion in Phase 3 + 4
            └── FloatingChatWidget.tsx    ← stub today, becomes real in Phase 5
```

Run commands:

```bash
# backend (from React Project/backend)
uvicorn app.main:app --reload --port 8000
pytest

# frontend (from React Project/frontend)
npm run dev          # http://localhost:5173
npx tsc -b           # type-check
```

---

## Backend API Contract (already implemented, do NOT change semantics)

| Method | Path | Purpose |
|---|---|---|
| GET    | `/health` | `{status, detector_loaded, gcp_configured}` |
| POST   | `/api/scan` | multipart `file` → `202 {scan_id, stream_url, result_url}` |
| GET    | `/api/scan/{scan_id}` | full row with `result` summary as JSON |
| GET    | `/api/scan/{scan_id}/events` | **SSE stream** of stage events |
| GET    | `/api/sessions/current/scans?limit=50` | recent scans (newest first) |
| DELETE | `/api/scans/{scan_id}` | 204 |

### SSE Event Vocabulary

```
event: stage_start    data: {"agent": "<name>", "label": "<human label>"}
event: stage_result   data: {"agent": "<name>", "result": {...}}
event: stage_chunk    data: {"agent": "<name>", "text": "<delta>"}     # only for streaming agents
event: stage_error    data: {"agent": "<name>", "message": "..."}
event: complete       data: {"scan_id": "...", "summary": {...}}
event: error          data: {"scan_id": "...", "message": "..."}
```

Stages emitted in order, identified by `agent` field:

1. `greeting` — Gemini Vision identifies the image's subject (one or two warm sentences).
2. `aide` — AIDE PyTorch mixture-of-experts detector. Returns `{score, success, error}`.
3. `opencv_maps` — local OpenCV forensic maps (compute-only, no LLM). Returns base64 PNGs for noise residual, Laplacian edge, and ELA heatmap.
4. `opencv_commentary` — Gemini Vision plain-English explanation of the three maps.
5. `synthid` — Gemini SynthID watermark check.
6. `eval` — Agentic Gemini evaluation, friendly forensic verdict + visual clues.

If the AIDE checkpoint isn't loaded, the orchestrator emits a single
`stage_error` for `aide` followed by a terminal `error` event and the scan
is persisted with `status="failed"`.

### Late-joiner replay

`GET /api/scan/{id}/events` falls back to a single `complete` or `error`
event sourced from SQLite when the live queue has been dropped (i.e. the
scan finished before the client connected).

---

## Authoritative Type Definitions (verbatim from `frontend/src/api/types.ts`)

```ts
export type RiskLabel = 'HIGH_RISK' | 'AI_GENERATED' | 'INCONCLUSIVE' | 'AUTHENTIC';
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

export interface AIDEStageResult { score: number; success: boolean; error: string | null; }
export interface ForensicMaps { noise_png_b64: string; edge_png_b64: string; ela_png_b64: string; }
export interface OpenCVComments { noise: string; edges: string; compression: string; }
export interface SynthIDResult {
  is_ai: boolean | null;
  confidence: number;
  reasoning: string;
  synth_id_detected: boolean;
  watermark_found: boolean;
}
export interface GreetingResult { text: string; success: boolean; }
export interface EvalResult { text: string; success: boolean; error: string | null; }

export interface ScanSummary {
  scan_id: string;
  greeting?: GreetingResult;
  aide?: AIDEStageResult;
  opencv_maps?: ForensicMaps;
  opencv_commentary?: OpenCVComments;
  synthid?: SynthIDResult;
  eval?: EvalResult;
}

export type StageEventName =
  | 'stage_start' | 'stage_result' | 'stage_chunk'
  | 'stage_error' | 'complete' | 'error';
export interface StageEvent { event: StageEventName; data: Record<string, unknown>; }
```

---

## Design Tokens (verbatim from `frontend/src/index.css`)

```css
@theme {
  --color-bg: #0f172a;
  --color-bg-elevated: #131c31;
  --color-card: #1e293b;
  --color-card-foreground: #f8fafc;
  --color-border: #1f2a44;
  --color-border-strong: #2c3a5e;

  --color-fg: #f8fafc;
  --color-muted: #94a3b8;
  --color-muted-foreground: #64748b;

  --color-primary: #6366f1;
  --color-primary-hover: #4f46e5;
  --color-primary-foreground: #ffffff;

  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-critical: #dc2626;

  --font-sans: "Inter", ui-sans-serif, ...;
  --font-display: "Space Grotesk", "Inter", ...;
  --radius-card: 0.75rem;
}
```

Tailwind v4 generates utilities like `bg-bg`, `bg-card`, `text-muted`,
`bg-primary`, `text-primary-foreground`, `bg-success`, `border-border`,
`rounded-card`, `font-display` automatically from these.

---

## Risk classification thresholds (must match backend `storage.classify_risk`)

| Condition | Label | UI treatment |
|---|---|---|
| `score >= 0.80` | `HIGH_RISK` | red, animated `bg-critical` glow, "⚠ HIGH RISK" banner |
| `0.50 ≤ score < 0.80` | `AI_GENERATED` | red `bg-danger` |
| `0.30 ≤ score < 0.50` | `INCONCLUSIVE` | amber `bg-warning` |
| `score < 0.30` | `AUTHENTIC` | green `bg-success` |

---

# PHASE 3 — Live Upload + Stage Streaming UI

## Scope

Wire `react-dropzone` to the existing `POST /api/scan`, then consume the
SSE event stream and progressively render each stage as its result arrives.
No backend changes.

## Files to add

| Path | Purpose |
|---|---|
| `frontend/src/hooks/useScanStream.ts` | Wraps `EventSource('/api/scan/{id}/events')`, accumulates stage state, exposes `{stages, status, summary, error}`. Cleans up on unmount. |
| `frontend/src/hooks/useUpload.ts` | Wraps `createScan`, handles loading + error state, returns `{upload, isPending, error}`. |
| `frontend/src/components/scan/UploadDropzone.tsx` | `react-dropzone` zone with the dashed border; calls `useUpload` and on success returns the scan_id to the parent. Replaces the disabled placeholder in `MainContent.tsx`. |
| `frontend/src/components/scan/ActiveScanPanel.tsx` | Live stage progress: one row per stage (`greeting`, `aide`, `opencv_maps`, `opencv_commentary`, `synthid`, `eval`) showing `pending / running / complete / error` and a small inline preview (the AIDE score, the three OpenCV thumbnails, the SynthID verdict, the streamed eval text). |
| `frontend/src/components/scan/StageRow.tsx` | Shared row primitive for `ActiveScanPanel`. |
| `frontend/src/components/scan/RiskScoreCard.tsx` | Big AIDE % with risk-tier glow. Animated `bg-critical` ring at HIGH_RISK. |
| `frontend/src/components/scan/ForensicMapTrio.tsx` | Renders the three base64 PNGs with captions and the corresponding Gemini comment in an expandable tile. |

## Edits

- `frontend/src/components/layout/MainContent.tsx`: replace the disabled
  upload placeholder with `<UploadDropzone />`. When a scan_id is active,
  render `<ActiveScanPanel scanId={...} />` directly underneath. Lift the
  current-scan-id state into local `useState` (or a Zustand
  `useActiveScanStore` if cleaner).

## Implementation notes

- **`useScanStream`**: open `new EventSource(`/api/scan/${scanId}/events`)`,
  subscribe to each named event individually
  (`source.addEventListener('stage_start', ...)`, etc.). Use a reducer to
  merge incoming events into a `Record<AgentName, StageState>`. Close the
  EventSource on `complete` or `error`, and on unmount.
- The `stage_chunk` event isn't emitted by the backend yet (eval is one-shot
  in Phase 1). Handle it in the reducer anyway for Phase 5 forward-compat.
- **Base64 images** render inline as `<img src={`data:image/png;base64,${b64}`} />`.
  Don't make a network call for them.
- **Progress UX**: show a skeleton / shimmer while a stage is `running`.
  Stages are sequential — at most one `running` at a time.
- Surface `stage_error` non-fatally: render the row in muted red with the
  message; do NOT abort the panel — the rest of the pipeline keeps going.
- Hide `<ActiveScanPanel>` smoothly when `complete` arrives and switch to
  the persisted-result view (which Phase 4 will pull from `getScan(id)`).
  For now, just keep showing the panel — Phase 4 builds the persisted view.

## Exit criteria

- Drop a JPG into the dropzone → see stages appear live.
- Stopping the backend mid-scan surfaces a `stage_error` row and an
  overall failure banner; nothing crashes.
- `npx tsc -b` clean. `npm run dev` clean.

---

# PHASE 4 — Active Session Forensics Table + Detail View

## Scope

Persist all session scans visibly in a sortable table on the dashboard,
and add a routed detail view that re-renders any past scan from
`getScan(id)`.

## Backend changes

None required for the table itself — Phase 1's `/api/sessions/current/scans`
already returns rows in newest-first order. **Optional** but recommended:

- Add `GET /api/scan/{scan_id}/artifact/{name}` that streams base64 maps
  back as real `image/png` bytes. This lets you keep the JSON `result`
  payload small and use long-lived browser image caches. Map names:
  `noise`, `edge`, `ela`, `shap`. Spec: read `result_json` from
  SQLite, decode the requested base64 field, return as `Response` with
  `media_type="image/png"` and `Cache-Control: public, max-age=86400`.
  If you skip this, just keep rendering the inlined base64.

## Files to add

| Path | Purpose |
|---|---|
| `frontend/src/hooks/useScansList.ts` | TanStack Query wrapper around `listScans()`. `staleTime: 2_000`, refetch on focus, optimistic delete. |
| `frontend/src/components/scan/ForensicsTable.tsx` | Replaces the empty-state card in `MainContent`. Columns: File · Type · Risk Score · Status · Created · Action. Sortable by created_at and score. |
| `frontend/src/components/scan/RiskBar.tsx` | Inline progress bar coloured by `risk_label`. Width = `score * 100%`. |
| `frontend/src/components/scan/StatusBadge.tsx` | Small pill: `queued / running / complete / failed`. |
| `frontend/src/pages/Dashboard.tsx` | Composes UploadDropzone + ActiveScanPanel + ForensicsTable. |
| `frontend/src/pages/ScanDetail.tsx` | Route `/scan/:scanId`. Calls `getScan(scanId)`, renders the same components Phase 3 used live, but from the persisted summary. Adds a "Run SHAP" button (calls a new endpoint — see backend note below). |
| `frontend/src/components/scan/SHAPPanel.tsx` | Shows the SHAP heatmap or a "Run SHAP" CTA. Lazy: SHAP is expensive (5–30s), don't auto-run. |

### React Router setup

Convert `App.tsx` to mount routes:

```tsx
<BrowserRouter>
  <QueryClientProvider client={queryClient}>
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan/:scanId" element={<ScanDetail />} />
      </Routes>
    </Layout>
  </QueryClientProvider>
</BrowserRouter>
```

`<Layout>` becomes a wrapper that puts its `children` into `<MainContent>`'s
slot. Adjust `MainContent.tsx` to accept and render children.

## Backend addition (recommended): on-demand SHAP

Add `POST /api/scan/{scan_id}/shap` that:

1. Loads the scan record from `ScanStore`.
2. Resolves the file at `<upload_dir>/<scan_id>{ext}` (extension preserved on save).
3. Calls `SHAPExplainerAgent(detector).explain(file_path)`.
4. Persists the resulting `heatmap_png_b64` into the scan's `result_json` under `summary["shap"]`.
5. Returns the updated record.

Run the work in `asyncio.to_thread`. SHAP is single-threaded and CPU-bound;
do not run two concurrently — use a per-process `asyncio.Lock`. Emit nothing
on the event bus (the bus has already closed).

Add a frontend call in `api/client.ts`:

```ts
export async function runShap(scanId: string): Promise<ScanRow> {
  const res = await fetch(`/api/scan/${scanId}/shap`, { method: 'POST' });
  if (!res.ok) throw new Error(`shap failed: ${res.status}`);
  return res.json();
}
```

## Exit criteria

- Multiple uploads accumulate in the table without page reload.
- Clicking a row navigates to `/scan/:id` and re-renders the full forensic
  report from cache (no recomputation).
- Deleting a row optimistically removes it; row reappears if the DELETE fails.
- "Run SHAP" button on the detail view computes the heatmap, persists it,
  and renders inline. Subsequent visits show it instantly from
  `getScan().result.shap`.
- `npx tsc -b` clean. `pytest` (backend) clean.

---

# PHASE 5 — Floating Forensic Assistant (Real Chat)

## Scope

Make the floating chat fully functional. Bind it to the currently active
scan so the LLM has context. Use Gemini's existing
`GeminiRouterAgent.conversational_reply` (already implemented and uses
the long forensic-expert system prompt).

## Backend changes

Add a new router `backend/app/api/routes_chat.py`:

```
POST /api/chat
  body: {
    scan_id: str | null,        # current binding, or null for general Q&A
    message: str,
    history: [{role: 'user'|'assistant', text: str}, ...]   # frontend-managed transcript
  }
  → { reply: str, used_scan_id: str | null }
```

Implementation:

- Validate `message` is non-empty.
- Run `GeminiRouterAgent.conversational_reply(message, history, project_id, location)` in `asyncio.to_thread`.
- If `scan_id` is provided AND the scan is `complete`, prepend a synthetic
  history entry summarising the scan's verdict (one paragraph derived from
  the `eval` text and AIDE score) so the LLM has scan context.
- Return `{reply, used_scan_id: scan_id}`.

Add the router to `app/main.py`:

```python
from .api import routes_chat
app.include_router(routes_chat.router)
```

Add a unit test in `backend/tests/test_api_chat.py` covering:
- empty message → 422 (FastAPI validation handles this if you Pydantic-model the request)
- happy path with no `scan_id` and no `GCP_PROJECT_ID` → returns the static fallback string from `conversational_reply`
- happy path with a `scan_id` that doesn't exist → still 200 (treat as general chat).

## Frontend changes

Replace `frontend/src/stores/chat-store.ts` with a richer Zustand store:

```ts
interface ChatMessage { id: string; role: 'user' | 'assistant'; text: string; ts: number; }
interface ChatState {
  isOpen: boolean;
  boundScanId: string | null;     // null = general chat
  transcript: ChatMessage[];
  isSending: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
  bindScan: (scanId: string | null) => void;
  send: (message: string) => Promise<void>;        // POSTs /api/chat, appends to transcript
  reset: () => void;
}
```

Promote `FloatingChatWidget.tsx` to a real chat:

- Header still gradient, shows "Forensic Assistant" + the current binding
  (e.g., "Discussing scan abc12345..." with a small "Unbind" affordance).
- Transcript list: `<ChatMessage>` bubbles for `user` (right-aligned,
  `bg-primary` ) and `assistant` (left-aligned, `bg-card`). Markdown
  rendering OK if you want — install `react-markdown`.
- Input: textarea + Send button (disable while `isSending`). Submit on
  Enter, Shift+Enter for newline.
- Auto-scroll to bottom on new message.

Wire the active scan ID from the dashboard's URL or active-scan store
into `bindScan` — when the user opens a scan detail, automatically bind.
When they navigate back to `/`, unbind (or leave binding sticky? you decide,
document the choice).

Add a chat client in `frontend/src/api/client.ts`:

```ts
export interface ChatRequest { scan_id: string | null; message: string; history: ChatMessage[]; }
export interface ChatResponse { reply: string; used_scan_id: string | null; }

export async function postChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`POST /api/chat failed: ${res.status}`);
  return res.json();
}
```

## Exit criteria

- Floating chat is fully usable without disrupting the table or detail view.
- Chat persists across navigation (Zustand state outlives route changes).
- Empty `GCP_PROJECT_ID` falls back gracefully to the static reply (verified
  by backend test).
- Without a scan binding, the assistant still answers forensic-concept
  questions (e.g., "what is ELA?") using its system prompt.
- With a scan binding, the assistant references the scan's verdict.
- `npx tsc -b` clean. `pytest` clean.

---

## How to Work

1. Read every file referenced above before writing. Do not assume; verify.
2. Run `pytest` after backend changes; run `npx tsc -b` after frontend changes.
3. Add tests alongside any backend route or agent helper you add.
4. Match the existing code style: typed Pydantic models, no `Any`, no
   broad `except`, log via `logging.getLogger(__name__)`.
5. Do not introduce a new state library. Use TanStack Query for server
   state, Zustand for client state, URL params for navigation state.
6. Do not vendor shadcn components you don't need. Reach for a primitive
   only when a custom div+Tailwind feels brittle (e.g., the chat textarea
   could use shadcn `Textarea`; the table could use shadcn `Table`).
7. Run the dev server end-to-end at the close of each phase and confirm
   the exit criteria with a real upload.

## Output Format

Produce a single PR per phase with:

- A concise summary of what changed and why.
- The list of files added / modified / removed.
- Notes on any deviation from this prompt and the reason.
- Test results (`pytest` line count and `npx tsc -b` exit code).

Begin with Phase 3.
