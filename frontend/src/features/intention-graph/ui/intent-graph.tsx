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

type ApiIntentNode = {
  id: string;
  label: string;
  type: string;
  service: string;
  intent: string;
  summary: string;
  token_start: number;
  token_end: number;
  started_at: number;
  ended_at: number;
};

function statusColor(type: string) {
  if (type === "completed") return "#22c55e";
  if (type === "failed") return "#ef4444";
  if (type === "waiting") return "#eab308";
  return "#3b82f6";
}

function transformToReactFlow(
  graph: { nodes: ApiIntentNode[]; edges: Array<{ source: string; target: string; label: string }> }
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = graph.nodes.map((n, index) => ({
    id: n.id,
    data: {
      label: (
        <div style={{ textAlign: "left" }}>
          <div style={{ fontWeight: 700, fontSize: "13px", marginBottom: "4px", opacity: 0.7 }}>
            {n.service}/{n.intent}
          </div>
          <div style={{ fontSize: "13px", lineHeight: 1.4 }}>
            {n.summary}
          </div>
          {n.ended_at > 0 && n.started_at > 0 && (
            <div style={{ fontSize: "11px", marginTop: "6px", opacity: 0.6 }}>
              {Math.round(n.ended_at - n.started_at)}s
            </div>
          )}
        </div>
      ),
    },
    position: { x: 100 + (index % 2) * 220, y: index * 220 },
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    style: {
      background: statusColor(n.type),
      color: "#fff",
      padding: "16px 20px",
      borderRadius: "12px",
      border: "2px solid rgba(255,255,255,0.15)",
      fontSize: "14px",
      minWidth: "240px",
      maxWidth: "360px",
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
