import { memo, useCallback, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  type Edge,
  type Node,
  type NodeMouseHandler,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { useIntentGraph } from "../model/use-intent-graph";
import { fetchTokenRange, type TokenEntry } from "shared/api/observability";

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

type IntentNodeData = {
  service: string;
  intent: string;
  status: string;
  summary: string;
  selected: boolean;
};

const serviceEmoji: Record<string, string> = {
  gmail: "\u{1F4E7}",
  calendar: "\u{1F4C5}",
  "web-search": "\u{1F50D}",
  browser: "\u{1F310}",
  slack: "\u{1F4AC}",
  github: "\u{1F4BB}",
  internal: "\u{2699}\u{FE0F}",
  composio: "\u{1F9E9}",
  bash: "\u{1F4DF}",
  filesystem: "\u{1F4C1}",
  database: "\u{1F5C4}\u{FE0F}",
};

function emojiForService(service: string) {
  const key = service.toLowerCase();
  if (serviceEmoji[key]) return serviceEmoji[key];
  for (const [k, v] of Object.entries(serviceEmoji)) {
    if (key.includes(k)) return v;
  }
  return "\u{1F916}";
}

function statusLabel(type: string) {
  switch (type) {
    case "completed": return "Completed.";
    case "in_progress": return "Currently executing.";
    case "waiting": return "Waiting.";
    case "failed": return "Failed.";
    default: return type;
  }
}

function statusBadgeClass(type: string) {
  switch (type) {
    case "completed": return "badge--completed";
    case "in_progress": return "badge--running";
    case "waiting": return "badge--waiting";
    case "failed": return "badge--blocked";
    default: return "";
  }
}

function IntentNodeComponent({ data }: NodeProps<IntentNodeData>) {
  return (
    <div
      className="canvas-node"
      style={{
        borderColor: data.selected
          ? "rgba(89, 196, 141, 0.6)"
          : "var(--line)",
        cursor: "pointer",
        minWidth: 260,
        maxWidth: 320,
      }}
    >
      <Handle
        className="canvas-node__handle"
        id="top"
        isConnectable={false}
        position={Position.Top}
        type="target"
      />
      <span
        className="canvas-node__icon"
        style={{ fontSize: "18px", lineHeight: 1 }}
        aria-hidden="true"
      >
        {emojiForService(data.service)}
      </span>
      <div className="canvas-node__content">
        <strong>{data.intent}</strong>
        <span>{statusLabel(data.status)}</span>
      </div>
      <Handle
        className="canvas-node__handle"
        id="bottom"
        isConnectable={false}
        position={Position.Bottom}
        type="source"
      />
    </div>
  );
}

const nodeTypes = { intentNode: memo(IntentNodeComponent) };

function transformToReactFlow(
  graph: { nodes: ApiIntentNode[]; edges: Array<{ source: string; target: string; label: string }> },
  selectedNodeId: string | null,
): { nodes: Node<IntentNodeData>[]; edges: Edge[] } {
  const nodes: Node<IntentNodeData>[] = graph.nodes.map((n, index) => ({
    id: n.id,
    type: "intentNode",
    data: {
      service: n.service,
      intent: n.intent,
      status: n.type,
      summary: n.summary,
      selected: selectedNodeId === n.id,
    },
    position: { x: 80 + (index % 2) * 200, y: index * 140 },
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
  }));

  const edges: Edge[] = graph.edges.map((e, index) => ({
    id: `e${index}`,
    source: e.source,
    target: e.target,
    sourceHandle: "bottom",
    targetHandle: "top",
    type: "smoothstep",
    animated: true,
    style: { stroke: "rgba(240, 232, 220, 0.24)", strokeWidth: 1.25 },
    labelStyle: { fill: "rgba(184, 174, 161, 0.88)", fontSize: 11 },
  }));

  return { nodes, edges };
}

// --- Event list (token drill-down) ---

function tokenNodeVariant(type: string) {
  switch (type) {
    case "tool_call": return { cls: "canvas-node--tool-call", title: "Tool Call" };
    case "tool_result": return { cls: "canvas-node--tool-result", title: "Tool Result" };
    case "thinking": return { cls: "canvas-node--text", title: "Thinking" };
    case "response": return { cls: "canvas-node--text", title: "Response" };
    case "spawn": return { cls: "canvas-node--agent", title: "Spawn" };
    case "completion": return { cls: "canvas-node--agent", title: "Completion" };
    default: return { cls: "canvas-node--text", title: type };
  }
}

function formatTokenArgs(token: TokenEntry) {
  if (token.type === "tool_call" && token.metadata?.args) {
    const args = String(token.metadata.args);
    return args.length > 220 ? `${args.slice(0, 217)}...` : args;
  }
  return null;
}

function EventList({ sessionId, tokenStart, tokenEnd }: { sessionId: string; tokenStart: number; tokenEnd: number }) {
  const { data: tokens, isLoading } = useQuery({
    queryKey: ["token-range", sessionId, tokenStart, tokenEnd],
    queryFn: () => fetchTokenRange(sessionId, tokenStart, tokenEnd),
  });

  if (isLoading) {
    return <div style={{ padding: "12px", color: "var(--text-soft)" }}>Loading events...</div>;
  }

  if (!tokens || tokens.length === 0) {
    return <div style={{ padding: "12px", color: "var(--text-soft)" }}>No events for this node.</div>;
  }

  return (
    <div style={{ display: "grid", gap: "8px" }}>
      {tokens.map((token: TokenEntry, i: number) => {
        const { cls, title } = tokenNodeVariant(token.type);
        const args = formatTokenArgs(token);
        return (
          <article className={`canvas-node ${cls}`} key={i} style={{ minWidth: 0, maxWidth: "100%" }}>
            <div className="canvas-node__content">
              <strong>{title}{token.type === "tool_call" ? `: ${token.content}` : ""}</strong>
              {token.type !== "tool_call" && <p>{token.content}</p>}
              {args && <p>{args}</p>}
            </div>
          </article>
        );
      })}
    </div>
  );
}

// --- Main component ---

export function IntentGraph({ sessionId }: IntentGraphProps) {
  const { data, isLoading, error } = useIntentGraph(sessionId);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const selectedNode = useMemo(() => {
    if (!data || !selectedNodeId) return null;
    return (data.nodes as ApiIntentNode[]).find((n) => n.id === selectedNodeId) ?? null;
  }, [data, selectedNodeId]);

  const { nodes, edges } = useMemo(() => {
    if (!data || !data.nodes.length) {
      return { nodes: [], edges: [] };
    }
    return transformToReactFlow(data as { nodes: ApiIntentNode[]; edges: typeof data.edges }, selectedNodeId);
  }, [data, selectedNodeId]);

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNodeId((prev) => (prev === node.id ? null : node.id));
  }, []);

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
    <div className="intent-graph-wrapper">
      <div className="intent-graph-container" style={{ height: "340px", width: "100%" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          attributionPosition="bottom-left"
          nodesConnectable={false}
          nodesDraggable={false}
        >
          <Background color="rgba(240, 232, 220, 0.08)" gap={24} size={1.2} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      {selectedNode && (
        <div className="intent-detail-panel">
          <div className="intent-detail-panel__header">
            <span style={{ fontSize: "20px" }}>{emojiForService(selectedNode.service)}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <strong>{selectedNode.service}/{selectedNode.intent}</strong>
                <span className={`badge ${statusBadgeClass(selectedNode.type)}`}>
                  {selectedNode.type}
                </span>
              </div>
              {selectedNode.summary && (
                <p style={{ margin: "4px 0 0", color: "var(--text-soft)", fontSize: "0.85rem", lineHeight: 1.4 }}>
                  {selectedNode.summary}
                </p>
              )}
            </div>
          </div>
          <EventList
            sessionId={sessionId}
            tokenStart={selectedNode.token_start}
            tokenEnd={selectedNode.token_end}
          />
        </div>
      )}
    </div>
  );
}
