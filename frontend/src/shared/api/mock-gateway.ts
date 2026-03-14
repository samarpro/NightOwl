import {
  dashboardSnapshotSchema,
  type DashboardSnapshot,
  type GatewayEventDto
} from "shared/api/contracts";

const snapshot: DashboardSnapshot = dashboardSnapshotSchema.parse({
  tasksActive: 3,
  pendingApprovals: 1,
  liveChannels: 2,
  sessions: [
    {
      id: "sess-main",
      parentId: null,
      label: "Main Session",
      role: "main",
      status: "running",
      taskSummary: "Plan a night out and secure a reservation approval.",
      currentIntent: "Coordinate child agents and review reservation step.",
      channel: "whatsapp",
      startedAt: "2026-03-14T17:15:00Z",
      waitReason: null
    },
    {
      id: "sess-calendar",
      parentId: "sess-main",
      label: "Calendar Check",
      role: "orchestrator",
      status: "completed",
      taskSummary: "Confirm free window for Saturday night.",
      currentIntent: "Report free time back to parent.",
      channel: "internal",
      startedAt: "2026-03-14T17:16:00Z",
      waitReason: null
    },
    {
      id: "sess-restaurants",
      parentId: "sess-main",
      label: "Restaurant Search",
      role: "orchestrator",
      status: "waiting",
      taskSummary: "Compare nearby options and ask for approval before booking.",
      currentIntent: "Prepare shortlist and request HITL approval.",
      channel: "internal",
      startedAt: "2026-03-14T17:16:08Z",
      waitReason: "approval_pending"
    }
  ],
  intents: [
    {
      id: "intent-root",
      sessionId: "sess-main",
      title: "Night Out Coordination",
      service: "Planner",
      status: "running",
      relationship: "root",
      riskLevel: "medium",
      elapsedMs: 322000,
      tokenRange: { start: 0, end: 5 }
    },
    {
      id: "intent-calendar",
      sessionId: "sess-calendar",
      title: "Availability Verification",
      service: "Calendar",
      status: "completed",
      relationship: "depends_on",
      riskLevel: "low",
      elapsedMs: 68000,
      tokenRange: { start: 6, end: 8 }
    },
    {
      id: "intent-restaurant",
      sessionId: "sess-restaurants",
      title: "Reservation Candidate Ranking",
      service: "OpenTable",
      status: "waiting",
      relationship: "triggers",
      riskLevel: "high",
      elapsedMs: 141000,
      tokenRange: { start: 9, end: 13 }
    }
  ],
  approvals: [
    {
      id: "approval-booking",
      sessionId: "sess-restaurants",
      title: "Approve reservation hold at Marion Wine Bar",
      toolName: "composio_execute",
      justification: "The agent found a matched time slot and is about to place a real booking hold.",
      riskLevel: "high",
      expiresAt: "2026-03-14T17:50:00Z",
      status: "pending"
    }
  ],
  tokens: [
    {
      id: "token-1",
      sessionId: "sess-main",
      intentId: "intent-root",
      type: "thinking",
      createdAt: "2026-03-14T17:15:03Z",
      content: "Need to split the work into availability checking and venue selection."
    },
    {
      id: "token-2",
      sessionId: "sess-main",
      intentId: "intent-root",
      type: "tool_call",
      createdAt: "2026-03-14T17:15:05Z",
      content: "{\"tool\":\"sessions_spawn\",\"task\":\"Check my calendar for Saturday 7pm\"}"
    },
    {
      id: "token-3",
      sessionId: "sess-calendar",
      intentId: "intent-calendar",
      type: "response",
      createdAt: "2026-03-14T17:16:31Z",
      content: "Calendar is clear from 6pm onward. Returning result to parent."
    },
    {
      id: "token-4",
      sessionId: "sess-restaurants",
      intentId: "intent-restaurant",
      type: "tool_result",
      createdAt: "2026-03-14T17:18:12Z",
      content: "{\"candidate\":\"Marion Wine Bar\",\"time\":\"7:30pm\",\"needsApproval\":true}"
    },
    {
      id: "token-5",
      sessionId: "sess-restaurants",
      intentId: "intent-restaurant",
      type: "response",
      createdAt: "2026-03-14T17:18:21Z",
      content: "Shortlist prepared. Waiting on human approval before final booking."
    }
  ],
  events: [
    {
      id: "evt-1",
      title: "Child session completed",
      detail: "Calendar Check returned a free window for Saturday evening.",
      happenedAt: "2026-03-14T17:16:31Z"
    },
    {
      id: "evt-2",
      title: "Approval required",
      detail: "Reservation hold requires operator approval before channel delivery.",
      happenedAt: "2026-03-14T17:18:22Z"
    }
  ]
});

const eventStream: GatewayEventDto[] = [
  {
    eventId: "ws-1",
    eventType: "session.updated",
    occurredAt: "2026-03-14T17:19:10Z",
    payload: {
      sessionId: "sess-restaurants",
      status: "waiting",
      currentIntent: "Hold candidate restaurant while approval is pending.",
      waitReason: "approval_pending"
    }
  },
  {
    eventId: "ws-2",
    eventType: "intent.updated",
    occurredAt: "2026-03-14T17:19:20Z",
    payload: {
      id: "intent-restaurant",
      sessionId: "sess-restaurants",
      title: "Reservation Candidate Ranking",
      service: "OpenTable",
      status: "waiting",
      relationship: "triggers",
      riskLevel: "high",
      elapsedMs: 175000,
      tokenRange: { start: 9, end: 14 }
    }
  }
];

export async function fetchDashboardSnapshot() {
  return snapshot;
}

export function subscribeMockEvents(onEvent: (event: GatewayEventDto) => void) {
  const timers = eventStream.map((event, index) =>
    window.setTimeout(() => {
      onEvent(event);
    }, 1200 * (index + 1)),
  );

  return () => {
    timers.forEach((timer) => window.clearTimeout(timer));
  };
}
