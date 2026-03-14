import { Position, type Edge, type Node } from "reactflow";
import type { SessionNode, SessionStatus } from "entities/session/model/types";
import type { ApiSessionMessageDto } from "shared/api/contracts";

export type SessionCanvasNodeData = {
  sessionId: string;
  kind: "agent" | "text" | "tool_call" | "tool_result";
  title: string;
  detail: string;
  status?: SessionStatus;
  meta?: string;
  onSelectAgent?: (sessionId: string) => void;
  onToggleToolCall?: (toolCallId: string) => void;
  resultCount?: number;
  toolCallId?: string;
  toolName?: string;
  isExpanded?: boolean;
};

export type SessionCanvasGraph = {
  nodes: Node<SessionCanvasNodeData>[];
  edges: Edge[];
};

const ROOT_X = 72;
const ROOT_Y = 84;
const LANE_X_GAP = 560;
const MESSAGE_START_Y_OFFSET = 210;
const MESSAGE_GAP_Y = 160;

export function buildSessionGraph(
  selectedSessionId: string,
  sessions: SessionNode[],
  messagesBySession: Record<string, ApiSessionMessageDto[]>,
  expandedToolCallIds: Set<string>,
  onSelectAgent: (sessionId: string) => void,
  onToggleToolCall: (toolCallId: string) => void
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
    nodes.push(createSessionNode(session, { x: laneX, y: ROOT_Y }, onSelectAgent));

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

    const messageEntries = createMessageEntries(session.id, messagesBySession[session.id] ?? [], expandedToolCallIds);

    messageEntries.forEach((entry, entryIndex) => {
      nodes.push(
        createMessageNode(
          entry,
          {
            x: laneX,
            y: ROOT_Y + MESSAGE_START_Y_OFFSET + entryIndex * MESSAGE_GAP_Y
          },
          onToggleToolCall
        )
      );
      edges.push({
        id: `edge:${session.id}->${entry.id}`,
        source: entry.parentId ?? `agent:${session.id}`,
        target: entry.id,
        type: "sessionCanvasEdge",
        animated: entry.kind === "tool_result"
      });
    });
  });

  return { nodes, edges };
}

function createSessionNode(
  session: SessionNode,
  position: { x: number; y: number },
  onSelectAgent: (sessionId: string) => void
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
      status: session.status
    }
  };
}

type MessageEntry = {
  sessionId: string;
  id: string;
  parentId: string | null;
  kind: "text" | "tool_call" | "tool_result";
  title: string;
  detail: string;
  meta?: string;
  resultCount?: number;
  toolCallId?: string;
  toolName?: string;
  isExpanded?: boolean;
};

function createMessageEntries(
  sessionId: string,
  messages: ApiSessionMessageDto[],
  expandedToolCallIds: Set<string>,
) {
  const entries: MessageEntry[] = [];
  const pendingToolCalls: string[] = [];
  const resultCounts = new Map<string, number>();
  const toolCalls = new Map<string, MessageEntry>();

  messages.forEach((message, messageIndex) => {
    message.parts.forEach((part, partIndex) => {
      const content = stringifyContent(part.content);

      if (part.type === "SystemPromptPart") {
        return;
      }

      if (part.type === "ToolCallPart") {
        const rawToolCallId = extractToolCallId(content) ?? `tool-call:${messageIndex}:${partIndex}`;
        const toolCallId = `tool-call:${sessionId}:${rawToolCallId}`;
        const toolName = extractToolName(content) ?? "Tool call";
        const entry: MessageEntry = {
          sessionId,
          id: toolCallId,
          parentId: null,
          kind: "tool_call",
          title: toolName,
          detail: summarizeToolArgs(content),
          meta: message.kind === "response" ? "Assistant tool call" : "Tool call",
          resultCount: 0,
          toolCallId,
          toolName,
          isExpanded: expandedToolCallIds.has(toolCallId)
        };
        entries.push(entry);
        pendingToolCalls.push(toolCallId);
        resultCounts.set(toolCallId, 0);
        toolCalls.set(toolCallId, entry);
        return;
      }

      if (part.type === "ToolReturnPart") {
        const parentToolCallId = pendingToolCalls.shift() ?? null;
        const nextCount = parentToolCallId ? (resultCounts.get(parentToolCallId) ?? 0) + 1 : 1;
        if (parentToolCallId) {
          resultCounts.set(parentToolCallId, nextCount);
          const parentCall = toolCalls.get(parentToolCallId);
          if (parentCall) {
            parentCall.resultCount = nextCount;
          }
        }

        if (!parentToolCallId || !expandedToolCallIds.has(parentToolCallId)) {
          return;
        }

        entries.push({
          sessionId,
          id: `${parentToolCallId}:result:${nextCount}`,
          parentId: parentToolCallId,
          kind: "tool_result",
          title: "Tool result",
          detail: content || "No tool output returned.",
          meta: "Click the tool call again to collapse"
        });
        return;
      }

      entries.push({
        sessionId,
        id: `message:${sessionId}:${messageIndex}:${partIndex}`,
        parentId: null,
        kind: "text",
        title: describeTextPart(message.kind, part.type),
        detail: content,
        meta: part.type
      });
    });
  });

  return entries.map((entry) =>
    entry.kind === "tool_call"
      ? { ...entry, resultCount: resultCounts.get(entry.toolCallId ?? "") ?? 0, isExpanded: entry.toolCallId ? expandedToolCallIds.has(entry.toolCallId) : false }
      : entry
  );
}

function createMessageNode(
  entry: MessageEntry,
  position: { x: number; y: number },
  onToggleToolCall: (toolCallId: string) => void
): Node<SessionCanvasNodeData> {
  return {
    id: entry.id,
    type: "sessionCanvasNode",
    position,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      sessionId: entry.sessionId,
      kind: entry.kind,
      title: entry.title,
      detail: entry.detail,
      meta: entry.meta,
      onToggleToolCall,
      resultCount: entry.resultCount,
      toolCallId: entry.toolCallId,
      toolName: entry.toolName,
      isExpanded: entry.isExpanded
    }
  };
}

function describeTextPart(kind: string, partType: string) {
  if (partType === "UserPromptPart") {
    return kind === "request" ? "User prompt" : "Prompt";
  }

  if (partType === "TextPart") {
    return kind === "response" ? "Assistant text" : "Text";
  }

  return partType;
}


function stringifyContent(content: unknown) {
  if (typeof content === "string") {
    return content;
  }

  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
  }
}

function extractToolCallId(content: string) {
  return content.match(/tool_call_id='([^']+)'/)?.[1] ?? null;
}

function extractToolName(content: string) {
  return content.match(/tool_name='([^']+)'/)?.[1] ?? null;
}

function summarizeToolArgs(content: string) {
  const args = content.match(/args=(\{[\s\S]*\}), tool_call_id=/)?.[1];
  if (!args) {
    return content;
  }

  return args.length > 220 ? `${args.slice(0, 217)}...` : args;
}
