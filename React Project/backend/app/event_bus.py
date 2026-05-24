"""In-memory async event bus keyed by scan_id.

Each scan owns one ``asyncio.Queue``. The orchestrator publishes stage
events to the queue; the SSE endpoint consumes from it. When the
orchestrator finishes (or errors) it signals completion by publishing
a sentinel ``None`` and the bus drops the queue after a short grace
period so late-arriving SSE clients can fall back to the persisted
final result.

Single-process only — for multi-worker deployments swap this for Redis
pub/sub or NATS. The SSE endpoint and orchestrator must run in the
same process for the bus to work.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    name: str
    data: dict[str, Any]


_DONE = object()  # sentinel published when a scan finishes


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def _get_or_create(self, scan_id: str) -> asyncio.Queue:
        async with self._lock:
            queue = self._queues.get(scan_id)
            if queue is None:
                queue = asyncio.Queue()
                self._queues[scan_id] = queue
            return queue

    async def publish(self, scan_id: str, name: str, data: dict[str, Any]) -> None:
        queue = await self._get_or_create(scan_id)
        await queue.put(Event(name=name, data=data))

    async def close(self, scan_id: str) -> None:
        """Mark the scan's stream as done. Existing subscribers will see EOF."""
        queue = await self._get_or_create(scan_id)
        await queue.put(_DONE)

    async def subscribe(self, scan_id: str) -> AsyncIterator[Event]:
        """Yield events for a scan until the orchestrator signals completion."""
        queue = await self._get_or_create(scan_id)
        try:
            while True:
                item = await queue.get()
                if item is _DONE:
                    return
                yield item
        finally:
            # Drop the queue once any subscriber finishes. If multiple
            # subscribers exist this is racy — but for a single-user demo
            # the SSE stream is 1:1 with the scan.
            self._queues.pop(scan_id, None)

    def has_active(self, scan_id: str) -> bool:
        return scan_id in self._queues


def get_bus() -> EventBus:
    """Single-process singleton accessor."""
    global _BUS
    if _BUS is None:
        _BUS = EventBus()
    return _BUS


_BUS: Optional[EventBus] = None
