"""Opt-in JSON/SVG diagram pipeline (DIAGRAM_PIPELINE=true)."""

from utils.diagram_compiler import (
    compile_diagram_to_mermaid,
    validate_diagram_spec,
    wrap_after_heading,
    wrap_replace_index,
)
from utils.diagram_json_generate import (
    generate_repair_patch_json,
    generate_supplement_patch_json,
)
from utils.diagram_paths import diagrams_dir_for_state
from utils.diagram_pipeline import render_diagrams_in_notes, strip_mermaid_from_notes
from utils.diagram_placeholders import (
    convert_mermaid_blocks_to_placeholders,
    count_diagram_embeds,
    find_placeholders,
    has_unfilled_placeholders,
)
from utils.diagram_svg import render_diagram_svg

__all__ = [
    "compile_diagram_to_mermaid",
    "convert_mermaid_blocks_to_placeholders",
    "count_diagram_embeds",
    "diagrams_dir_for_state",
    "find_placeholders",
    "generate_repair_patch_json",
    "generate_supplement_patch_json",
    "has_unfilled_placeholders",
    "render_diagram_svg",
    "render_diagrams_in_notes",
    "strip_mermaid_from_notes",
    "validate_diagram_spec",
    "wrap_after_heading",
    "wrap_replace_index",
]
