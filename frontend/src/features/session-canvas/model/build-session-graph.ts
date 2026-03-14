import { Position, type Edge, type Node } from "reactflow";
import type { IntentNode } from "entities/intent/model/types";
import type { SessionNode, SessionStatus } from "entities/session/model/types";
import type { TokenEntry } from "entities/token/model/types";

export type SessionCanvasNodeKind = "agent" | "thinking" | "tool";

export type SessionCanvasNodeData = {
  sessionId: string;
  kind: SessionCanvasNodeKind;
  title: string;
  detail: string;
  status?: SessionStatus;
  meta?: string;
  isExpanded?: boolean;
};

export type SessionCanvasGraph = {
  nodes: Node<SessionCanvasNodeData>[];
  edges: Edge[];
};

const ROOT_X = 72;
const SESSION_DEPTH_X = 0;
const THINKING_X_OFFSET = 400;
const TOOL_X_OFFSET = 700;
const TOOL_SPACING_X = 308;
const CANVAS_TOP_PADDING = 48;
const COLLAPSED_SESSION_GAP = 36;
const EXPANDED_SESSION_GAP = 72;
const ACTION_ROW_GAP = 28;

export function buildSessionGraph(
  selectedSessionId: string,
  sessions: SessionNode[],
  intents: IntentNode[],
  tokens: TokenEntry[],
  expandedSessionIds: Set<string>,
): SessionCanvasGraph {
  const rootSession = sessions.find((session) => session.id === selectedSessionId);

  if (!rootSession) {
    return { nodes: [], edges: [] };
  }

  const sessionMap = new Map(sessions.map((session) => [session.id, session]));
  const childrenByParent = new Map<string, SessionNode[]>();

  for (const session of sessions) {
    if (!session.parentId) {
      continue;
    }

    const siblings = childrenByParent.get(session.parentId) ?? [];
    siblings.push(session);
    childrenByParent.set(session.parentId, siblings);
  }

  const orderedSessions: Array<{ session: SessionNode; depth: number }> = [];

  function visit(sessionId: string, depth: number) {
    const session = sessionMap.get(sessionId);

    if (!session) {
      return;
    }

    orderedSessions.push({ session, depth });

    const children = [...(childrenByParent.get(sessionId) ?? [])].sort((left, right) =>
      left.startedAt.localeCompare(right.startedAt),
    );

    for (const child of children) {
      visit(child.id, depth + 1);
    }
  }

  visit(selectedSessionId, 0);

  const nodes: Node<SessionCanvasNodeData>[] = [];
  const edges: Edge[] = [];
  let cursorY = CANVAS_TOP_PADDING;

  for (const { session, depth } of orderedSessions) {
    const sessionIntents = intents.filter((intent) => intent.sessionId === session.id);
    const sessionToolTokens = tokens.filter(
      (token) =>
        token.sessionId === session.id && (token.type === "tool_call" || token.type === "tool_result"),
    );
    const agentNodeId = `agent:${session.id}`;
    const agentY = cursorY;
    const isExpanded = expandedSessionIds.has(session.id);

    nodes.push({
      id: agentNodeId,
      type: "sessionCanvasNode",
      position: { x: ROOT_X + depth * SESSION_DEPTH_X, y: agentY },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: {
        sessionId: session.id,
        kind: "agent",
        title: session.label,
        detail: session.taskSummary,
        meta: session.currentIntent,
        status: session.status,
        isExpanded
      }
    });

    if (session.parentId && sessionMap.has(session.parentId)) {
      edges.push({
        id: `edge:${session.parentId}->${session.id}`,
        source: `agent:${session.parentId}`,
        sourceHandle: "agent-bottom",
        target: agentNodeId,
        targetHandle: "agent-top",
        type: "sessionCanvasEdge",
        label: "spawn",
        animated: session.status === "running",
        data: {
          style: {
            stroke: "rgba(89, 196, 141, 0.34)",
            strokeWidth: 1.6
          }
        }
      });
    }

    if (!isExpanded) {
      cursorY += estimateNodeHeight(session.label, session.taskSummary, session.currentIntent) + COLLAPSED_SESSION_GAP;
      continue;
    }

    if (sessionIntents.length === 0) {
      const placeholderId = `thinking:${session.id}:current`;
      const placeholderHeight = estimateNodeHeight(
        "Current plan",
        session.currentIntent,
        session.waitReason ? `waiting: ${session.waitReason}` : "no explicit intent graph yet",
      );
      nodes.push({
        id: placeholderId,
        type: "sessionCanvasNode",
        position: { x: THINKING_X_OFFSET + depth * SESSION_DEPTH_X, y: agentY },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          sessionId: session.id,
          kind: "thinking",
          title: "Current plan",
          detail: session.currentIntent,
          meta: session.waitReason ? `waiting: ${session.waitReason}` : "no explicit intent graph yet"
        }
      });
      edges.push({
        id: `edge:${agentNodeId}->${placeholderId}`,
        source: agentNodeId,
        sourceHandle: "agent-right",
        target: placeholderId,
        type: "sessionCanvasEdge",
        data: {
          style: {
            stroke: "rgba(241, 191, 76, 0.32)",
            strokeWidth: 1.5
          }
        }
      });
      cursorY += Math.max(
        estimateNodeHeight(session.label, session.taskSummary, session.currentIntent),
        placeholderHeight,
      ) + EXPANDED_SESSION_GAP;
      continue;
    }

    let actionCursorY = cursorY;
    let tallestActionBottom = agentY + estimateNodeHeight(session.label, session.taskSummary, session.currentIntent);

    sessionIntents.forEach((intent) => {
      const intentNodeId = `thinking:${intent.id}`;
      const intentMeta = `${intent.relationship} · risk ${intent.riskLevel}`;
      const intentHeight = estimateNodeHeight(intent.title, `${intent.service} is ${intent.status}`, intentMeta);
      const intentY = actionCursorY;

      nodes.push({
        id: intentNodeId,
        type: "sessionCanvasNode",
        position: { x: THINKING_X_OFFSET + depth * SESSION_DEPTH_X, y: intentY },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          sessionId: session.id,
          kind: "thinking",
          title: intent.title,
          detail: `${intent.service} is ${intent.status}`,
          meta: intentMeta
        }
      });

      edges.push({
        id: `edge:${agentNodeId}->${intentNodeId}`,
        source: agentNodeId,
        sourceHandle: "agent-right",
        target: intentNodeId,
        type: "sessionCanvasEdge",
        data: {
          style: {
            stroke: "rgba(241, 191, 76, 0.32)",
            strokeWidth: 1.5
          }
        }
      });

      const matchingTools = sessionToolTokens.filter((token) => token.intentId === intent.id);
      let actionRowHeight = intentHeight;
      matchingTools.forEach((token, toolIndex) => {
        const toolNodeId = `tool:${token.id}`;
        const toolTitle = describeToolToken(token);
        const toolDetail = summarizeToken(token.content);
        const toolMeta = new Date(token.createdAt).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit"
        });
        const toolHeight = estimateNodeHeight(toolTitle, toolDetail, toolMeta);
        nodes.push({
          id: toolNodeId,
          type: "sessionCanvasNode",
          position: { x: TOOL_X_OFFSET + depth * SESSION_DEPTH_X + toolIndex * TOOL_SPACING_X, y: intentY },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: {
            sessionId: session.id,
            kind: "tool",
            title: toolTitle,
            detail: toolDetail,
            meta: toolMeta
          }
        });

        edges.push({
          id: `edge:${intentNodeId}->${toolNodeId}`,
          source: intentNodeId,
          target: toolNodeId,
          type: "sessionCanvasEdge",
          animated: token.type === "tool_call",
          data: {
            style: {
              stroke: "rgba(212, 108, 61, 0.4)",
              strokeWidth: 1.6
            }
          }
        });

        actionRowHeight = Math.max(actionRowHeight, toolHeight);
      });

      actionCursorY += actionRowHeight + ACTION_ROW_GAP;
      tallestActionBottom = Math.max(tallestActionBottom, intentY + actionRowHeight);
    });

    cursorY = tallestActionBottom + EXPANDED_SESSION_GAP;
  }

  return { nodes, edges };
}

function describeToolToken(token: TokenEntry) {
  try {
    const parsed = JSON.parse(token.content) as { tool?: string; candidate?: string };
    if (parsed.tool) {
      return parsed.tool;
    }

    if (parsed.candidate) {
      return `result: ${parsed.candidate}`;
    }
  } catch {
    return token.type === "tool_call" ? "tool call" : "tool result";
  }

  return token.type === "tool_call" ? "tool call" : "tool result";
}

function summarizeToken(content: string) {
  const normalized = content.replace(/\s+/g, " ").trim();
  return normalized.length > 72 ? `${normalized.slice(0, 69)}...` : normalized;
}

function estimateNodeHeight(title: string, detail: string, meta?: string) {
  const titleLines = estimateTextLines(title, 24);
  const detailLines = estimateTextLines(detail, 32);
  const metaLines = meta ? estimateTextLines(meta, 32) : 0;
  return 68 + titleLines * 22 + detailLines * 18 + metaLines * 16;
}

function estimateTextLines(value: string, charsPerLine: number) {
  if (!value.trim()) {
    return 1;
  }

  return Math.max(
    1,
    value
      .split("\n")
      .map((segment) => Math.ceil(segment.trim().length / charsPerLine) || 1)
      .reduce((total, count) => total + count, 0),
  );
}
