"""Pydantic models for structured diagram JSON (React Flow / SVG pipeline)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

NodeType = Literal["process", "input", "output", "database", "decision"]
NodeColor = Literal["blue", "purple", "green", "orange", "red"]
DiagramLayout = Literal["LR", "TD"]

MIN_NODES = 4
MIN_EDGES = 3


def _word_count(label: str) -> int:
    return len(re.findall(r"\w+", label or ""))


class DiagramNode(BaseModel):
    id: str
    label: str
    type: NodeType
    icon: str = "process"
    color: NodeColor = "purple"

    @field_validator("id")
    @classmethod
    def id_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Node id is required")
        return v

    @field_validator("label")
    @classmethod
    def label_rules(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Node label is required")
        if ":" in v:
            raise ValueError("Node label must not contain colons")
        if _word_count(v) > 3:
            raise ValueError(f"Node label exceeds 3 words: '{v}'")
        return v


class DiagramEdge(BaseModel):
    source: str
    target: str
    label: str = ""

    @field_validator("source", "target")
    @classmethod
    def edge_endpoints_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Edge source/target is required")
        return v


class DiagramSpec(BaseModel):
    title: str = "Diagram"
    layout: DiagramLayout = "TD"
    nodes: list[DiagramNode] = Field(min_length=MIN_NODES)
    edges: list[DiagramEdge] = Field(min_length=MIN_EDGES)

    @model_validator(mode="after")
    def validate_graph(self) -> DiagramSpec:
        node_ids = {n.id for n in self.nodes}
        connected: set[str] = set()
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge source '{edge.source}' not in nodes")
            if edge.target not in node_ids:
                raise ValueError(f"Edge target '{edge.target}' not in nodes")
            connected.update({edge.source, edge.target})
        isolated = node_ids - connected
        if isolated:
            raise ValueError(f"Isolated nodes: {', '.join(sorted(isolated)[:6])}")
        return self

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class BatchDiagramItem(DiagramSpec):
    """One diagram tied to a markdown section anchor."""

    anchor: str

    @field_validator("anchor")
    @classmethod
    def anchor_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("Diagram anchor is required")
        return v


class BatchDiagramResponse(BaseModel):
    diagrams: list[BatchDiagramItem] = Field(min_length=1)
