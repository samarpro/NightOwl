const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

type DashboardSubscribeMessage = {
  type: "dashboard.subscribe";
  sessionId: string | null;
};

export function buildGatewayWebSocketUrl() {
  if (!apiBaseUrl?.trim()) {
    throw new Error("VITE_API_BASE_URL is not configured.");
  }

  const url = new URL(apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws";
  url.search = "";
  url.hash = "";
  return url.toString();
}

export function buildDashboardSubscribeMessage(sessionId: string | null): DashboardSubscribeMessage {
  return {
    type: "dashboard.subscribe",
    sessionId
  };
}
