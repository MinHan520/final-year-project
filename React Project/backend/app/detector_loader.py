"""Lazy loader for the AIDE detector agent, kept separate to avoid circular imports."""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path

from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def get_detector(app: FastAPI):
    if app.state.detector is not None:
        return app.state.detector

    settings = app.state.settings

    if settings.aide_mock_mode:
        logger.info("Using AIDE Mock Detector (random scores)")
        from unittest.mock import MagicMock
        from .schemas import AIDEResult

        mock = MagicMock()
        mock.device = "mock-cpu"
        mock.predict.return_value = AIDEResult(score=random.uniform(0, 1), success=True)
        app.state.detector = mock
        return mock

    ckpt = Path(settings.aide_checkpoint_path)
    logger.info("AIDE checkpoint path: %s (resolved: %s, exists: %s)", ckpt, ckpt.resolve(), ckpt.exists())
    if not ckpt.exists():
        logger.warning("AIDE checkpoint not found at %s", ckpt)
        return None

    try:
        from .agents import AIDEDetectorAgent

        detector = await asyncio.to_thread(
            AIDEDetectorAgent,
            checkpoint_path=ckpt,
            device=settings.aide_device,
            resnet_path=settings.aide_resnet_path,
            convnext_path=settings.aide_convnext_path,
        )
        app.state.detector = detector
        logger.info("AIDE detector lazily loaded on %s", detector.device)
        return detector
    except Exception as e:
        logger.exception("AIDE detector failed to lazy-load: %s", e)
        return None
