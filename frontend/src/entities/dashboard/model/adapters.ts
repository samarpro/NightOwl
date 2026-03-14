import type { DashboardSnapshot, GatewayEventDto } from "shared/api/contracts";
import type { DashboardState } from "entities/dashboard/model/types";

export function toDashboardState(snapshot: DashboardSnapshot): DashboardState {
  return {
    tasksActive: snapshot.tasksActive,
    pendingApprovals: snapshot.pendingApprovals,
    liveChannels: snapshot.liveChannels,
    sessions: snapshot.sessions,
    intents: snapshot.intents,
    approvals: snapshot.approvals,
    tokens: snapshot.tokens,
    events: snapshot.events
  };
}

export function applyGatewayEvent(state: DashboardState, event: GatewayEventDto): DashboardState {
  switch (event.eventType) {
    case "session.updated": {
      const payload = event.payload;
      if (isApiSessionPayload(payload)) {
        return state;
      }

      return {
        ...state,
        sessions: state.sessions.map((session) =>
          session.id === payload.sessionId
            ? {
                ...session,
                status: payload.status,
                currentIntent: payload.currentIntent,
                waitReason: payload.waitReason
              }
            : session,
        )
      };
    }
    case "approval.requested":
      return {
        ...state,
        pendingApprovals: state.pendingApprovals + 1,
        approvals: [event.payload, ...state.approvals]
      };
    case "intent.updated":
      return {
        ...state,
        intents: state.intents.map((intent) => (intent.id === event.payload.id ? event.payload : intent))
      };
    default:
      return state;
  }
}

function isApiSessionPayload(
  payload: Extract<GatewayEventDto, { eventType: "session.updated" }>["payload"]
): payload is Extract<GatewayEventDto, { eventType: "session.updated" }>["payload"] & { id: string } {
  return "id" in payload;
}
