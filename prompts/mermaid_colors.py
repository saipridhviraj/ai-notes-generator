"""
Shared Mermaid color palette — single source of truth.
Import in mermaid_prompts.py, evaluator_prompts.py, and validators.
"""

# ── Fill colors (node backgrounds) ───────────────────────────────────────────
FILLS = [
    "#1a1a2e",  # deep navy       — root / top-level nodes
    "#16213e",  # dark blue       — general process nodes
    "#0f3460",  # mid navy        — secondary process nodes
    "#312e81",  # indigo          — ML / AI concept nodes
    "#4c1d95",  # deep purple     — GenAI / highlight nodes
    "#1e3a5f",  # steel blue      — input / output nodes
]

# ── Stroke colors (node borders) ─────────────────────────────────────────────
STROKES = [
    "#7c3aed",  # violet          — default accent
    "#2563eb",  # blue            — ML / data nodes
    "#06b6d4",  # cyan            — DL / process nodes
    "#10b981",  # emerald         — output / success nodes
    "#f59e0b",  # amber           — decision / warning nodes
    "#d946ef",  # fuchsia         — GenAI highlight nodes
    "#ec4899",  # pink            — marketing / creative nodes
]

TEXT_COLOR = "#e2e8f0"

FILLS_INLINE = " ".join(FILLS)
STROKES_INLINE = " ".join(STROKES)

PALETTE_RULE = (
    f"Allowed fills  : {FILLS_INLINE}\n"
    f"Allowed strokes: {STROKES_INLINE}\n"
    f"Text color     : {TEXT_COLOR} (always)"
)


def style(node_id: str, fill: str, stroke: str) -> str:
    """Return a Mermaid style line for a node."""
    return f"style {node_id} fill:{fill},stroke:{stroke},stroke-width:2px,color:{TEXT_COLOR}"
