"""Tests for LLM token stream bus."""
import asyncio

import pytest

from utils import stream_bus


@pytest.fixture(autouse=True)
def _reset_stream_bus():
    stream_bus.clear_session("sess-1")
    yield
    stream_bus.clear_session("sess-1")


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    loop = asyncio.get_running_loop()
    stream_bus.set_event_loop(loop)

    async def run_subscriber():
        events = []
        async for event in stream_bus.subscribe("sess-1"):
            events.append(event)
            if event.get("type") == "done":
                break
        return events

    sub_task = asyncio.create_task(run_subscriber())
    await asyncio.sleep(0.05)

    stream_bus.start_node("sess-1", "student_notes")
    await asyncio.sleep(0.05)
    stream_bus.publish_token("sess-1", "student_notes", "Hello")
    stream_bus.publish_token("sess-1", "student_notes", " world")
    stream_bus.end_node("sess-1", "student_notes")
    await asyncio.sleep(0.05)

    events = await asyncio.wait_for(sub_task, timeout=2.0)
    types = [e["type"] for e in events]
    assert "start" in types
    assert "token" in types
    assert "done" in types
    assert stream_bus.get_snapshot("sess-1")["text"] == "Hello world"


def test_get_snapshot_empty():
    stream_bus.clear_session("missing")
    assert stream_bus.get_snapshot("missing") is None
