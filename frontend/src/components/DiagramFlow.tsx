import { memo, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  NODE_COLORS,
  layoutDiagramNodes,
  type DiagramNodeColor,
  type DiagramNodeSpec,
  type DiagramSpec,
} from "../types/diagram";

type DiagramNodeData = { spec: DiagramNodeSpec };

function DiagramNodeCard({ data }: NodeProps<Node<DiagramNodeData>>) {
  const spec = data.spec;
  const colors = NODE_COLORS[spec.color as DiagramNodeColor] ?? NODE_COLORS.purple;
  const isDecision = spec.type === "decision";

  return (
    <div
      className="px-3 py-2 text-xs font-medium text-slate-100 min-w-[120px] text-center border-2 shadow-lg"
      style={{
        background: colors.fill,
        borderColor: colors.stroke,
        borderRadius: isDecision ? 6 : 10,
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
      {spec.label}
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { diagram: DiagramNodeCard };

interface Props {
  spec: DiagramSpec;
  className?: string;
}

function DiagramFlowInner({ spec, className = "" }: Props) {
  const { nodes, edges } = useMemo(() => {
    const positions = layoutDiagramNodes(spec);
    const flowNodes: Node<DiagramNodeData>[] = spec.nodes.map((n) => ({
      id: n.id,
      type: "diagram",
      position: positions.get(n.id) ?? { x: 0, y: 0 },
      data: { spec: n },
    }));
    const flowEdges: Edge[] = spec.edges.map((e, i) => ({
      id: `e-${i}`,
      source: e.source,
      target: e.target,
      label: e.label || undefined,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
      style: { stroke: "#64748b" },
      labelStyle: { fill: "#cbd5e1", fontSize: 10 },
    }));
    return { nodes: flowNodes, edges: flowEdges };
  }, [spec]);

  return (
    <div className={`h-[280px] w-full bg-slate-950 ${className}`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnScroll={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={16} />
        <Controls showInteractive={false} className="!bg-slate-800 !border-slate-600" />
      </ReactFlow>
    </div>
  );
}

export const DiagramFlow = memo(DiagramFlowInner);
