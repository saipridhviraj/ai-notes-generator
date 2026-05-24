_graph = None


def get_graph():
    """Build and cache the compiled LangGraph. Called on first use after .env is loaded."""
    global _graph
    if _graph is None:
        from graph.graph_builder import build_graph
        _graph = build_graph()
    return _graph


def reset_graph_cache() -> None:
    """Clear cached graph (tests / checkpointer re-init)."""
    global _graph
    _graph = None


class _LazyGraph:
    """Transparent proxy so callers can write `from graph import graph` without
    triggering node imports (and service key checks) at module load time."""

    def __getattr__(self, name):
        return getattr(get_graph(), name)

    # astream returns an async generator — return it directly (no await)
    def astream(self, *args, **kwargs):
        return get_graph().astream(*args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        return await get_graph().ainvoke(*args, **kwargs)


graph = _LazyGraph()

__all__ = ["graph", "get_graph"]
