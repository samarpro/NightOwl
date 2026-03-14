import { describe, expect, it } from "vitest";
import { buildSessionGraph } from "features/session-canvas/model/build-session-graph";

describe("buildSessionGraph", () => {
  it("creates agent, thinking, and tool nodes for the selected session subtree", () => {
    const graph = buildSessionGraph(
      "sess-main",
      [
        {
          id: "sess-main",
          parentId: null,
          label: "Main Session",
          role: "main",
          status: "running",
          taskSummary: "Coordinate a plan",
          currentIntent: "Delegate work",
          channel: "web",
          startedAt: "2026-03-14T17:00:00Z",
          waitReason: null
        },
        {
          id: "sess-child",
          parentId: "sess-main",
          label: "Child Session",
          role: "leaf",
          status: "waiting",
          taskSummary: "Call an external tool",
          currentIntent: "Await booking hold",
          channel: "internal",
          startedAt: "2026-03-14T17:01:00Z",
          waitReason: "approval_pending"
        }
      ],
      [
        {
          id: "intent-main",
          sessionId: "sess-main",
          title: "Plan route",
          service: "Planner",
          status: "running",
          relationship: "root",
          riskLevel: "medium",
          elapsedMs: 1200,
          tokenRange: { start: 0, end: 3 }
        }
      ],
      [
        {
          id: "token-tool",
          sessionId: "sess-main",
          intentId: "intent-main",
          type: "tool_call",
          createdAt: "2026-03-14T17:00:02Z",
          content: "{\"tool\":\"sessions_spawn\"}"
        }
      ],
      new Set(["sess-main"]),
    );

    expect(graph.nodes.some((node) => node.data.kind === "agent")).toBe(true);
    expect(graph.nodes.some((node) => node.data.kind === "thinking")).toBe(true);
    expect(graph.nodes.some((node) => node.data.kind === "tool")).toBe(true);
    expect(graph.edges.some((edge) => edge.source === "agent:sess-main" && edge.target === "agent:sess-child")).toBe(
      true,
    );
  });
});
