"""In-memory LLM token stream bus — sync publish from graph nodes, async SSE subscribe."""
from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _SessionStream:
    node: str | None = None
    text: str = ""
    subscribers: list[asyncio.Queue] = field(default_factory=list)


_lock = threading.Lock()
_sessions: dict[str, _SessionStream] = {}
_status_subscribers: dict[str, list[asyncio.Queue]] = {}
_main_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def _ensure_session(session_id: str) -> _SessionStream:
    if session_id not in _sessions:
        _sessions[session_id] = _SessionStream()
    return _sessions[session_id]


def _get_session(session_id: str) -> _SessionStream:
    with _lock:
        return _ensure_session(session_id)


def _broadcast(session_id: str, event: dict[str, Any]) -> None:
    with _lock:
        session = _sessions.get(session_id)
        if not session:
            return
        dead: list[asyncio.Queue] = []
        for queue in session.subscribers:
            try:
                queue.put_nowait(event)
            except Exception:
                dead.append(queue)
        for queue in dead:
            session.subscribers.remove(queue)


def _schedule(coro) -> None:
    if _main_loop is None or not _main_loop.is_running():
        return
    asyncio.run_coroutine_threadsafe(coro, _main_loop)


async def _async_start_node(session_id: str, node: str) -> None:
    with _lock:
        session = _ensure_session(session_id)
        session.node = node
        session.text = ""
    _broadcast(session_id, {"type": "start", "node": node})


async def _async_publish_token(session_id: str, node: str, token: str) -> None:
    from utils.node_lifecycle import mark_node_streaming

    mark_node_streaming(session_id, node)
    with _lock:
        session = _ensure_session(session_id)
        if session.node != node:
            session.node = node
            session.text = ""
        session.text += token
    _broadcast(session_id, {"type": "token", "node": node, "token": token})


async def _async_end_node(session_id: str, node: str) -> None:
    _broadcast(session_id, {"type": "done", "node": node})


def start_node(session_id: str, node: str) -> None:
    _schedule(_async_start_node(session_id, node))


def publish_token(session_id: str, node: str, token: str) -> None:
    _schedule(_async_publish_token(session_id, node, token))


def _broadcast_status(session_id: str, event: dict[str, Any]) -> None:
    with _lock:
        queues = list(_status_subscribers.get(session_id, []))
    dead: list[asyncio.Queue] = []
    for queue in queues:
        try:
            queue.put_nowait(event)
        except Exception:
            dead.append(queue)
    if dead:
        with _lock:
            subs = _status_subscribers.get(session_id, [])
            for queue in dead:
                if queue in subs:
                    subs.remove(queue)


async def _async_publish_status(session_id: str, payload: dict[str, Any]) -> None:
    _broadcast_status(session_id, {"type": "status", "data": payload})


def publish_activity(session_id: str, message: str) -> None:
    """Append a visible status line to the live token panel."""
    if not message:
        return
    line = message if message.endswith("\n") else message + "\n"
    with _lock:
        session = _ensure_session(session_id)
        session.text += line
    _broadcast(session_id, {"type": "activity", "text": line})


def publish_status(session_id: str, payload: dict[str, Any]) -> None:
    event = {"type": "status", "data": payload}
    if _main_loop is None or not _main_loop.is_running():
        _broadcast_status(session_id, event)
        return
    _schedule(_async_publish_status(session_id, payload))


def end_node(session_id: str, node: str) -> None:
    _schedule(_async_end_node(session_id, node))


def get_snapshot(session_id: str) -> dict[str, Any] | None:
    with _lock:
        session = _sessions.get(session_id)
        if not session or not session.node or not session.text:
            return None
        return {"type": "snapshot", "node": session.node, "text": session.text}


def clear_session(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)
        _status_subscribers.pop(session_id, None)


async def subscribe_status(session_id: str):
    """Async generator of status events for SSE (/status-stream)."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)
    with _lock:
        _status_subscribers.setdefault(session_id, []).append(queue)

    try:
        while True:
            event = await queue.get()
            yield event
            data = event.get("data") or {}
            if data.get("status") in {
                "completed",
                "failed",
                "max_retries_reached",
                "rejected",
                "cancelled",
            }:
                break
    finally:
        with _lock:
            subs = _status_subscribers.get(session_id, [])
            if queue in subs:
                subs.remove(queue)
            if not subs:
                _status_subscribers.pop(session_id, None)


async def subscribe(session_id: str):
    """Async generator of stream events for SSE."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=512)
    with _lock:
        session = _ensure_session(session_id)
        session.subscribers.append(queue)

    snapshot = get_snapshot(session_id)
    if snapshot:
        yield snapshot

    try:
        while True:
            event = await queue.get()
            yield event
    finally:
        with _lock:
            session = _sessions.get(session_id)
            if session and queue in session.subscribers:
                session.subscribers.remove(queue)
