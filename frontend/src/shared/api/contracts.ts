import { z } from "zod";

export const sessionStatusSchema = z.enum(["running", "waiting", "blocked", "completed"]);
export const apiSessionStateSchema = z.enum([
  "pending",
  "running",
  "waiting",
  "blocked",
  "completed",
  "failed",
  "cancelled"
]);
export const riskLevelSchema = z.enum(["low", "medium", "high"]);
export const tokenTypeSchema = z.enum(["thinking", "tool_call", "tool_result", "response"]);
export const channelMessageSchema = z.object({
  channel: z.string().min(1),
  sender_id: z.string().min(1),
  text: z.string().min(1),
  thread_id: z.string().nullable().optional()
});
export const ingestMessageResponseSchema = z.object({
  sessionId: z.string(),
  created: z.boolean()
});

export const sessionNodeSchema = z.object({
  id: z.string(),
  parentId: z.string().nullable(),
  label: z.string(),
  role: z.enum(["main", "orchestrator", "leaf"]),
  status: sessionStatusSchema,
  taskSummary: z.string(),
  currentIntent: z.string(),
  channel: z.string(),
  startedAt: z.string(),
  waitReason: z.string().nullable()
});

export const apiSessionSchema = z.object({
  id: z.string(),
  parentId: z.string().nullable(),
  role: z.string(),
  state: apiSessionStateSchema,
  depth: z.number().int().nonnegative(),
  task: z.string(),
  label: z.string().nullable(),
  sandboxMode: z.string().nullable(),
  channelRoute: z.string().nullable(),
  createdAt: z.string().nullable(),
  completedAt: z.string().nullable(),
  result: z.string().nullable()
});

export const intentNodeSchema = z.object({
  id: z.string(),
  sessionId: z.string(),
  title: z.string(),
  service: z.string(),
  status: sessionStatusSchema,
  relationship: z.enum(["root", "depends_on", "informs", "triggers"]),
  riskLevel: riskLevelSchema,
  elapsedMs: z.number().int().nonnegative(),
  tokenRange: z.object({
    start: z.number().int().nonnegative(),
    end: z.number().int().nonnegative()
  })
});

export const approvalSchema = z.object({
  id: z.string(),
  sessionId: z.string(),
  title: z.string(),
  toolName: z.string(),
  justification: z.string(),
  riskLevel: riskLevelSchema,
  expiresAt: z.string(),
  status: z.enum(["pending", "approved", "rejected"])
});

export const tokenEntrySchema = z.object({
  id: z.string(),
  sessionId: z.string(),
  intentId: z.string(),
  type: tokenTypeSchema,
  createdAt: z.string(),
  content: z.string()
});

export const eventSchema = z.discriminatedUnion("eventType", [
  z.object({
    eventId: z.string(),
    eventType: z.literal("session.updated"),
    occurredAt: z.string(),
    payload: z.object({
      sessionId: z.string(),
      status: sessionStatusSchema,
      currentIntent: z.string(),
      waitReason: z.string().nullable()
    })
  }),
  z.object({
    eventId: z.string(),
    eventType: z.literal("approval.requested"),
    occurredAt: z.string(),
    payload: approvalSchema
  }),
  z.object({
    eventId: z.string(),
    eventType: z.literal("intent.updated"),
    occurredAt: z.string(),
    payload: intentNodeSchema
  })
]);

export const dashboardSnapshotSchema = z.object({
  tasksActive: z.number().int().nonnegative(),
  pendingApprovals: z.number().int().nonnegative(),
  liveChannels: z.number().int().nonnegative(),
  sessions: z.array(sessionNodeSchema),
  intents: z.array(intentNodeSchema),
  approvals: z.array(approvalSchema),
  tokens: z.array(tokenEntrySchema),
  events: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      detail: z.string(),
      happenedAt: z.string()
    }),
  )
});

export type DashboardSnapshot = z.infer<typeof dashboardSnapshotSchema>;
export type ChannelMessageDto = z.infer<typeof channelMessageSchema>;
export type IngestMessageResponseDto = z.infer<typeof ingestMessageResponseSchema>;
export type SessionNodeDto = z.infer<typeof sessionNodeSchema>;
export type ApiSessionDto = z.infer<typeof apiSessionSchema>;
export type IntentNodeDto = z.infer<typeof intentNodeSchema>;
export type ApprovalDto = z.infer<typeof approvalSchema>;
export type TokenEntryDto = z.infer<typeof tokenEntrySchema>;
export type GatewayEventDto = z.infer<typeof eventSchema>;
