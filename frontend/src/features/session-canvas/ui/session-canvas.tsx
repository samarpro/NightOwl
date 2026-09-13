import { useMutation } from "@tanstack/react-query";
import { memo, useEffect, useMemo, useState, type CSSProperties } from "react";
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
import { correctShadow, createShadow, messageShadow } from "shared/api/shadow";
import robotIcon from "shared/assets/robot.svg";

type SessionCanvasProps = {
  selectedSession: SessionNode;
  sessions: SessionNode[];
  onSelectAgent: (sessionId: string) => void;
};

const nodeTypes = {
  sessionCanvasNode: memo(SessionCanvasNode)
};

const edgeTypes = {
  sessionCanvasEdge: memo(SessionCanvasEdge)
};

export function SessionCanvas({ selectedSession, sessions, onSelectAgent }: SessionCanvasProps) {
  const [shadowAgentSessionId, setShadowAgentSessionId] = useState<string | null>(null);
  const [shadowInput, setShadowInput] = useState("");
  const [shadowReply, setShadowReply] = useState<string | null>(null);
  const [shadowIdsBySession, setShadowIdsBySession] = useState<Record<string, string>>({});

  useEffect(() => {
    setShadowAgentSessionId(null);
    setShadowInput("");
    setShadowReply(null);
  }, [selectedSession.id]);

  const createShadowMutation = useMutation({
    mutationFn: ({ sessionId }: { sessionId: string }) => createShadow(sessionId)
  });
  const askShadowMutation = useMutation({
    mutationFn: ({ shadowId, message }: { shadowId: string; message: string }) => messageShadow(shadowId, message)
  });
  const correctShadowMutation = useMutation({
    mutationFn: ({ shadowId, message }: { shadowId: string; message: string }) => correctShadow(shadowId, message)
  });

  const shadowAgent = sessions.find((session) => session.id === shadowAgentSessionId) ?? null;

  const graph = useMemo(
    () =>
      buildSessionGraph(
        selectedSession.id,
        sessions,
        onSelectAgent,
        (sessionId) => {
          setShadowAgentSessionId(sessionId);
          setShadowInput("");
          setShadowReply(null);
        },
      ),
    [selectedSession.id, sessions, onSelectAgent]
  );

  async function withShadow(sessionId: string, callback: (shadowId: string) => Promise<void>) {
    let shadowId = shadowIdsBySession[sessionId];

    if (!shadowId) {
      const created = await createShadowMutation.mutateAsync({ sessionId });
      shadowId = created.shadow_id;
      setShadowIdsBySession((current) => ({
        ...current,
        [sessionId]: shadowId
      }));
    }

    await callback(shadowId);
  }

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
          <p>{sessions.length} agent session(s)</p>
        </div>
        <span className={`badge badge--${selectedSession.status}`}>{selectedSession.status}</span>
      </div>

      <div className="session-canvas">
        {shadowAgent ? (
          <div className="session-shadow-panel">
            <div className="session-shadow-panel__header">
              <div>
                <strong>{shadowAgent.label}</strong>
                <span>Shadow steer and correction</span>
              </div>
              <button
                className="button button--ghost"
                onClick={() => {
                  setShadowAgentSessionId(null);
                  setShadowInput("");
                  setShadowReply(null);
                }}
                type="button"
              >
                Close
              </button>
            </div>
            <textarea
              className="session-shadow-panel__input"
              onChange={(event) => setShadowInput(event.target.value)}
              placeholder="Ask the shadow what the agent is doing, or write a correction to redirect it."
              rows={5}
              value={shadowInput}
            />
            <div className="session-shadow-panel__actions">
              <button
                className="button button--ghost"
                disabled={!shadowInput.trim() || askShadowMutation.isPending || correctShadowMutation.isPending}
                onClick={() => {
                  void withShadow(shadowAgent.id, async (shadowId) => {
                    const result = await askShadowMutation.mutateAsync({
                      shadowId,
                      message: shadowInput.trim()
                    });
                    setShadowReply(result.reply);
                  });
                }}
                type="button"
              >
                {askShadowMutation.isPending ? "Asking..." : "Ask shadow"}
              </button>
              <button
                className="button button--primary"
                disabled={!shadowInput.trim() || createShadowMutation.isPending || correctShadowMutation.isPending}
                onClick={() => {
                  void withShadow(shadowAgent.id, async (shadowId) => {
                    await correctShadowMutation.mutateAsync({
                      shadowId,
                      message: shadowInput.trim()
                    });
                    setShadowReply("Correction sent to the live agent.");
                    setShadowInput("");
                  });
                }}
                type="button"
              >
                {correctShadowMutation.isPending ? "Redirecting..." : "Redirect agent"}
              </button>
            </div>
            {createShadowMutation.isError ? <span className="muted">{createShadowMutation.error.message}</span> : null}
            {askShadowMutation.isError ? <span className="muted">{askShadowMutation.error.message}</span> : null}
            {correctShadowMutation.isError ? <span className="muted">{correctShadowMutation.error.message}</span> : null}
            {shadowReply ? (
              <div className="session-shadow-panel__reply">
                <strong>Shadow reply</strong>
                <p>{shadowReply}</p>
              </div>
            ) : null}
          </div>
        ) : null}
        <ReactFlow
          defaultViewport={{ x: 0, y: 0, zoom: 0.9 }}
          edges={edges}
          edgeTypes={edgeTypes}
          maxZoom={1.1}
          minZoom={0.35}
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
    <button
      className="canvas-node canvas-node--agent"
      data-status={data.status}
      onClick={() => data.onSelectAgent?.(data.sessionId)}
      onDoubleClick={() => data.onDoubleClickAgent?.(data.sessionId)}
      type="button"
    >
      <Handle
        className="canvas-node__handle"
        id="agent-top"
        isConnectable={false}
        position={Position.Top}
        type="target"
      />
      <span className="canvas-node__icon" aria-hidden="true">
        <img alt="Session" className="canvas-node__icon-image" src={robotIcon} />
      </span>
      <div className="canvas-node__content">
        <strong>{data.title}</strong>
        {data.status ? <span>{data.status}</span> : null}
      </div>
      <Handle
        className="canvas-node__handle"
        id="agent-bottom"
        isConnectable={false}
        position={Position.Bottom}
        type="source"
      />
    </button>
  );
}

function SessionCanvasEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition = Position.Bottom,
  targetPosition = Position.Top,
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
