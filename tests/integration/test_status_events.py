"""Tests for status SSE events."""

import asyncio

import pytest

from utils import stream_bus
from utils.helpers import create_session, set_session
from utils.status_events import build_status_payload, publish_status_update


@pytest.fixture(autouse=True)
def _reset():
    stream_bus.clear_session("status-s1")
    yield
    stream_bus.clear_session("status-s1")


def test_build_status_payload():
    create_session(
        "status-s1",
        {"status": "running", "errors": [], "output_files": [], "retry_count": 0},
    )
    payload = build_status_payload("status-s1")
    assert payload is not None
    assert payload["session_id"] == "status-s1"
    assert payload["interrupted"] is True
    assert payload["status"] == "running"
    assert len(payload["pipeline_steps"]) == 8


@pytest.mark.asyncio
async def test_publish_status_reaches_subscriber():
    loop = asyncio.get_running_loop()
    stream_bus.set_event_loop(loop)

    create_session(
        "status-s1",
        {"status": "running", "errors": [], "output_files": [], "retry_count": 0},
    )

    async def collect():
        events = []
        async for event in stream_bus.subscribe_status("status-s1"):
            events.append(event)
            if len(events) >= 1:
                break
        return events

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.05)
    publish_status_update("status-s1")
    events = await asyncio.wait_for(task, timeout=2.0)

    assert events[0]["type"] == "status"
    assert events[0]["data"]["session_id"] == "status-s1"


@pytest.mark.asyncio
async def test_set_session_publishes_status():
    loop = asyncio.get_running_loop()
    stream_bus.set_event_loop(loop)

    create_session(
        "status-s1",
        {"status": "running", "errors": [], "output_files": [], "retry_count": 0},
    )

    async def collect():
        events = []
        async for event in stream_bus.subscribe_status("status-s1"):
            events.append(event)
            if event["data"].get("current_node") == "research":
                break
        return events

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.05)

    set_session(
        "status-s1",
        {
            "state": {
                "status": "running",
                "errors": [],
                "output_files": [],
                "retry_count": 0,
            },
            "current_node": "research",
            "start_time": 1.0,
        },
    )

    events = await asyncio.wait_for(task, timeout=2.0)
    assert events[-1]["data"]["current_node"] == "research"
