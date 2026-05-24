"""Unit tests for the asyncio event bus."""

import asyncio

import pytest

from app.event_bus import EventBus


@pytest.mark.asyncio
async def test_publish_then_subscribe_yields_in_order():
    bus = EventBus()
    scan_id = "abc"

    await bus.publish(scan_id, "stage_start", {"agent": "aide"})
    await bus.publish(scan_id, "stage_result", {"agent": "aide", "score": 0.9})
    await bus.close(scan_id)

    received = []
    async for ev in bus.subscribe(scan_id):
        received.append((ev.name, ev.data))

    assert received == [
        ("stage_start", {"agent": "aide"}),
        ("stage_result", {"agent": "aide", "score": 0.9}),
    ]
    assert bus.has_active(scan_id) is False


@pytest.mark.asyncio
async def test_subscribe_blocks_until_publish():
    bus = EventBus()
    scan_id = "xyz"

    async def consume():
        events = []
        async for ev in bus.subscribe(scan_id):
            events.append(ev.name)
        return events

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    await bus.publish(scan_id, "stage_start", {})
    await bus.close(scan_id)

    result = await asyncio.wait_for(consumer, timeout=1.0)
    assert result == ["stage_start"]
