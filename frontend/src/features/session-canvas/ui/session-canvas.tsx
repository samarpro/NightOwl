import { useMutation, useQueries } from "@tanstack/react-query";
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
import { fetchSessionMessages } from "shared/api/sessions";
import { correctShadow, createShadow, messageShadow } from "shared/api/shadow";
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
  const [expandedToolCallIds, setExpandedToolCallIds] = useState<Set<string>>(() => new Set());
  const [activeAgentSessionId, setActiveAgentSessionId] = useState<string | null>(null);
  const [shadowInput, setShadowInput] = useState("");
  const [shadowReply, setShadowReply] = useState<string | null>(null);
  const [shadowIdsBySession, setShadowIdsBySession] = useState<Record<string, string>>({});
  const messageQueries = useQueries({
    queries: sessions.map((session) => ({
      queryKey: ["sessions", session.id, "messages"],
      queryFn: () => fetchSessionMessages(session.id)
    }))
  });

  useEffect(() => {
    setExpandedToolCallIds(new Set());
  }, [selectedSession.id]);

  useEffect(() => {
    setActiveAgentSessionId(null);
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

  const messagesBySession = useMemo(
    () =>
      sessions.reduce<Record<string, Awaited<ReturnType<typeof fetchSessionMessages>>>>((accumulator, session, index) => {
        accumulator[session.id] = messageQueries[index]?.data ?? [];
        return accumulator;
      }, {}),
    [messageQueries, sessions]
  );

  const hasMessageError = messageQueries.some((query) => query.isError);
  const loadedMessageGroups = messageQueries.reduce(
    (total, query) => total + (query.data?.length ?? 0),
    0
  );
  const activeAgent = sessions.find((session) => session.id === activeAgentSessionId) ?? null;

  const graph = useMemo(
    () =>
      buildSessionGraph(
        selectedSession.id,
        sessions,
        messagesBySession,
        expandedToolCallIds,
        (sessionId) => {
          setActiveAgentSessionId(sessionId);
          setShadowInput("");
          setShadowReply(null);
        },
        (toolCallId) => {
          setExpandedToolCallIds((current) => {
            const next = new Set(current);
            if (next.has(toolCallId)) {
              next.delete(toolCallId);
            } else {
              next.add(toolCallId);
            }
            return next;
          });
        }
      ),
    [expandedToolCallIds, messagesBySession, selectedSession.id, sessions]
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
          <p>
            {sessions.length} agent lane(s) and {loadedMessageGroups} persisted message group(s) loaded.
          </p>
        </div>
        <span className={`badge badge--${selectedSession.status}`}>{selectedSession.status}</span>
      </div>

      <div className="session-canvas">
        {hasMessageError ? (
          <div className="session-canvas__overlay">Failed to load one or more session message streams.</div>
        ) : null}
        {activeAgent ? (
          <div className="session-shadow-panel">
            <div className="session-shadow-panel__header">
              <div>
                <strong>{activeAgent.label}</strong>
                <span>Shadow steer and correction</span>
              </div>
              <button
                className="button button--ghost"
                onClick={() => {
                  setActiveAgentSessionId(null);
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
                  void withShadow(activeAgent.id, async (shadowId) => {
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
                  void withShadow(activeAgent.id, async (shadowId) => {
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
  if (data.kind === "tool_call") {
    return (
      <button
        className="canvas-node canvas-node--tool-call"
        onClick={() => {
          if (data.toolCallId) {
            data.onToggleToolCall?.(data.toolCallId);
          }
        }}
        type="button"
      >
        <span className="canvas-node__icon" aria-hidden="true">
          <img alt="Tool" className="canvas-node__icon-image" src={robotIcon} />
        </span>
        <div className="canvas-node__content">
          <strong>{data.title}</strong>
          <p>{data.detail}</p>
          {typeof data.resultCount === "number" ? (
            <span>{data.isExpanded ? "Hide" : "Show"} {data.resultCount} tool result(s)</span>
          ) : null}
        </div>
      </button>
    );
  }

  if (data.kind === "tool_result") {
    return (
      <article className="canvas-node canvas-node--tool-result">
        <div className="canvas-node__content">
          <strong>{data.title}</strong>
          <p>{data.detail}</p>
          {data.meta ? <span>{data.meta}</span> : null}
        </div>
      </article>
    );
  }

  if (data.kind === "text") {
    return (
      <article className="canvas-node canvas-node--text">
        <div className="canvas-node__content">
          <strong>{data.title}</strong>
          <p>{data.detail}</p>
          {data.meta ? <span>{data.meta}</span> : null}
        </div>
      </article>
    );
  }

  return (
    <button
      className="canvas-node canvas-node--agent"
      data-status={data.status}
      onClick={() => data.onSelectAgent?.(data.sessionId)}
      type="button"
    >
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
    </button>
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
