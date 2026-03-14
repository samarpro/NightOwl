import type { RiskLevel } from "entities/intent/model/types";

export type Approval = {
  id: string;
  sessionId: string;
  title: string;
  toolName: string;
  justification: string;
  riskLevel: RiskLevel;
  expiresAt: string;
  status: "pending" | "approved" | "rejected";
};
