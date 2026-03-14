import { describe, expect, it } from "vitest";
import { buildChannels } from "entities/channel/model/selectors";

describe("buildChannels", () => {
  it("marks known channels as active when sessions are routed through them", () => {
    const channels = buildChannels([
      {
        id: "sess-main",
        parentId: null,
        label: "Main",
        role: "main",
        status: "running",
        taskSummary: "Coordinate",
        currentIntent: "Route approval",
        channel: "whatsapp",
        startedAt: "2026-03-14T17:15:00Z",
        waitReason: null
      }
    ]);

    expect(channels.find((channel) => channel.id === "whatsapp")?.traffic).toBe("active");
    expect(channels.find((channel) => channel.id === "telegram")?.configured).toBe(false);
  });
});
