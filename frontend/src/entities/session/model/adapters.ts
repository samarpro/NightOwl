import type { SessionNode, SessionRole, SessionStatus } from "entities/session/model/types";
import type { ApiSessionDto } from "shared/api/contracts";

export function toSessionNode(session: ApiSessionDto): SessionNode {
  const label = session.label?.trim() || "Untitled session";
  const taskSummary = session.task.trim() || label || "No task summary available.";

  return {
    id: session.id,
    parentId: session.parentId,
    label,
    role: toSessionRole(session.role),
    status: toSessionStatus(session.state),
    taskSummary,
    currentIntent: summarizeCurrentIntent(session),
    channel: session.channelRoute ?? "unrouted",
    startedAt: session.createdAt ?? new Date(0).toISOString(),
    waitReason: toWaitReason(session.state, session.result)
  };
}

function toSessionRole(role: string): SessionRole {
  if (role === "main" || role === "orchestrator" || role === "leaf") {
    return role;
  }

  return role === "subagent" ? "leaf" : "orchestrator";
}

function toSessionStatus(state: ApiSessionDto["state"]): SessionStatus {
  switch (state) {
    case "pending":
      return "waiting";
    case "failed":
    case "cancelled":
      return "blocked";
    default:
      return state;
  }
}

function summarizeCurrentIntent(session: ApiSessionDto) {
  if (session.result?.trim()) {
    return session.result.trim();
  }

  switch (session.state) {
    case "pending":
      return "Queued and waiting to start.";
    case "running":
      return "Currently executing.";
    case "waiting":
      return "Waiting for an external dependency.";
    case "blocked":
      return "Blocked and needs intervention.";
    case "failed":
      return "Execution failed.";
    case "cancelled":
      return "Execution was cancelled.";
    case "completed":
      return "Completed.";
  }
}

function toWaitReason(state: ApiSessionDto["state"], result: string | null) {
  if (state === "waiting" || state === "pending") {
    return result?.trim() || state;
  }

  return null;
}
