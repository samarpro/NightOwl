export type ChannelHealth =
  | "healthy"
  | "active"
  | "idle"
  | "degraded"
  | "reconnecting"
  | "blocked"
  | "faulty"
  | "disabled";

export type ChannelItem = {
  id: string;
  name: string;
  kind: "messaging" | "web" | "internal";
  icon: string;
  configured: boolean;
  connected: boolean;
  traffic: "active" | "idle";
  health: ChannelHealth;
  authState: string;
  linkedRoutes: string[];
  lastInbound: string | null;
  lastOutbound: string | null;
  typing: boolean;
  pairing: string;
  allowlist: string;
  detail: string;
};
