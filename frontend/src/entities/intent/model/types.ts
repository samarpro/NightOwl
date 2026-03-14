import type { SessionStatus } from "entities/session/model/types";

export type IntentRelationship = "root" | "depends_on" | "informs" | "triggers";
export type RiskLevel = "low" | "medium" | "high";

export type IntentNode = {
  id: string;
  sessionId: string;
  title: string;
  service: string;
  status: SessionStatus;
  relationship: IntentRelationship;
  riskLevel: RiskLevel;
  elapsedMs: number;
  tokenRange: {
    start: number;
    end: number;
  };
};
