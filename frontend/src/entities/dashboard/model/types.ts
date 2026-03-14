import type { Approval } from "entities/approval/model/types";
import type { IntentNode } from "entities/intent/model/types";
import type { SessionNode } from "entities/session/model/types";
import type { TokenEntry } from "entities/token/model/types";

export type TimelineEvent = {
  id: string;
  title: string;
  detail: string;
  happenedAt: string;
};

export type DashboardState = {
  tasksActive: number;
  pendingApprovals: number;
  liveChannels: number;
  sessions: SessionNode[];
  intents: IntentNode[];
  approvals: Approval[];
  tokens: TokenEntry[];
  events: TimelineEvent[];
};
