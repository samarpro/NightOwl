import { Position, type Edge, type Node } from "reactflow";
import type { SessionNode, SessionStatus } from "entities/session/model/types";

export type SessionCanvasNodeData = {
  sessionId: string;
  kind: "agent";
  title: string;
  detail: string;
  status: SessionStatus;
  meta?: string;
};

export type SessionCanvasGraph = {
  nodes: Node<SessionCanvasNodeData>[];
  edges: Edge[];
};

const ROOT_X = 72;
const CHILD_X = 420;
const ROOT_Y = 84;
const CHILD_START_Y = 48;
const CHILD_GAP_Y = 184;

export function buildSessionGraph(selectedSessionId: string, sessions: SessionNode[]): SessionCanvasGraph {
  const rootSession = sessions.find((session) => session.id === selectedSessionId);

  if (!rootSession) {
    return { nodes: [], edges: [] };
  }

  const childSessions = sessions
    .filter((session) => session.parentId === selectedSessionId)
    .sort((left, right) => left.startedAt.localeCompare(right.startedAt));

  const nodes: Node<SessionCanvasNodeData>[] = [
    createSessionNode(rootSession, { x: ROOT_X, y: ROOT_Y })
  ];

  const edges: Edge[] = [];

  childSessions.forEach((session, index) => {
    nodes.push(createSessionNode(session, { x: CHILD_X, y: CHILD_START_Y + index * CHILD_GAP_Y }));
    edges.push({
      id: `edge:${selectedSessionId}->${session.id}`,
      source: `agent:${selectedSessionId}`,
      sourceHandle: "agent-right",
      target: `agent:${session.id}`,
      targetHandle: "agent-left",
      type: "sessionCanvasEdge",
      label: "child",
      animated: session.status === "running"
    });
  });

  return { nodes, edges };
}

function createSessionNode(session: SessionNode, position: { x: number; y: number }): Node<SessionCanvasNodeData> {
  return {
    id: `agent:${session.id}`,
    type: "sessionCanvasNode",
    position,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      sessionId: session.id,
      kind: "agent",
      title: session.label,
      detail: session.taskSummary,
      meta: session.currentIntent,
      status: session.status
    }
  };
}
