import { Position, type Edge, type Node } from "reactflow";
import type { SessionNode, SessionStatus } from "entities/session/model/types";

export type SessionCanvasNodeData = {
  sessionId: string;
  kind: "agent";
  title: string;
  detail: string;
  status?: SessionStatus;
  meta?: string;
  onSelectAgent?: (sessionId: string) => void;
  onDoubleClickAgent?: (sessionId: string) => void;
};

export type SessionCanvasGraph = {
  nodes: Node<SessionCanvasNodeData>[];
  edges: Edge[];
};

const ROOT_X = 72;
const ROOT_Y = 84;
const LANE_X_GAP = 560;

export function buildSessionGraph(
  selectedSessionId: string,
  sessions: SessionNode[],
  onSelectAgent: (sessionId: string) => void,
  onDoubleClickAgent: (sessionId: string) => void,
): SessionCanvasGraph {
  const rootSession = sessions.find((session) => session.id === selectedSessionId);

  if (!rootSession) {
    return { nodes: [], edges: [] };
  }

  const childSessions = sessions
    .filter((session) => session.parentId === selectedSessionId)
    .sort((left, right) => left.startedAt.localeCompare(right.startedAt));

  const orderedSessions = [rootSession, ...childSessions];
  const nodes: Node<SessionCanvasNodeData>[] = [];
  const edges: Edge[] = [];
  orderedSessions.forEach((session, sessionIndex) => {
    const laneX = ROOT_X + sessionIndex * LANE_X_GAP;
    nodes.push(createSessionNode(session, { x: laneX, y: ROOT_Y }, onSelectAgent, onDoubleClickAgent));

    if (session.parentId === selectedSessionId) {
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
    }
  });

  return { nodes, edges };
}

function createSessionNode(
  session: SessionNode,
  position: { x: number; y: number },
  onSelectAgent: (sessionId: string) => void,
  onDoubleClickAgent: (sessionId: string) => void,
): Node<SessionCanvasNodeData> {
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
      onSelectAgent,
      onDoubleClickAgent,
      status: session.status
    }
  };
}
