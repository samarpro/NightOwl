import { describe, expect, it } from "vitest";
import { toSessionNode } from "entities/session/model/adapters";

describe("toSessionNode", () => {
  it("maps backend session payloads into dashboard session nodes", () => {
    const session = toSessionNode({
      id: "sess-1",
      parentId: null,
      role: "subagent",
      state: "pending",
      depth: 0,
      task: "Review the dashboard payload",
      label: "Payload Review",
      sandboxMode: null,
      channelRoute: "whatsapp:+15555550123",
      createdAt: "2026-03-15T01:00:00Z",
      completedAt: null,
      result: null
    });

    expect(session).toEqual({
      id: "sess-1",
      parentId: null,
      role: "leaf",
      status: "waiting",
      label: "Payload Review",
      taskSummary: "Review the dashboard payload",
      currentIntent: "Queued and waiting to start.",
      channel: "whatsapp:+15555550123",
      startedAt: "2026-03-15T01:00:00Z",
      waitReason: "pending"
    });
  });

  it("fills a fallback label when the backend returns null", () => {
    const session = toSessionNode({
      id: "sess-2",
      parentId: null,
      role: "main",
      state: "running",
      depth: 0,
      task: "",
      label: null,
      sandboxMode: null,
      channelRoute: null,
      createdAt: "2026-03-15T01:00:00Z",
      completedAt: null,
      result: null
    });

    expect(session.label).toBe("Untitled session");
    expect(session.taskSummary).toBe("Untitled session");
  });
});
