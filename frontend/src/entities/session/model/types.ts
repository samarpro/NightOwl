export type SessionStatus = "running" | "waiting" | "blocked" | "completed";
export type SessionRole = "main" | "orchestrator" | "leaf";

export type SessionNode = {
  id: string;
  parentId: string | null;
  label: string;
  role: SessionRole;
  status: SessionStatus;
  taskSummary: string;
  currentIntent: string;
  channel: string;
  startedAt: string;
  waitReason: string | null;
};

export type SessionTreeNode = SessionNode & {
  children: SessionTreeNode[];
};
