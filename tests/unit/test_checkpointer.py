"""Tests for AsyncSqliteSaver checkpointer — v1.1 session persistence."""
import os
import tempfile

import pytest


@pytest.fixture
async def checkpoint_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("CHECKPOINT_DB_PATH", path)
    import graph.graph_builder as gb
    from graph import reset_graph_cache

    await gb.close_checkpointer()
    reset_graph_cache()
    await gb.init_checkpointer()
    yield path
    await gb.close_checkpointer()
    reset_graph_cache()
    if os.path.exists(path):
        os.unlink(path)


class TestCheckpointer:
    @pytest.mark.asyncio
    async def test_get_checkpointer_creates_sqlite_file(self, checkpoint_db):
        from graph.graph_builder import get_checkpointer

        cp = get_checkpointer()
        assert cp is not None
        assert os.path.exists(checkpoint_db)

    @pytest.mark.asyncio
    async def test_get_checkpointer_returns_singleton(self, checkpoint_db):
        from graph.graph_builder import get_checkpointer

        assert get_checkpointer() is get_checkpointer()

    @pytest.mark.asyncio
    async def test_build_graph_uses_sqlite_checkpointer(self, checkpoint_db):
        from graph.graph_builder import build_graph

        graph = build_graph()
        assert graph.checkpointer is not None

    @pytest.mark.asyncio
    async def test_get_checkpointer_raises_before_init(self, monkeypatch):
        import graph.graph_builder as gb
        from graph import reset_graph_cache

        await gb.close_checkpointer()
        reset_graph_cache()
        with pytest.raises(RuntimeError, match="not initialized"):
            gb.get_checkpointer()
