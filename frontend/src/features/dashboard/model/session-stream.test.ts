import { describe, expect, it } from "vitest";
import {
  applyDashboardSessionEvent,
  createDashboardSessionStreamState
} from "features/dashboard/model/session-stream";

describe("createDashboardSessionStreamState", () => {
  it("maps websocket snapshots into dashboard session state", () => {
    const state = createDashboardSessionStreamState({
      selectedSessionId: "session:root",
      rootSessions: [
        {
          id: "session:root",
          parentId: null,
          role: "main",
          state: "running",
          depth: 0,
          task: "Root task",
          label: "Root",
          sandboxMode: null,
          channelRoute: "whatsapp",
          createdAt: "2026-03-15T00:00:00Z",
          completedAt: null,
          result: null
        }
      ],
      childSessions: []
    });

    expect(state.hasSnapshot).toBe(true);
    expect(state.rootSessions[0]?.id).toBe("session:root");
  });
});

describe("applyDashboardSessionEvent", () => {
  it("adds child sessions created for the selected root", () => {
    const state = createDashboardSessionStreamState({
      selectedSessionId: "session:root",
      rootSessions: [],
      childSessions: []
    });

    const next = applyDashboardSessionEvent(
      state,
      {
        eventId: "evt-1",
        eventType: "session.created",
        occurredAt: "2026-03-15T00:00:00Z",
        payload: {
          id: "session:child",
          parentId: "session:root",
          role: "leaf",
          state: "pending",
          depth: 1,
          task: "Child task",
          label: "Child",
          sandboxMode: null,
          channelRoute: null,
          createdAt: "2026-03-15T00:01:00Z",
          completedAt: null,
          result: null
        }
      },
      "session:root"
    );

    expect(next.childSessions).toHaveLength(1);
    expect(next.childSessions[0]?.id).toBe("session:child");
  });

  it("patches existing sessions from lightweight updates", () => {
    const state = createDashboardSessionStreamState({
      selectedSessionId: "session:root",
      rootSessions: [
        {
          id: "session:root",
          parentId: null,
          role: "main",
          state: "running",
          depth: 0,
          task: "Root task",
          label: "Root",
          sandboxMode: null,
          channelRoute: "whatsapp",
          createdAt: "2026-03-15T00:00:00Z",
          completedAt: null,
          result: null
        }
      ],
      childSessions: []
    });

    const next = applyDashboardSessionEvent(
      state,
      {
        eventId: "evt-2",
        eventType: "session.updated",
        occurredAt: "2026-03-15T00:02:00Z",
        payload: {
          sessionId: "session:root",
          status: "waiting",
          currentIntent: "Waiting for approval.",
          waitReason: "approval_pending"
        }
      },
      "session:root"
    );

    expect(next.rootSessions[0]?.status).toBe("waiting");
    expect(next.rootSessions[0]?.currentIntent).toBe("Waiting for approval.");
  });
});
