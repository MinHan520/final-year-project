# TruthLens

Multi-agent forensic system for AI-generated image detection. React frontend +
FastAPI backend, migrating from the original Streamlit prototype in `../AIDE/`.

## Repository layout

```
React Project/
├── backend/        # FastAPI + agent modules (Python)
│   ├── app/
│   │   ├── agents/     # one module per forensic / LLM agent
│   │   ├── schemas.py  # Pydantic models shared across agents and API
│   │   └── config.py   # pydantic-settings (env-driven config)
│   └── tests/      # pytest unit tests for the agents
└── frontend/       # (Phase 2) Vite + React + TypeScript
```

## Phase 0 status — agent decoupling

The Streamlit `app.py` mixed UI with model + LLM logic. Phase 0 extracts the
pure logic into typed agent classes so Phase 1 (FastAPI) and Phase 2 (React)
have a clean import boundary.

| Agent | Purpose | Streamlit-free? |
|---|---|---|
| `AIDEDetectorAgent` | PyTorch mixture-of-experts deepfake detector (5-stream DCT + spatial). | yes |
| `OpenCVForensicsAgent` | Noise residual, Laplacian edge, ELA heatmap + Gemini commentary. | yes |
| `SynthIDAgent` | Gemini-driven SynthID watermark check. | yes |
| `GeminiRouterAgent` | Object Classification + greeting + agentic eval + chat reply. | yes |
| `SHAPExplainerAgent` | On-demand pixel-level SHAP heatmap (PNG, base64). | yes |

All agents return Pydantic models from `app/schemas.py`. No agent imports
Streamlit; the original prototype keeps running unchanged in `../AIDE/`.

## Running the tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The OpenCV, SynthID, and router tests use a synthetic 256×256 image fixture
and run anywhere. The AIDE detector test is skipped unless you point it at
a checkpoint:

```bash
AIDE_CHECKPOINT_PATH=/Users/you/Desktop/FYP/AIDE/results/progan_train.pth pytest
```

## Environment

Copy `backend/.env.example` to `backend/.env` and set:

- `GCP_PROJECT_ID` — required for Gemini-backed agents (router, OpenCV
  commentary, SynthID, agentic eval, chat reply). Without it the agents
  return safe fallbacks so unit tests don't need network access.
- `GCP_LOCATION` — defaults to `us-central1`.
- `AIDE_REPO_PATH` — only needed if the legacy `AIDE/` folder isn't a
  sibling of `React Project/`. The detector imports `models.AIDE` and
  `data.dct` from that repo until they are vendored here.

## Phase 1 status — FastAPI + SSE

Routes mounted on `app.main:app`:

| Method | Path | Purpose |
|---|---|---|
| GET    | `/health` | Liveness + detector / GCP wiring status |
| POST   | `/api/scan` | Upload image, returns 202 + `scan_id` |
| GET    | `/api/scan/{scan_id}` | Final JSON for a completed scan |
| GET    | `/api/scan/{scan_id}/events` | SSE stream of stage events |
| GET    | `/api/sessions/current/scans` | Recent scans for the implicit session |
| DELETE | `/api/scans/{scan_id}` | Drop a scan record |

SSE event vocabulary:

```
event: stage_start    data: {"agent": "...", "label": "..."}
event: stage_result   data: {"agent": "...", "result": {...}}
event: stage_error    data: {"agent": "...", "message": "..."}
event: complete       data: {"scan_id": "...", "summary": {...}}
event: error          data: {"scan_id": "...", "message": "..."}
```

Stages run in this order: `greeting` → `aide` → `opencv_maps` →
`opencv_commentary` → `synthid` → `eval`. Per-stage failures are
surfaced as `stage_error` but don't abort the run; only a missing AIDE
detector or an unexpected exception terminates the scan early.

### Running the dev server

```bash
cd backend
source ../../AIDE/aide_env/bin/activate
uvicorn app.main:app --port 8002

uvicorn app.main:app --reload --port 8002

curl -F file=@/path/to/image.jpg http://localhost:8000/api/scan
curl -N http://localhost:8000/api/scan/<scan_id>/events
```

Without `AIDE_CHECKPOINT_PATH` and `GCP_PROJECT_ID` set, the API still
boots and accepts uploads — every Gemini-backed stage returns its
fallback and the AIDE stage emits a `stage_error`. Useful for frontend
work without ML dependencies on the laptop.

## Phase 2 status — React skeleton

Stack:

- **Vite 8** + **React 19** + **TypeScript 6** (whatever `create-vite` ships).
- **Tailwind v4** via `@tailwindcss/vite`. Design tokens declared with the
  `@theme` directive in `src/index.css` — utilities like `bg-bg`,
  `bg-card`, `text-fg`, `text-muted`, `bg-primary`, `bg-success` are
  generated automatically.
- **shadcn/ui** is wired (`components.json`, `lib/utils.ts` `cn` helper)
  but no shadcn components are vendored yet — add them with
  `npx shadcn@latest add <name>` as needed in later phases.
- **TanStack Query** mounted at the app root.
- **Zustand** holds the floating chat open/closed state today; will hold
  transcript + per-scan binding in Phase 5.
- **react-dropzone** and **react-router-dom** installed but not yet used.

Layout shell (`src/components/layout/`):

```
<Layout>
├── <Sidebar>             // 240px, nav menu + nodes-online status
├── <TopHeader>           // sticky h-14, header links + search + Scan File
├── <MainContent>         // upload dropzone placeholder + capabilities + table stub
└── <FloatingChatWidget>  // bottom-right toggle, panel anchored above
```

API client lives at `src/api/client.ts` (typed wrappers for
`/api/scan`, `/api/scan/{id}`, `/api/sessions/current/scans`,
`/health`). Vite dev server proxies `/api` and `/health` to
`VITE_BACKEND_URL` (default `http://localhost:8000`), so the UI
calls the same relative paths in dev as in prod.

### Running both processes locally

```bash
# terminal 1
cd backend
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
# open http://localhost:5173
```

`npm run dev` boots in ~3s. Type-check with `npx tsc -b`.

## Phases ahead

- **Phase 3** — Live upload UI driven by `useScanStream` (EventSource).
- **Phase 4** — Active Session Forensics table + artifact endpoints.
- **Phase 5** — Floating chat widget bound to a per-scan conversation.
- **Phase 6** — Cutover behind a single reverse proxy; archive Streamlit.
