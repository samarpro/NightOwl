import { describe, expect, it } from "vitest";
import { buildSessionTree } from "entities/session/model/selectors";

describe("buildSessionTree", () => {
  it("nests children under their parent", () => {
    const tree = buildSessionTree([
      {
        id: "root",
        parentId: null,
        label: "Root",
        role: "main",
        status: "running",
        taskSummary: "Root task",
        currentIntent: "Coordinate",
        channel: "web",
        startedAt: "2026-03-14T17:00:00Z",
        waitReason: null
      },
      {
        id: "child",
        parentId: "root",
        label: "Child",
        role: "leaf",
        status: "completed",
        taskSummary: "Child task",
        currentIntent: "Return result",
        channel: "internal",
        startedAt: "2026-03-14T17:01:00Z",
        waitReason: null
      }
    ]);

    expect(tree).toHaveLength(1);
    expect(tree[0]?.children[0]?.id).toBe("child");
  });
});
