# TruthLens — Frontend

TruthLens is an AI-powered deepfake and media forensics platform. This directory contains the React/TypeScript single-page application (SPA) that provides the user interface for the multi-agent forensic pipeline. Users upload an image, watch real-time stage-by-stage analysis stream in, and receive a structured forensic report backed by AIDE (a Mixture-of-Experts deep learning model), OpenCV artifact maps, SynthID watermark detection, and a Gemini-powered agentic evaluation.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Environment Variables](#environment-variables)
   - [Running the Dev Server](#running-the-dev-server)
   - [Building for Production](#building-for-production)
4. [Architecture Overview](#architecture-overview)
   - [Routing](#routing)
   - [Data Fetching & Caching](#data-fetching--caching)
   - [Real-Time Streaming (SSE)](#real-time-streaming-sse)
   - [Global State](#global-state)
   - [API Proxy](#api-proxy)
5. [Pages](#pages)
   - [Dashboard (`/`)](#dashboard-)
   - [Scan Detail (`/scan/:scanId`)](#scan-detail-scanscandid)
6. [Components](#components)
   - [Layout](#layout-components)
   - [Scan](#scan-components)
7. [Hooks](#hooks)
8. [Stores](#stores)
9. [API Client](#api-client)
10. [Type System](#type-system)
11. [Design System](#design-system)
12. [Forensic Pipeline Stages](#forensic-pipeline-stages)
13. [Conflict Resolution Flow](#conflict-resolution-flow)

---

## Tech Stack

| Layer | Library | Version |
|---|---|---|
| UI Framework | React | 19.x |
| Language | TypeScript | 6.x |
| Build Tool | Vite | 8.x |
| Styling | Tailwind CSS | v4 (Vite plugin) |
| Routing | React Router DOM | v7 |
| Server State | TanStack React Query | v5 |
| Client State | Zustand | v5 |
| File Upload | React Dropzone | v15 |
| Icons | Lucide React | v1 |
| Class Utilities | clsx + tailwind-merge | latest |

**Fonts**: Inter (body text) · Space Grotesk (display/headings) — loaded from Google Fonts.

---

## Project Structure

```
frontend/
├── index.html                  # HTML entry point; loads Google Fonts
├── vite.config.ts              # Vite config: dev proxy, path alias (@/)
├── tsconfig.json               # Root TypeScript config
├── tsconfig.app.json           # App-level TS config (strict mode)
├── tsconfig.node.json          # Node/Vite config TS config
├── eslint.config.js            # ESLint flat config
├── components.json             # shadcn/ui config (for future component scaffolding)
├── package.json
└── src/
    ├── main.tsx                # React root — mounts <App> inside StrictMode
    ├── App.tsx                 # BrowserRouter + QueryClientProvider + route table
    ├── index.css               # Global styles and Tailwind v4 @theme design tokens
    │
    ├── api/
    │   ├── client.ts           # Typed fetch wrappers for every backend endpoint
    │   └── types.ts            # TypeScript mirrors of backend Pydantic schemas
    │
    ├── hooks/
    │   ├── useUpload.ts        # File upload state machine (pending / error)
    │   ├── useScanStream.ts    # SSE listener — translates events into stage state
    │   └── useScansList.ts     # TanStack Query wrapper for listing & deleting scans
    │
    ├── stores/
    │   └── chat-store.ts       # Zustand store — floating chat widget state & API calls
    │
    ├── lib/
    │   └── utils.ts            # cn() helper (clsx + tailwind-merge)
    │
    ├── pages/
    │   ├── Dashboard.tsx       # Upload entry point; transitions to live analysis view
    │   └── ScanDetail.tsx      # Full forensic report with tabbed interface
    │
    └── components/
        ├── layout/
        │   ├── Layout.tsx           # Root shell: sidebar + header + main + chat widget
        │   ├── Sidebar.tsx          # Collapsible left nav with status indicator
        │   ├── TopHeader.tsx        # Sticky top bar: search, scan button, user menu
        │   ├── MainContent.tsx      # Scrollable main content area
        │   └── FloatingChatWidget.tsx  # Fixed-position AI forensic assistant chat
        │
        └── scan/
            ├── UploadDropzone.tsx   # Drag-and-drop / click-to-upload file input
            ├── ActiveScanPanel.tsx  # Live SSE-driven pipeline stage tracker
            ├── StageRow.tsx         # Single pipeline stage row (icon + label + content)
            ├── RiskScoreCard.tsx    # Coloured AIDE score card (percentage + label)
            ├── RiskBar.tsx          # Inline progress bar for score in table rows
            ├── StatusBadge.tsx      # Text badge reflecting scan status / risk label
            ├── ForensicMapTrio.tsx  # Three-panel grid of base64 OpenCV images
            ├── SHAPPanel.tsx        # On-demand SHAP heatmap launcher and display
            ├── ConflictAlert.tsx    # Human-in-the-loop conflict resolution form
            └── ForensicsTable.tsx   # Scan history table with delete and link actions
```

---

## Getting Started

### Prerequisites

- **Node.js** ≥ 20 (LTS recommended)
- **npm** ≥ 10
- The **backend** server running at `http://127.0.0.1:8002` (or your custom URL — see [Environment Variables](#environment-variables))

### Installation

```bash
cd frontend
npm install
```

### Environment Variables

Create a `.env.local` file in the `frontend/` directory if you need to override the backend URL:

```env
# Default: http://127.0.0.1:8002
VITE_BACKEND_URL=http://your-backend-host:port
```

The Vite dev server automatically proxies all `/api` and `/health` requests to this URL, so the browser never crosses an origin boundary during development.

### Running the Dev Server

```bash
npm run dev
```

Opens at **http://localhost:5173** with Hot Module Replacement (HMR) enabled.

### Building for Production

```bash
npm run build
```

Output is written to `dist/`. Preview the production build locally with:

```bash
npm run preview
```

---

## Architecture Overview

### Routing

Defined in `src/App.tsx` using React Router v7 (`BrowserRouter`):

| Path | Component | Description |
|---|---|---|
| `/` | `Dashboard` | Upload entry point; transitions into live scan view inline |
| `/scan/:scanId` | `ScanDetail` | Full forensic report for a completed (or running) scan |

The `Layout` component wraps all routes and renders the persistent sidebar, top header, and floating chat widget.

### Data Fetching & Caching

TanStack Query (`QueryClient`) handles all server state:

- **Global defaults** (set in `App.tsx`): `staleTime: 5_000`, `refetchOnWindowFocus: false`.
- **`['scans']` query** (`useScansList`): Fetches the full scan history for the current session. `staleTime: 2_000`, `refetchOnWindowFocus: true` so the table stays fresh.
- **`['scan', scanId]` query** (`ScanDetail`): Fetches a single scan. Polls every 2 seconds while `status === 'running' | 'queued'`, stops when complete or failed.
- **Optimistic deletion**: `useScansList` removes the row from the cache immediately on delete and rolls back on error.

### Real-Time Streaming (SSE)

When a scan is created, the backend opens a Server-Sent Events stream at `/api/scan/:scanId/events`. The `useScanStream` hook opens an `EventSource` to this URL and maps each event type to per-stage state:

| SSE event | Effect |
|---|---|
| `stage_start` | Sets the named stage to `running` |
| `stage_result` | Sets the named stage to `complete` and attaches the result payload |
| `stage_chunk` | Appends text to `streamText` (for streaming LLM output) |
| `stage_error` | Sets the named stage to `error` with the message |
| `complete` | Sets overall status to `complete`, stores the full `ScanSummary`, closes the stream |
| `error` | Sets overall status to `failed`, closes the stream |

The `ActiveScanPanel` component reads this state and renders each pipeline stage as a `StageRow` with the appropriate icon and inline result.

### Global State

Zustand (`src/stores/chat-store.ts`) manages the floating chat widget:

| State | Type | Description |
|---|---|---|
| `isOpen` | `boolean` | Whether the chat panel is visible |
| `boundScanId` | `string \| null` | The scan ID currently providing context to the assistant |
| `transcript` | `ChatMessage[]` | Full message history |
| `isSending` | `boolean` | True while waiting for an API response |

Actions: `toggle`, `open`, `close`, `bindScan`, `send`, `reset`.

The `send` action calls `POST /api/chat` with the current `boundScanId` and full transcript as history. On failure it injects a user-visible error message into the transcript rather than throwing.

The `Dashboard` page calls `reset()` on mount to clear any previous scan context. The `ScanDetail` page calls `bindScan(scanId)` on mount and `reset()` on unmount so the assistant always has context for the currently viewed scan.

### API Proxy

`vite.config.ts` proxies two path prefixes to the backend:

```
/api   →  VITE_BACKEND_URL (default http://127.0.0.1:8002)
/health → VITE_BACKEND_URL
```

`changeOrigin: true` is set so the `Host` header matches the backend. In production, configure your web server (nginx, Caddy, etc.) to handle the same proxy rules.

---

## Pages

### Dashboard (`/`)

**File**: `src/pages/Dashboard.tsx`

The entry point for creating a new forensic scan. Its lifecycle has two phases:

**Phase 1 — Upload**: Shows the `UploadDropzone` and a capability status grid (Image scan ready; Video, Audio, Text/PDF marked as coming soon). When the user drops or selects a file, `useUpload` calls `POST /api/scan`, receives a `scan_id`, and transitions to Phase 2.

**Phase 2 — Live Analysis**: Shows a file preview card (thumbnail for images, file icon for other types) followed by `ActiveScanPanel`. The panel streams stage results in real time. When the scan completes, the page automatically navigates to `/scan/:scanId` after a 1.5-second delay.

A **Clear Process** button (visible in Phase 2) resets the page back to Phase 1 and clears the chat context.

**State**:
- `activeScanId` — the scan ID returned from the upload API call
- `activeFile` — the `File` object (used for preview and file info display)
- `previewUrl` — an object URL created from `activeFile` (revoked on cleanup)

---

### Scan Detail (`/scan/:scanId`)

**File**: `src/pages/ScanDetail.tsx`

Shows the full forensic report for a completed scan. Uses `useQuery` to fetch the scan and polls while the scan is still running (redirecting to `ActiveScanPanel` in that case).

If the detected `media_type` is not an image, a placeholder card is shown with a "coming soon" message.

For completed image scans, the report is presented in four tabs:

| Tab | Content |
|---|---|
| **AIDE Detection** | `RiskScoreCard` with probability score and threshold legend |
| **Low-Level Artifacts** | `ForensicMapTrio` — noise residuals, Laplacian edge gradient, ELA compression maps with AI commentary |
| **SynthID** | Watermark detection status and reasoning from Google's SynthID verifier |
| **Agentic Evaluation** | Plain-English forensic verdict from Gemini, with markdown bold (`**text**`) rendered inline |

Below all tabs, `SHAPPanel` is always visible — SHAP computation is on-demand because it is expensive (5–30 seconds).

The page binds its `scanId` to the Zustand chat store on mount, so the floating assistant has context while the user reviews the report.

---

## Components

### Layout Components

#### `Layout` — `src/components/layout/Layout.tsx`

Root shell component. Renders the full-height flex layout:

```
┌──────────┬────────────────────────────────┐
│          │ TopHeader                      │
│ Sidebar  ├────────────────────────────────┤
│          │ MainContent (children / pages) │
└──────────┴────────────────────────────────┘
                                  FloatingChatWidget (fixed)
```

**Props**: `children: ReactNode`

---

#### `Sidebar` — `src/components/layout/Sidebar.tsx`

Collapsible left navigation bar. Hidden on screens smaller than `lg` (1024px).

- Collapsed width: `72px` (icons only, with `title` tooltips)
- Expanded width: `240px` (icons + labels)
- Toggle is controlled by local `isCollapsed` state (not persisted)
- Bottom section shows a pulsing "Nodes online" status indicator and Settings/Support buttons
- Navigation items are declared in the `NAV` constant — add new routes there

---

#### `TopHeader` — `src/components/layout/TopHeader.tsx`

Sticky top bar (`z-30`, `h-14`) with backdrop blur. Contains:
- A search input (hidden on mobile) — currently decorative (no search logic wired)
- A **Scan File** button — currently decorative (the upload flow lives on the Dashboard)
- Notifications and Account icon buttons — currently decorative placeholders

---

#### `MainContent` — `src/components/layout/MainContent.tsx`

Thin wrapper that provides `overflow-y-auto` and consistent padding (`px-6 py-8`) around the routed page content.

**Props**: `children: ReactNode`

---

#### `FloatingChatWidget` — `src/components/layout/FloatingChatWidget.tsx`

A fixed-position (`bottom-6 right-6 z-50`) AI forensic assistant chat panel. When closed, it renders as a circular button. When open, it expands to a `400×600px` panel (capped at `80vh`).

- Reads and writes the Zustand `chat-store`
- Submits on `Enter` (without Shift); `Shift+Enter` inserts a newline
- Auto-scrolls to the latest message using a `bottomRef`
- Displays the bound `scanId` (first 8 chars) in the header with an **Unbind** button
- Shows a `Loader2` spinner while waiting for the assistant response

---

### Scan Components

#### `UploadDropzone` — `src/components/scan/UploadDropzone.tsx`

Drag-and-drop / click-to-browse file upload zone powered by `react-dropzone`.

| Configuration | Value |
|---|---|
| Max file size | 25 MB |
| Accepted formats | Image (jpg, jpeg, png, webp, gif, bmp, tiff, avif), Video (mp4, mov, avi, mkv, webm, m4v), Audio (mp3, wav, ogg, flac, m4a, aac), Text (txt, md, csv, log), PDF |

Rejection errors (file too large, wrong type) are shown as a slide-in toast banner at the top of the viewport and auto-dismissed after 5 seconds.

**Props**:
```ts
onScanCreated: (scanId: string, file: File) => void
```

---

#### `ActiveScanPanel` — `src/components/scan/ActiveScanPanel.tsx`

Renders the real-time pipeline progress driven by `useScanStream`. Each stage is rendered as a `StageRow`.

The **Low Level Artifact Analysis** display state is a composite: it stays `running` until `opencv_commentary` finishes (not just when `opencv_maps` finishes), because the AI commentary streams in after the maps are generated.

When the `conflict` stage resolves with `action_required === 'human_review'`, the panel pauses and shows a `ConflictAlert` form. Once the analyst submits a decision, `conflictResolved` is set to `true` and the pipeline resumes.

**Props**:
```ts
scanId: string
onComplete?: (scanId: string) => void   // called 1.5 s after status === 'complete'
```

---

#### `StageRow` — `src/components/scan/StageRow.tsx`

A single pipeline step row. Renders a status icon on the left and a label + optional content on the right.

| `state` value | Icon | Colour |
|---|---|---|
| `pending` | `Clock` | muted |
| `running` | `Loader2` (spinning) | primary |
| `complete` | `CheckCircle2` | success |
| `error` | `AlertCircle` | danger |

When `running` and no `children` are provided, it shows an animated skeleton bar.

**Props**:
```ts
label: string
state: 'pending' | 'running' | 'complete' | 'error'
children?: ReactNode
error?: string
```

---

#### `RiskScoreCard` — `src/components/scan/RiskScoreCard.tsx`

A coloured card displaying the AIDE AI probability score. Returns `null` if `aide.success` is false.

| Score range | Label | Colour |
|---|---|---|
| ≥ 80% | ⚠ HIGH RISK | Red + pulse glow |
| 50–79% | AI GENERATED | Danger red |
| 30–49% | INCONCLUSIVE | Warning amber |
| < 30% | AUTHENTIC | Success green |

**Props**:
```ts
aide: AIDEStageResult   // { score: number; success: boolean; error: string | null }
```

---

#### `RiskBar` — `src/components/scan/RiskBar.tsx`

A compact inline progress bar + percentage text for use in table rows. Returns a dash (`-`) when `score` is `null`.

**Props**:
```ts
score: number | null
label: RiskLabel | null
```

---

#### `StatusBadge` — `src/components/scan/StatusBadge.tsx`

A small text badge showing the scan status or risk classification.

| Condition | Text | Colour |
|---|---|---|
| `status === 'queued'` | QUEUED | muted |
| `status === 'running'` | RUNNING (pulsing) | primary |
| `status === 'failed'` | FAILED | danger |
| `risk_label === 'HIGH_RISK'` | HIGH PROBABILITY | critical |
| `risk_label === 'AI_GENERATED'` | AI GENERATED | danger |
| `risk_label === 'INCONCLUSIVE'` | INCONCLUSIVE | warning |
| `risk_label === 'AUTHENTIC'` or `null` | AUTHENTIC | success |

**Props**:
```ts
status: ScanStatus
risk_label: RiskLabel | null
```

---

#### `ForensicMapTrio` — `src/components/scan/ForensicMapTrio.tsx`

A responsive three-column grid (stacks to 1-col on mobile) displaying the three OpenCV forensic maps as base64 PNG images, each with an optional AI commentary caption below.

| Map | Base64 field | Commentary field |
|---|---|---|
| Noise Residuals | `noise_png_b64` | `comments.noise` |
| Laplacian Edge Gradient | `edge_png_b64` | `comments.edges` |
| Compression Analysis (ELA) | `ela_png_b64` | `comments.compression` |

**Props**:
```ts
maps: ForensicMaps
comments?: OpenCVComments
```

---

#### `SHAPPanel` — `src/components/scan/SHAPPanel.tsx`

On-demand SHAP (SHapley Additive exPlanations) heatmap display. Before computation, shows an explanatory message and a **Run SHAP Explainability** button. After computation, displays the heatmap image and evaluation count.

Clicking the button calls `POST /api/scan/:scanId/shap` and updates the TanStack Query cache directly with the returned `ScanRow` so the `ScanDetail` page re-renders without a refetch.

**Props**:
```ts
scanId: string
summary: ScanSummary | null
```

---

#### `ConflictAlert` — `src/components/scan/ConflictAlert.tsx`

A rich human-in-the-loop conflict resolution form shown when the pipeline's conflict detection stage returns `action_required === 'human_review'`.

Features:
- Countdown timer (default 300 seconds) — auto-proceeds with reason `"Auto-proceeded after timeout."` when it reaches zero
- Timer flashes red when under 60 seconds
- Required free-text reasoning field (submit buttons disabled until non-empty)
- Two decision buttons: **Proceed to Verdict** and **Re-classify**
- Calls `POST /api/scan/:scanId/resolve_conflict` with `{ decision, reason }`
- Severity styling (`low` / `medium` / `high`) applied to border, background, and text colours

**Props**:
```ts
conflict: ConflictResult
scanId: string
onDecision?: (decision: 'proceed' | 'reclassify', reason: string) => void
```

---

#### `ForensicsTable` — `src/components/scan/ForensicsTable.tsx`

A tabular view of all scans in the current session, fetched via `useScansList`. Each row shows:
- Filename (links to `/scan/:scanId`) + creation timestamp
- Media type badge
- `RiskBar` (inline score visualisation)
- `StatusBadge`
- Delete button (with optimistic UI update) + Details link

Displays a loading skeleton and an empty-state message when appropriate.

---

## Hooks

### `useUpload` — `src/hooks/useUpload.ts`

Thin wrapper around `createScan` that tracks pending and error state.

```ts
const { upload, isPending, error } = useUpload();
const scanId = await upload(file);  // throws on failure
```

| Return | Type | Description |
|---|---|---|
| `upload` | `(file: File) => Promise<string>` | Uploads the file, returns the `scan_id` |
| `isPending` | `boolean` | True while the request is in flight |
| `error` | `string \| null` | Error message if the upload failed |

---

### `useScanStream` — `src/hooks/useScanStream.ts`

Opens a Server-Sent Events connection to `/api/scan/:scanId/events` and maintains per-stage state. The `EventSource` is closed and cleaned up when the component unmounts or `scanId` changes.

```ts
const { stages, status, summary, error } = useScanStream(scanId);
```

| Return | Type | Description |
|---|---|---|
| `stages` | `Record<string, StageData>` | Map from stage name to `{ state, result?, error?, streamText? }` |
| `status` | `'running' \| 'complete' \| 'failed'` | Overall pipeline status |
| `summary` | `ScanSummary \| null` | Full result payload (set on `complete` event) |
| `error` | `string \| null` | Fatal error message |

Stage names tracked: `object_classification`, `aide`, `opencv_maps`, `opencv_commentary`, `synthid`, `conflict`, `eval`.

---

### `useScansList` — `src/hooks/useScansList.ts`

TanStack Query wrapper for the scans list with optimistic delete.

```ts
const { scans, isLoading, error, deleteScan, isDeleting } = useScansList();
```

| Return | Type | Description |
|---|---|---|
| `scans` | `ScanRow[]` | All scans for the current session |
| `isLoading` | `boolean` | True on the first load |
| `error` | `Error \| null` | Fetch error |
| `deleteScan` | `(scanId: string) => void` | Triggers optimistic delete + API call |
| `isDeleting` | `boolean` | True while a delete mutation is in flight |

---

## Stores

### `chat-store` — `src/stores/chat-store.ts`

Zustand store for the floating chat assistant. Created with `create<ChatState>`.

```ts
const { isOpen, toggle, send, bindScan, transcript, isSending } = useChatStore();
```

| Action | Signature | Description |
|---|---|---|
| `toggle` | `() => void` | Flips `isOpen` |
| `open` | `() => void` | Sets `isOpen = true` |
| `close` | `() => void` | Sets `isOpen = false` |
| `bindScan` | `(scanId: string \| null) => void` | Sets `boundScanId` for API context |
| `send` | `(message: string) => Promise<void>` | Appends user message, calls API, appends reply |
| `reset` | `() => void` | Clears transcript and unbinds scan |

`send` auto-opens the widget (sets `isOpen = true`) when called, so it can be triggered programmatically. On API failure it pushes a user-facing error message into the transcript instead of throwing.

---

## API Client

**File**: `src/api/client.ts`

All network calls go through this module. Each function throws a descriptive `Error` on non-OK responses.

| Function | Method + Path | Description |
|---|---|---|
| `createScan(file)` | `POST /api/scan` | Upload a file, returns `{ scan_id, stream_url, result_url }` |
| `getScan(scanId)` | `GET /api/scan/:scanId` | Fetch a single scan row |
| `listScans()` | `GET /api/sessions/current/scans` | Fetch all scans for the current session |
| `deleteScan(scanId)` | `DELETE /api/scans/:scanId` | Delete a scan (404 is silently ignored) |
| `getHealth()` | `GET /health` | Backend health check — returns `status`, `detector_loaded`, `gcp_configured` |
| `runShap(scanId)` | `POST /api/scan/:scanId/shap` | Trigger SHAP computation, returns updated `ScanRow` |
| `resolveConflict(scanId, decision, reason)` | `POST /api/scan/:scanId/resolve_conflict` | Submit a human review decision |
| `postChat(req)` | `POST /api/chat` | Send a message to the forensic assistant |

The real-time event stream at `GET /api/scan/:scanId/events` is consumed directly via the browser's `EventSource` API in `useScanStream` — it is not wrapped in the client module because `EventSource` manages its own lifecycle.

---

## Type System

**File**: `src/api/types.ts`

TypeScript interfaces that mirror the backend's Pydantic schemas in `app/schemas.py`. Keep these in sync when the backend schema changes.

### Core Types

```ts
type RiskLabel = 'HIGH_RISK' | 'AI_GENERATED' | 'INCONCLUSIVE' | 'AUTHENTIC';
type ScanStatus = 'queued' | 'running' | 'complete' | 'failed';
type ConflictSeverity = 'low' | 'medium' | 'high';
type ConflictAction = 'proceed' | 'human_review' | 'reclassify';
```

### `ScanRow`

The top-level record returned by `GET /api/scan/:scanId` and `GET /api/sessions/current/scans`:

```ts
interface ScanRow {
  scan_id: string;
  filename: string;
  media_type: string;
  status: ScanStatus;
  score: number | null;           // AIDE probability (0–1)
  risk_label: RiskLabel | null;
  error: string | null;
  created_at: string;             // ISO 8601
  updated_at: string;
  result: ScanSummary | null;     // null while running
}
```

### `ScanSummary`

The nested result payload, populated stage by stage as the pipeline runs:

```ts
interface ScanSummary {
  scan_id: string;
  object_classification?: ObjectClassificationResult;
  aide?: AIDEStageResult;
  opencv_maps?: ForensicMaps;
  opencv_commentary?: OpenCVComments;
  synthid?: SynthIDResult;
  conflict?: ConflictResult;
  eval?: EvalResult;
  shap?: SHAPResult;
}
```

### Stage Result Types

| Interface | Key Fields |
|---|---|
| `AIDEStageResult` | `score: number`, `success: boolean`, `error: string \| null` |
| `ForensicMaps` | `noise_png_b64`, `edge_png_b64`, `ela_png_b64` (base64 PNG strings) |
| `OpenCVComments` | `noise`, `edges`, `compression` (plain text commentary) |
| `SynthIDResult` | `is_ai`, `confidence`, `reasoning`, `synth_id_detected`, `watermark_found` |
| `ConflictResult` | `has_conflict`, `severity`, `conflicting_signals[]`, `rule_triggered`, `reason`, `action_required`, `confidence_gap` |
| `EvalResult` | `text` (Gemini verdict, may contain `**bold**` markdown), `success`, `error` |
| `SHAPResult` | `heatmap_png_b64`, `max_evals`, `success`, `error` |

### SSE Event Types

```ts
type StageEventName =
  | 'stage_start'    // { agent: string }
  | 'stage_result'   // { agent: string, result: any }
  | 'stage_chunk'    // { agent: string, text: string }
  | 'stage_error'    // { agent: string, message: string }
  | 'complete'       // { summary: ScanSummary }
  | 'error';         // { message: string }
```

---

## Design System

**File**: `src/index.css`

TruthLens uses a dark-first design system defined as Tailwind v4 `@theme` CSS variables. These compile to utility classes (`bg-bg`, `text-fg`, `ring-primary`, etc.).

### Colour Tokens

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#0f172a` | Page background |
| `--color-bg-elevated` | `#131c31` | Sidebar, elevated surfaces |
| `--color-card` | `#1e293b` | Card backgrounds |
| `--color-border` | `#1f2a44` | Default borders |
| `--color-border-strong` | `#2c3a5e` | Emphasis borders, scrollbar |
| `--color-fg` | `#f8fafc` | Primary text |
| `--color-muted` | `#94a3b8` | Secondary / placeholder text |
| `--color-primary` | `#6366f1` | Indigo — interactive elements |
| `--color-primary-hover` | `#4f46e5` | Hover state |
| `--color-success` | `#10b981` | Authentic / complete |
| `--color-warning` | `#f59e0b` | Inconclusive / caution |
| `--color-danger` | `#ef4444` | AI generated / error |
| `--color-critical` | `#dc2626` | High risk (darker red) |

### Typography

| Variable | Fonts |
|---|---|
| `--font-sans` | Inter → system-ui → sans-serif |
| `--font-display` | Space Grotesk → Inter → sans-serif |

Use `font-display` on headings (`h1`, `h2`) and brand text. `font-sans` is the body default.

### Border Radius

`--radius-card: 0.75rem` — used as the `rounded-card` utility on all card/panel surfaces.

---

## Forensic Pipeline Stages

The backend executes these stages sequentially (some in parallel where noted). The frontend tracks each independently via SSE:

| # | Stage Key | Display Label | Description |
|---|---|---|---|
| 1 | `object_classification` | Object Classification | Classifies the media type (image / video / audio / text) |
| 2 | `aide` | AIDE Detection | Runs the MoE deep learning model; produces a 0–1 AI probability score |
| 3 | `opencv_maps` | Low Level Artifact Analysis | Generates noise residual, edge gradient, and ELA maps |
| 3b | `opencv_commentary` | *(sub-stage)* | AI commentary on the OpenCV maps; merged with stage 3 in the UI |
| 4 | `synthid` | SynthID Detection | Checks for Google's SynthID imperceptible watermark |
| 5 | `conflict` | Conflict Resolution | Evaluates signal consistency; may pause for human review |
| 6 | `eval` | Final Verdict | Gemini synthesises all signals into a plain-English forensic verdict |

After the pipeline completes, the user may optionally run:

| Stage | Display Label | Description |
|---|---|---|
| `shap` | SHAP Explainability | Pixel-level attribution heatmap (on-demand, 5–30 s) |

---

## Conflict Resolution Flow

When the `conflict` stage returns `action_required === 'human_review'`, the pipeline pauses and `ActiveScanPanel` shows `ConflictAlert`. The analyst must:

1. Read the conflict reason and the list of conflicting signals (e.g. `AIDE Score` vs `SynthID Watermark`).
2. Enter a free-text reasoning in the text area.
3. Click **Proceed to Verdict** (accepts the automated classification) or **Re-classify** (overrides it).

The decision is sent to `POST /api/scan/:scanId/resolve_conflict`. The backend resumes the pipeline and emits further SSE events. If no action is taken within **300 seconds**, the conflict auto-proceeds.

Only `human_review` severity shows the interactive form. A `low`-severity conflict shows a simple informational banner and the pipeline continues automatically.
