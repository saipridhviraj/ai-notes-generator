"""Wrap graph nodes so the UI reflects the active step immediately."""

from __future__ import annotations

from typing import Callable

from graph.state import GraphState
from utils.node_lifecycle import mark_node_started


def wrap_graph_node(node_id: str, fn: Callable[[GraphState], dict]) -> Callable[[GraphState], dict]:
    def wrapped(state: GraphState) -> dict:
        mark_node_started(state.get("session_id"), node_id)
        return fn(state)

    wrapped.__name__ = getattr(fn, "__name__", node_id)
    wrapped.__doc__ = fn.__doc__
    return wrapped
