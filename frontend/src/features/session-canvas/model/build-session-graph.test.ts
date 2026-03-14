import { describe, expect, it } from "vitest";
import { buildSessionGraph } from "features/session-canvas/model/build-session-graph";

describe("buildSessionGraph", () => {
  it("creates one node per session for the selected root and its direct children", () => {
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
      ],
      {
        "sess-main": [
          {
            kind: "response",
            parts: [
              { type: "TextPart", content: "Hello from the agent" },
              {
                type: "ToolCallPart",
                content:
                  "ToolCallPart(tool_name='sessions_spawn', args={'task': 'Hello'}, tool_call_id='tooluse_123')"
              }
            ]
          },
          {
            kind: "request",
            parts: [{ type: "ToolReturnPart", content: "Spawned child session session:child" }]
          }
        ],
        "sess-child-a": [
          {
            kind: "request",
            parts: [{ type: "UserPromptPart", content: "Child prompt" }]
          }
        ]
      },
      new Set(["tool-call:sess-main:tooluse_123"]),
      () => {},
      () => {}
    );

    expect(graph.nodes).toHaveLength(7);
    expect(graph.nodes.some((node) => node.data.kind === "text")).toBe(true);
    expect(graph.nodes.some((node) => node.data.kind === "tool_call")).toBe(true);
    expect(graph.nodes.some((node) => node.data.kind === "tool_result")).toBe(true);
    expect(graph.edges).toHaveLength(6);
    expect(graph.edges.some((edge) => edge.source === "agent:sess-main" && edge.target === "agent:sess-child-a")).toBe(
      true,
    );
    expect(
      graph.edges.some(
        (edge) =>
          edge.source === "tool-call:sess-main:tooluse_123" &&
          edge.target === "tool-call:sess-main:tooluse_123:result:1"
      )
    ).toBe(true);
    const childNode = graph.nodes.find((node) => node.id === "agent:sess-child-a");
    const childPromptNode = graph.nodes.find((node) => node.id === "message:sess-child-a:0:0");
    const rootNode = graph.nodes.find((node) => node.id === "agent:sess-main");
    expect(childNode?.position.x).toBe(childPromptNode?.position.x);
    expect(childPromptNode?.position.y).toBeGreaterThan((childNode?.position.y ?? 0));
    expect((childNode?.position.x ?? 0) - (rootNode?.position.x ?? 0)).toBe(560);
    expect(graph.nodes.some((node) => node.id === "agent:sess-grandchild")).toBe(false);
  });
});
