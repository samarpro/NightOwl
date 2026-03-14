import { describe, expect, it } from "vitest";
import { translateGatewayEvent } from "shared/websocket/translate-event";

describe("translateGatewayEvent", () => {
  it("accepts websocket snapshots", () => {
    const event = translateGatewayEvent({
      eventId: "evt-0",
      eventType: "dashboard.snapshot",
      occurredAt: "2026-03-15T01:00:00Z",
      payload: {
        selectedSessionId: null,
        rootSessions: [],
        childSessions: []
      }
    });

    expect(event?.eventType).toBe("dashboard.snapshot");
  });

  it("accepts a valid approval event", () => {
    const event = translateGatewayEvent({
      eventId: "evt-1",
      eventType: "approval.requested",
      occurredAt: "2026-03-14T17:18:22Z",
      payload: {
        id: "approval-1",
        sessionId: "sess-1",
        title: "Approve booking",
        toolName: "composio_execute",
        justification: "Booking step writes to an external service.",
        riskLevel: "high",
        expiresAt: "2026-03-14T17:22:22Z",
        status: "pending"
      }
    });

    expect(event?.eventType).toBe("approval.requested");
  });

  it("drops malformed events", () => {
    const event = translateGatewayEvent({
      eventId: "evt-2",
      eventType: "session.updated",
      occurredAt: "2026-03-14T17:18:22Z",
      payload: {
        sessionId: "sess-1",
        status: "unknown"
      }
    });

    expect(event).toBeNull();
  });
});
