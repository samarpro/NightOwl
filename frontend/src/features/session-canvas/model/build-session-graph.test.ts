import { describe, expect, it } from "vitest";
import { buildSessionGraph } from "features/session-canvas/model/build-session-graph";

describe("buildSessionGraph", () => {
  it("creates one node per session for the selected root and its direct children", () => {
    const graph = buildSessionGraph("sess-main", [
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
        id: "sess-child-a",
        parentId: "sess-main",
        label: "Child A",
        role: "leaf",
        status: "waiting",
        taskSummary: "First child",
        currentIntent: "Waiting on a dependency",
        channel: "internal",
        startedAt: "2026-03-14T17:01:00Z",
        waitReason: "waiting"
      },
      {
        id: "sess-child-b",
        parentId: "sess-main",
        label: "Child B",
        role: "leaf",
        status: "completed",
        taskSummary: "Second child",
        currentIntent: "Completed",
        channel: "internal",
        startedAt: "2026-03-14T17:02:00Z",
        waitReason: null
      },
      {
        id: "sess-grandchild",
        parentId: "sess-child-a",
        label: "Grandchild",
        role: "leaf",
        status: "running",
        taskSummary: "Nested child",
        currentIntent: "Should not be rendered",
        channel: "internal",
        startedAt: "2026-03-14T17:03:00Z",
        waitReason: null
      }
    ]);

    expect(graph.nodes).toHaveLength(3);
    expect(graph.nodes.every((node) => node.data.kind === "agent")).toBe(true);
    expect(graph.edges).toHaveLength(2);
    expect(graph.edges.some((edge) => edge.source === "agent:sess-main" && edge.target === "agent:sess-child-a")).toBe(
      true,
    );
    expect(graph.nodes.some((node) => node.id === "agent:sess-grandchild")).toBe(false);
  });
});
