import { memo, useMemo, type CSSProperties } from "react";
import ReactFlow, {
  Background,
  BaseEdge,
  Controls,
  Handle,
  MarkerType,
  Position,
  getSmoothStepPath,
  type EdgeProps,
  type NodeProps
} from "reactflow";
import "reactflow/dist/style.css";
import type { SessionNode } from "entities/session/model/types";
import {
  buildSessionGraph,
  type SessionCanvasNodeData
} from "features/session-canvas/model/build-session-graph";
import robotIcon from "shared/assets/robot.svg";

type SessionCanvasProps = {
  selectedSession: SessionNode;
  sessions: SessionNode[];
};

const nodeTypes = {
  sessionCanvasNode: memo(SessionCanvasNode)
};

const edgeTypes = {
  sessionCanvasEdge: memo(SessionCanvasEdge)
};

export function SessionCanvas({ selectedSession, sessions }: SessionCanvasProps) {
  const graph = useMemo(() => buildSessionGraph(selectedSession.id, sessions), [selectedSession.id, sessions]);

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

  return (
    <div className="session-canvas-shell">
      <div className="session-canvas-shell__header">
        <div>
          <h2>{selectedSession.taskSummary}</h2>
          <p>{sessions.length - 1} direct child sessions loaded for this root session.</p>
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
  return (
    <article className="canvas-node canvas-node--agent" data-status={data.status}>
      <Handle
        className="canvas-node__handle"
        id="agent-left"
        isConnectable={false}
        position={Position.Left}
        type="target"
      />
      <span className="canvas-node__icon" aria-hidden="true">
        <img alt="Session" className="canvas-node__icon-image" src={robotIcon} />
      </span>
      <div className="canvas-node__content">
        <strong>{data.title}</strong>
        <p>{data.detail}</p>
        {data.meta ? <span>{data.meta}</span> : null}
      </div>
      <Handle
        className="canvas-node__handle"
        id="agent-right"
        isConnectable={false}
        position={Position.Right}
        type="source"
      />
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
