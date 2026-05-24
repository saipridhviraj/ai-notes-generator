import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from graph.state import GraphState
from graph.nodes import (
    planner_node,
    consult_tutor_node,
    research_node,
    student_notes_creator,
    diagram_generator_node,
    tutor_notes_creator,
    evaluator_node,
    gap_bridger_node,
    final_response_node,
    mermaid_repair_node,
)
from utils.graph_node_wrapper import wrap_graph_node
from services.prompt_config import use_diagram_pipeline


def route_after_tutor(state: GraphState) -> str:
    if state.get("status") == "rejected":
        return "rejected"
    if state.get("awaiting_tutor", True):
        return "consult_tutor"
    return "research"


def route_after_evaluation(state: GraphState) -> str:
    result = state.get("evaluation_result")
    max_retries = int(os.getenv("MAX_EVAL_RETRIES", "2"))

    if result is None:
        return "final_response_max_retries"

    if result.passed:
        return "final_response"

    if state.get("retry_count", 0) >= max_retries:
        return "final_response_max_retries"

    return "gap_bridger"


_checkpointer: AsyncSqliteSaver | None = None
_db_conn = None


async def init_checkpointer() -> AsyncSqliteSaver:
    """Open persistent AsyncSqliteSaver for graph.astream (required for async execution)."""
    global _checkpointer, _db_conn
    if _checkpointer is not None:
        return _checkpointer

    import aiosqlite

    db_path = os.getenv("CHECKPOINT_DB_PATH", "data/checkpoints.db")
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    _db_conn = await aiosqlite.connect(db_path)
    _checkpointer = AsyncSqliteSaver(_db_conn)
    await _checkpointer.setup()
    return _checkpointer


async def close_checkpointer() -> None:
    global _checkpointer, _db_conn
    if _db_conn is not None:
        await _db_conn.close()
    _checkpointer = None
    _db_conn = None


def get_checkpointer() -> AsyncSqliteSaver:
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer not initialized. init_checkpointer() must run at app startup."
        )
    return _checkpointer


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("planner",        wrap_graph_node("planner", planner_node))
    builder.add_node("consult_tutor",  wrap_graph_node("consult_tutor", consult_tutor_node))
    builder.add_node("research",       wrap_graph_node("research", research_node))
    builder.add_node("student_notes",  wrap_graph_node("student_notes", student_notes_creator))
    if use_diagram_pipeline():
        builder.add_node("diagram_generator", wrap_graph_node("diagram_generator", diagram_generator_node))
    builder.add_node("tutor_notes",    wrap_graph_node("tutor_notes", tutor_notes_creator))
    builder.add_node("evaluator",      wrap_graph_node("evaluator", evaluator_node))
    builder.add_node("gap_bridger",    wrap_graph_node("gap_bridger", gap_bridger_node))
    builder.add_node("mermaid_repair", wrap_graph_node("mermaid_repair", mermaid_repair_node))
    builder.add_node("final_response", wrap_graph_node("final_response", final_response_node))

    builder.set_entry_point("planner")

    builder.add_edge("planner", "consult_tutor")

    builder.add_conditional_edges(
        "consult_tutor",
        route_after_tutor,
        {
            "research":      "research",
            "consult_tutor": "consult_tutor",
            "rejected":      END,
        },
    )

    builder.add_edge("research",      "student_notes")
    if use_diagram_pipeline():
        builder.add_edge("student_notes", "diagram_generator")
        builder.add_edge("diagram_generator", "tutor_notes")
    else:
        builder.add_edge("student_notes", "tutor_notes")
    builder.add_edge("tutor_notes",   "evaluator")

    builder.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "final_response":             "final_response",
            "gap_bridger":                "gap_bridger",
            "final_response_max_retries": "final_response",
        },
    )

    builder.add_edge("gap_bridger",    "evaluator")
    builder.add_edge("mermaid_repair", "evaluator")
    builder.add_edge("final_response", END)

    return builder.compile(checkpointer=get_checkpointer())
