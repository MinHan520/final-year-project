"""FastAPI application entry point.

Run locally:

    cd backend
    uvicorn app.main:app --reload --port 8000

Lifespan:
  * Loads settings from env / .env.
  * Initialises the SQLite ``ScanStore`` (creates ``sessions.db`` next
    to the upload dir on first run).
  * Constructs the ``EventBus``.
  * Lazily loads the ``AIDEDetectorAgent`` if the checkpoint exists. If
    not, the API still starts and every endpoint other than the scan
    pipeline works — useful for local UI iteration without the model.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import pillow_heif
pillow_heif.register_heif_opener()

from .api import routes_scan, routes_session, routes_chat
from .config import get_settings
from .detector_loader import get_detector
from .event_bus import get_bus
from .storage import ScanStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    db_path = settings.upload_dir.parent / "sessions.db"
    store = ScanStore(db_path)
    bus = get_bus()

    app.state.settings = settings
    app.state.store = store
    app.state.bus = bus
    app.state.detector = None  # Will be replaced below if checkpoint exists

    # Pre-load AIDE so the first scan response is immediate.
    detector = await get_detector(app)
    if detector:
        logger.info("AIDE detector pre-loaded at startup")
    else:
        logger.warning("AIDE detector not available — scans will fail until checkpoint is set")

    try:
        yield
    finally:
        logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TruthLens API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Dev CORS only. In prod, serve the React bundle behind the same origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_scan.router)
    app.include_router(routes_session.router)
    app.include_router(routes_chat.router)

    @app.get("/health")
    async def health():
        detector_loaded = app.state.detector is not None
        return {
            "status": "ok",
            "detector_loaded": detector_loaded,
            "gcp_configured": bool(app.state.settings.gcp_project_id),
            "lazy_loading": True,
        }

    return app


app = create_app()
