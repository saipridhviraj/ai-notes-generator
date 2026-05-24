export type DiagramNodeType = "process" | "input" | "output" | "database" | "decision";
export type DiagramNodeColor = "blue" | "purple" | "green" | "orange" | "red";
export type DiagramLayout = "LR" | "TD";

export interface DiagramNodeSpec {
  id: string;
  label: string;
  type: DiagramNodeType;
  icon?: string;
  color: DiagramNodeColor;
}

export interface DiagramEdgeSpec {
  source: string;
  target: string;
  label?: string;
}

export interface DiagramSpec {
  title?: string;
  layout: DiagramLayout;
  nodes: DiagramNodeSpec[];
  edges: DiagramEdgeSpec[];
}

export const NODE_COLORS: Record<DiagramNodeColor, { fill: string; stroke: string }> = {
  blue: { fill: "#16213e", stroke: "#2563eb" },
  purple: { fill: "#1a1a2e", stroke: "#7c3aed" },
  green: { fill: "#0f3460", stroke: "#10b981" },
  orange: { fill: "#1e3a5f", stroke: "#f59e0b" },
  red: { fill: "#312e81", stroke: "#ef4444" },
};

export function parseDiagramSpec(raw: string): DiagramSpec {
  const parsed = JSON.parse(raw) as DiagramSpec;
  if (!parsed?.nodes?.length || !parsed?.edges?.length) {
    throw new Error("Invalid diagram spec");
  }
  return parsed;
}

export function layoutDiagramNodes(spec: DiagramSpec): Map<string, { x: number; y: number }> {
  const ids = spec.nodes.map((n) => n.id);
  const indegree: Record<string, number> = Object.fromEntries(ids.map((id) => [id, 0]));
  const adj: Record<string, string[]> = Object.fromEntries(ids.map((id) => [id, []]));

  for (const edge of spec.edges) {
    adj[edge.source]?.push(edge.target);
    indegree[edge.target] = (indegree[edge.target] ?? 0) + 1;
  }

  const roots = ids.filter((id) => indegree[id] === 0);
  const start = roots.length ? roots : [ids[0]];
  const depth: Record<string, number> = Object.fromEntries(start.map((id) => [id, 0]));
  const queue = [...start];

  while (queue.length) {
    const cur = queue.shift()!;
    for (const nxt of adj[cur] ?? []) {
      depth[nxt] = Math.max(depth[nxt] ?? 0, (depth[cur] ?? 0) + 1);
      indegree[nxt] -= 1;
      if (indegree[nxt] <= 0) queue.push(nxt);
    }
  }

  const layers: Record<number, string[]> = {};
  for (const id of ids) {
    const d = depth[id] ?? 0;
    (layers[d] ??= []).push(id);
  }

  const positions = new Map<string, { x: number; y: number }>();
  const lr = spec.layout === "LR";
  Object.entries(layers).forEach(([layerStr, layerIds]) => {
    const layer = Number(layerStr);
    layerIds.forEach((id, row) => {
      positions.set(id, lr ? { x: layer * 220, y: row * 100 } : { x: row * 220, y: layer * 100 });
    });
  });
  return positions;
}
