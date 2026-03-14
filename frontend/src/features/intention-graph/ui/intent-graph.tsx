import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { useIntentGraph } from "../model/use-intent-graph";

type IntentGraphProps = {
  sessionId: string;
};

function transformToReactFlow(
  graph: { nodes: Array<{ id: string; label: string; type: string }>; edges: Array<{ source: string; target: string; label: string }> }
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = graph.nodes.map((n, index) => ({
    id: n.id,
    data: { label: n.label },
    position: { x: 100 + (index % 2) * 200, y: index * 180 },
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    style: {
      background: n.type === "completed" ? "#22c55e" : n.type === "waiting" ? "#eab308" : "#3b82f6",
      color: "#fff",
      padding: "16px 24px",
      borderRadius: "12px",
      border: "2px solid rgba(255,255,255,0.15)",
      fontSize: "14px",
      minWidth: "180px",
      textAlign: "center",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
    },
  }));

  const edges: Edge[] = graph.edges.map((e, index) => ({
    id: `e${index}`,
    source: e.source,
    target: e.target,
    label: e.label,
    type: "smoothstep",
    animated: true,
    style: { stroke: "#6b7280", strokeWidth: 2 },
    labelStyle: { fill: "#9ca3af", fontWeight: 600 },
    labelBgStyle: { fill: "#1f2937", fillOpacity: 0.9 },
    labelBgPadding: [8, 4] as [number, number],
    labelBgBorderRadius: 4,
    curveOffset: 50,
  }));

  return { nodes, edges };
}

export function IntentGraph({ sessionId }: IntentGraphProps) {
  const { data, isLoading, error } = useIntentGraph(sessionId);

  const { nodes, edges } = useMemo(() => {
    if (!data || !data.nodes.length) {
      return { nodes: [], edges: [] };
    }
    return transformToReactFlow(data);
  }, [data]);

  if (isLoading) {
    return (
      <div className="intent-graph-loading">
        <span>Loading intent graph...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="intent-graph-error">
        <span>Failed to load intent graph</span>
      </div>
    );
  }

  if (!nodes.length) {
    return (
      <div className="intent-graph-empty">
        <span>No intents recorded yet</span>
      </div>
    );
  }

  return (
    <div className="intent-graph-container" style={{ height: "500px", width: "100%" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#374151" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
