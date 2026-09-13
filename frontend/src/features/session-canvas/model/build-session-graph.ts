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

const NODE_WIDTH = 280;
const H_GAP = 60;
const V_GAP = 140;

/**
 * Build a tree layout from a flat list of sessions.
 * Root is the selected session; every other session is placed
 * under its parent, recursively.
 */
export function buildSessionGraph(
  selectedSessionId: string,
  sessions: SessionNode[],
  onSelectAgent: (sessionId: string) => void,
  onDoubleClickAgent: (sessionId: string) => void,
): SessionCanvasGraph {
  const byId = new Map(sessions.map((s) => [s.id, s]));
  const childrenOf = new Map<string, SessionNode[]>();

  for (const s of sessions) {
    const pid = s.parentId ?? "__root__";
    const list = childrenOf.get(pid) ?? [];
    list.push(s);
    childrenOf.set(pid, list);
  }

  // Sort children by start time
  for (const list of childrenOf.values()) {
    list.sort((a, b) => a.startedAt.localeCompare(b.startedAt));
  }

  const root = byId.get(selectedSessionId);
  if (!root) {
    return { nodes: [], edges: [] };
  }

  const nodes: Node<SessionCanvasNodeData>[] = [];
  const edges: Edge[] = [];

  // Compute subtree widths for centering
  function subtreeWidth(id: string): number {
    const kids = childrenOf.get(id) ?? [];
    if (kids.length === 0) return NODE_WIDTH;
    const total = kids.reduce((sum, kid) => sum + subtreeWidth(kid.id), 0);
    return total + H_GAP * (kids.length - 1);
  }

  function layout(session: SessionNode, x: number, y: number) {
    nodes.push(createSessionNode(session, { x, y }, onSelectAgent, onDoubleClickAgent));

    const kids = childrenOf.get(session.id) ?? [];
    if (kids.length === 0) return;

    const totalWidth = subtreeWidth(session.id);
    let cursorX = x - totalWidth / 2 + NODE_WIDTH / 2;
    const childY = y + V_GAP;

    for (const kid of kids) {
      const kidWidth = subtreeWidth(kid.id);
      const kidX = cursorX + kidWidth / 2 - NODE_WIDTH / 2;
      layout(kid, kidX, childY);

      edges.push({
        id: `edge:${session.id}->${kid.id}`,
        source: `agent:${session.id}`,
        sourceHandle: "agent-bottom",
        target: `agent:${kid.id}`,
        targetHandle: "agent-top",
        type: "sessionCanvasEdge",
        label: "child",
        animated: kid.status === "running",
      });

      cursorX += kidWidth + H_GAP;
    }
  }

  layout(root, 400, 60);

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
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
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
