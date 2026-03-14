import type { ChannelItem } from "entities/channel/model/types";
import type { SessionNode } from "entities/session/model/types";

const channelCatalog: Record<
  string,
  Omit<ChannelItem, "linkedRoutes" | "lastInbound" | "lastOutbound" | "traffic">
> = {
  whatsapp: {
    id: "whatsapp",
    name: "WhatsApp",
    kind: "messaging",
    icon: "wa",
    configured: true,
    connected: true,
    health: "active",
    authState: "paired operator device",
    typing: true,
    pairing: "trusted device paired",
    allowlist: "friends allowlist applied",
    detail: "Primary user-facing channel for approvals and delivery."
  },
  telegram: {
    id: "telegram",
    name: "Telegram",
    kind: "messaging",
    icon: "tg",
    configured: false,
    connected: false,
    health: "disabled",
    authState: "not configured",
    typing: true,
    pairing: "not required",
    allowlist: "not configured",
    detail: "Ready for setup once a bot token and route are configured."
  },
  web_ui: {
    id: "web-ui",
    name: "Web UI",
    kind: "web",
    icon: "ui",
    configured: true,
    connected: true,
    health: "healthy",
    authState: "operator signed in",
    typing: false,
    pairing: "browser trust active",
    allowlist: "workspace operator access",
    detail: "Internal dashboard channel for direct control and observability."
  },
  internal: {
    id: "internal",
    name: "Internal Bus",
    kind: "internal",
    icon: "in",
    configured: true,
    connected: true,
    health: "healthy",
    authState: "service scoped",
    typing: false,
    pairing: "service-to-service",
    allowlist: "system scoped",
    detail: "Sub-agent and orchestrator session handoff path."
  },
  slack: {
    id: "slack",
    name: "Slack",
    kind: "messaging",
    icon: "sl",
    configured: false,
    connected: false,
    health: "disabled",
    authState: "not configured",
    typing: true,
    pairing: "oauth pending",
    allowlist: "workspace policies unavailable",
    detail: "Supported but not configured in this workspace."
  },
  discord: {
    id: "discord",
    name: "Discord",
    kind: "messaging",
    icon: "dc",
    configured: false,
    connected: false,
    health: "disabled",
    authState: "not configured",
    typing: true,
    pairing: "token pending",
    allowlist: "channel policy unavailable",
    detail: "Supported connector available for future expansion."
  }
};

export function buildChannels(sessions: SessionNode[]): ChannelItem[] {
  const routesByChannel = new Map<string, Set<string>>();
  const latestInboundByChannel = new Map<string, string>();

  for (const session of sessions) {
    const channelKey = normalizeChannelKey(session.channel);
    const routes = routesByChannel.get(channelKey) ?? new Set<string>();
    routes.add(`${session.label} -> ${session.currentIntent}`);
    routesByChannel.set(channelKey, routes);

    const currentLatest = latestInboundByChannel.get(channelKey);
    if (!currentLatest || currentLatest < session.startedAt) {
      latestInboundByChannel.set(channelKey, session.startedAt);
    }
  }

  return Object.entries(channelCatalog).map(([key, base]) => {
    const linkedRoutes = [...(routesByChannel.get(key) ?? [])];
    const lastInbound = latestInboundByChannel.get(key) ?? null;
    const lastOutbound = lastInbound;
    const traffic = linkedRoutes.length > 0 ? "active" : "idle";

    return {
      ...base,
      linkedRoutes,
      lastInbound,
      lastOutbound,
      traffic,
      health: traffic === "active" && base.health === "healthy" ? "active" : base.health
    };
  });
}

function normalizeChannelKey(channel: string) {
  return channel === "web" ? "web_ui" : channel.replace(/[\s-]+/g, "_");
}
