"""Render validated DiagramSpec JSON to static SVG (server-side embed in markdown)."""

from __future__ import annotations

import html
from collections import deque

from models.diagram_spec import DiagramSpec

_COLOR_STYLES: dict[str, tuple[str, str]] = {
    "blue": ("#16213e", "#2563eb"),
    "purple": ("#1a1a2e", "#7c3aed"),
    "green": ("#0f3460", "#10b981"),
    "orange": ("#1e3a5f", "#f59e0b"),
    "red": ("#312e81", "#ef4444"),
}

NODE_W = 160
NODE_H = 52
GAP_X = 80
GAP_Y = 70
PAD = 40


def _layer_nodes(spec: DiagramSpec) -> dict[str, tuple[int, int]]:
    """Assign grid positions — columns for LR, rows for TD."""
    ids = [n.id for n in spec.nodes]
    indegree = {i: 0 for i in ids}
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for edge in spec.edges:
        adj[edge.source].append(edge.target)
        indegree[edge.target] = indegree.get(edge.target, 0) + 1

    roots = [i for i in ids if indegree[i] == 0] or [ids[0]]
    depth: dict[str, int] = {r: 0 for r in roots}
    q: deque[str] = deque(roots)
    while q:
        cur = q.popleft()
        for nxt in adj.get(cur, []):
            depth[nxt] = max(depth.get(nxt, 0), depth[cur] + 1)
            indegree[nxt] -= 1
            if indegree[nxt] <= 0:
                q.append(nxt)

    layers: dict[int, list[str]] = {}
    for nid, d in depth.items():
        layers.setdefault(d, []).append(nid)
    for nid in ids:
        if nid not in depth:
            layers.setdefault(max(layers.keys(), default=0) + 1, []).append(nid)

    positions: dict[str, tuple[int, int]] = {}
    lr = spec.layout == "LR"
    for layer_idx, layer_nodes in sorted(layers.items()):
        for row_idx, nid in enumerate(layer_nodes):
            if lr:
                positions[nid] = (layer_idx, row_idx)
            else:
                positions[nid] = (row_idx, layer_idx)
    return positions


def _node_center(pos: tuple[int, int], lr: bool) -> tuple[float, float]:
    col, row = pos
    if lr:
        x = PAD + col * (NODE_W + GAP_X) + NODE_W / 2
        y = PAD + row * (NODE_H + GAP_Y) + NODE_H / 2
    else:
        x = PAD + col * (NODE_W + GAP_X) + NODE_W / 2
        y = PAD + row * (NODE_H + GAP_Y) + NODE_H / 2
    return x, y


def _node_rect(pos: tuple[int, int], lr: bool) -> tuple[float, float, float, float]:
    cx, cy = _node_center(pos, lr)
    return cx - NODE_W / 2, cy - NODE_H / 2, NODE_W, NODE_H


def render_diagram_svg(spec: DiagramSpec | dict) -> str:
    if isinstance(spec, dict):
        spec = DiagramSpec.model_validate(spec)

    positions = _layer_nodes(spec)
    lr = spec.layout == "LR"
    max_col = max(p[0] for p in positions.values())
    max_row = max(p[1] for p in positions.values())
    width = PAD * 2 + (max_col + 1) * NODE_W + max_col * GAP_X
    height = PAD * 2 + (max_row + 1) * NODE_H + max_row * GAP_Y

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img">',
        f'<title>{html.escape(spec.title)}</title>',
        '<defs>',
        '<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">',
        '<path d="M0,0 L8,4 L0,8 Z" fill="#94a3b8"/>',
        "</marker>",
        "</defs>",
        '<rect width="100%" height="100%" fill="#0f172a"/>',
    ]

    for edge in spec.edges:
        sp = positions.get(edge.source)
        tp = positions.get(edge.target)
        if not sp or not tp:
            continue
        sx, sy, sw, sh = _node_rect(sp, lr)
        tx, ty, tw, th = _node_rect(tp, lr)
        if lr:
            x1, y1 = sx + sw, sy + sh / 2
            x2, y2 = tx, ty + th / 2
        else:
            x1, y1 = sx + sw / 2, sy + sh
            x2, y2 = tx + tw / 2, ty
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#64748b" stroke-width="2" marker-end="url(#arrow)"/>'
        )
        if edge.label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 8
            parts.append(
                f'<text x="{mx:.1f}" y="{my:.1f}" fill="#cbd5e1" font-size="11" '
                f'text-anchor="middle">{html.escape(edge.label)}</text>'
            )

    for node in spec.nodes:
        pos = positions.get(node.id)
        if not pos:
            continue
        x, y, w, h = _node_rect(pos, lr)
        fill, stroke = _COLOR_STYLES.get(node.color, _COLOR_STYLES["purple"])
        rx = 8 if node.type != "decision" else 4
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + 4:.1f}" fill="#e2e8f0" '
            f'font-size="13" font-family="system-ui,sans-serif" text-anchor="middle">'
            f"{html.escape(node.label)}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)
