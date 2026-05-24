"""Resolve output directory for diagram SVG files."""

from __future__ import annotations

from pathlib import Path

from graph.state import GraphState
from services.file_service import NOTES_DIR
from utils.helpers import slugify


def diagrams_dir_for_state(state: GraphState) -> Path:
    if state.get("output_dir"):
        return Path(state["output_dir"]) / "diagrams"
    plan = state["planner_output"]
    return NOTES_DIR / slugify(plan.topic) / "diagrams"
