"""Tests for utils/helpers.py — session store, Mermaid validation, graph config."""
import pytest
import time
from unittest.mock import patch
from utils.helpers import (
    create_session,
    get_session,
    set_session,
    generate_session_id,
    get_graph_config,
    slugify,
    validate_mermaid_block,
    validate_all_mermaid_in_notes,
    extract_mermaid_blocks,
    is_tutor_timed_out,
)


class TestSessionStore:
    def test_create_and_get_session(self):
        sid = generate_session_id()
        create_session(sid, {"status": "running"})
        result = get_session(sid)
        assert result is not None
        assert result["state"]["status"] == "running"

    def test_set_session_updates_data(self):
        sid = generate_session_id()
        create_session(sid, {"status": "running"})
        session = get_session(sid)
        session["state"]["status"] = "completed"
        set_session(sid, session)
        assert get_session(sid)["state"]["status"] == "completed"

    def test_get_nonexistent_session_returns_none(self):
        assert get_session("does-not-exist-xyz") is None

    def test_generate_session_id_is_unique(self):
        ids = {generate_session_id() for _ in range(100)}
        assert len(ids) == 100


class TestGraphConfig:
    def test_graph_config_structure(self):
        config = get_graph_config("session-abc")
        assert config == {"configurable": {"thread_id": "session-abc"}}


class TestMermaidValidation:
    def test_valid_block_passes(self):
        block = (
            "graph TD\n"
            "    A[Start] --> B[End]\n"
            "    style A fill:#1a1a2e,color:#e2e8f0\n"
            "    style B fill:#0f3460,color:#e2e8f0\n"
        )
        issues = validate_mermaid_block(block)
        assert not issues

    def test_missing_graph_type_flagged(self):
        block = "A --> B\nstyle A fill:#1a1a2e,color:#e2e8f0"
        issues = validate_mermaid_block(block)
        assert any("Invalid or missing graph type" in i for i in issues)

    def test_no_arrows_flagged(self):
        block = "graph TD\nA[Only node]\nstyle A fill:#1a1a2e,color:#e2e8f0"
        issues = validate_mermaid_block(block)
        assert any("No arrows" in i for i in issues)

    def test_missing_text_color_flagged(self):
        block = "graph TD\nA --> B\nstyle A fill:#1a1a2e"
        issues = validate_mermaid_block(block)
        assert any("#e2e8f0" in i for i in issues)

    def test_empty_block_flagged(self):
        issues = validate_mermaid_block("")
        assert issues


class TestValidateAllMermaid:
    def test_no_mermaid_blocks_flagged(self):
        issues = validate_all_mermaid_in_notes("# Hello\n\nNo diagrams here.")
        assert any("No Mermaid diagrams" in i for i in issues)

    def test_fewer_than_min_blocks_flagged(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "2")
        block = "```mermaid\ngraph TD\nA --> B\nstyle A fill:#1a1a2e,color:#e2e8f0\n```"
        issues = validate_all_mermaid_in_notes(block)
        assert any("minimum 2 required" in i for i in issues)

    def test_extract_mermaid_blocks(self):
        block = "```mermaid\ngraph TD\nA --> B\n```"
        result = extract_mermaid_blocks(f"Some text\n{block}\nMore text")
        assert len(result) == 1
        assert "graph TD" in result[0]


class TestTutorTimeout:
    def test_no_session_is_not_timed_out(self):
        assert is_tutor_timed_out("ghost-session") is False

    def test_fresh_session_is_not_timed_out(self):
        sid = generate_session_id()
        create_session(sid, {"status": "awaiting_tutor"})
        assert is_tutor_timed_out(sid) is False

    def test_old_session_is_timed_out(self):
        sid = generate_session_id()
        create_session(sid, {"status": "awaiting_tutor"})
        from utils.helpers import session_store
        session_store[sid]["start_time"] = time.time() - 400
        assert is_tutor_timed_out(sid) is True
