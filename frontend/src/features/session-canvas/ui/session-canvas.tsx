import { memo, useEffect, useMemo, useState, type CSSProperties } from "react";
import ReactFlow, {
  Background,
  BaseEdge,
  Controls,
  Handle,
  MarkerType,
  Position,
  getSmoothStepPath,
  type Node,
  type EdgeProps,
  type NodeProps
} from "reactflow";
import "reactflow/dist/style.css";
import type { IntentNode } from "entities/intent/model/types";
import type { SessionNode } from "entities/session/model/types";
import type { TokenEntry } from "entities/token/model/types";
import {
  buildSessionGraph,
  type SessionCanvasNodeData
} from "features/session-canvas/model/build-session-graph";
import robotIcon from "shared/assets/robot.svg";
import brainIcon from "shared/assets/brain.svg";
import toolIcon from "shared/assets/tool.svg";

type SessionCanvasProps = {
  selectedSession: SessionNode;
  sessions: SessionNode[];
  intents: IntentNode[];
  tokens: TokenEntry[];
};

const nodeTypes = {
  sessionCanvasNode: memo(SessionCanvasNode)
};

const edgeTypes = {
  sessionCanvasEdge: memo(SessionCanvasEdge)
};

export function SessionCanvas({ selectedSession, sessions, intents, tokens }: SessionCanvasProps) {
  const [expandedSessionIds, setExpandedSessionIds] = useState<Set<string>>(() => new Set([selectedSession.id]));

  useEffect(() => {
    setExpandedSessionIds(new Set([selectedSession.id]));
  }, [selectedSession.id]);

  const graph = useMemo(
    () => buildSessionGraph(selectedSession.id, sessions, intents, tokens, expandedSessionIds),
    [expandedSessionIds, intents, selectedSession.id, sessions, tokens],
  );

  const edges = useMemo(
    () =>
      graph.edges.map((edge) => ({
        ...edge,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: "rgba(240, 232, 220, 0.24)", strokeWidth: 1.25 },
        labelStyle: { fill: "rgba(184, 174, 161, 0.88)", fontSize: 11 }
      })),
    [graph.edges],
  );

  function handleNodeClick(_: React.MouseEvent, node: Node<SessionCanvasNodeData>) {
    if (node.data.kind !== "agent") {
      return;
    }

    setExpandedSessionIds((current) => {
      const next = new Set(current);
      if (next.has(node.data.sessionId)) {
        next.delete(node.data.sessionId);
      } else {
        next.add(node.data.sessionId);
      }
      return next;
    });
  }

  return (
    <div className="session-canvas-shell">
      <div className="session-canvas-shell__header">
        <div>
          <h2>{selectedSession.taskSummary}</h2>
          <p>{selectedSession.currentIntent}</p>
        </div>
        <span className={`badge badge--${selectedSession.status}`}>{selectedSession.status}</span>
      </div>

      <div className="session-canvas">
        <ReactFlow
          edges={edges}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.18 }}
          nodes={graph.nodes}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          nodesConnectable={false}
          nodesDraggable={false}
          panOnScroll
          proOptions={{ hideAttribution: true }}
        >
          <Background color="rgba(240, 232, 220, 0.08)" gap={24} size={1.2} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}

function SessionCanvasNode({ data }: NodeProps<SessionCanvasNodeData>) {
  const iconSrc = data.kind === "agent" ? robotIcon : data.kind === "thinking" ? brainIcon : toolIcon;
  const iconAlt = data.kind === "agent" ? "Agent" : data.kind === "thinking" ? "Thinking" : "Tool call";

  return (
    <article className={`canvas-node canvas-node--${data.kind}`} data-status={data.status}>
      <Handle
        className="canvas-node__handle"
        id={data.kind === "agent" ? "agent-left" : undefined}
        isConnectable={false}
        position={Position.Left}
        type="target"
      />
      {data.kind === "agent" ? (
        <Handle
          className="canvas-node__handle"
          id="agent-top"
          isConnectable={false}
          position={Position.Top}
          type="target"
        />
      ) : null}
      <span className="canvas-node__icon" aria-hidden="true">
        <img alt={iconAlt} className="canvas-node__icon-image" src={iconSrc} />
      </span>
      <div className="canvas-node__content">
        <strong>{data.title}</strong>
        <p>{data.detail}</p>
        {data.meta ? <span>{data.meta}</span> : null}
      </div>
      {data.kind === "agent" ? (
        <span className="canvas-node__expander" aria-hidden="true">
          {data.isExpanded ? "Collapse" : "Expand"}
        </span>
      ) : null}
      <Handle
        className="canvas-node__handle"
        id={data.kind === "agent" ? "agent-right" : undefined}
        isConnectable={false}
        position={Position.Right}
        type="source"
      />
      {data.kind === "agent" ? (
        <Handle
          className="canvas-node__handle"
          id="agent-bottom"
          isConnectable={false}
          position={Position.Bottom}
          type="source"
        />
      ) : null}
    </article>
  );
}

function SessionCanvasEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition = Position.Right,
  targetPosition = Position.Left,
  markerEnd,
  style
}: EdgeProps) {
  const [path] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 18,
    offset: 28
  });

  return (
    <>
      <BaseEdge id={id} markerEnd={markerEnd} path={path} style={style as CSSProperties | undefined} />
      <path className="canvas-edge-accent" d={path} />
    </>
  );
}
