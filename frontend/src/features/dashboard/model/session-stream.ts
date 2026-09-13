import { toSessionNode } from "entities/session/model/adapters";
import type { SessionNode } from "entities/session/model/types";
import type { DashboardSessionSnapshotDto, GatewayEventDto } from "shared/api/contracts";

export type DashboardSessionStreamState = {
  childSessions: SessionNode[];
  descendants: SessionNode[];
  hasSnapshot: boolean;
  rootSessions: SessionNode[];
};

export const initialDashboardSessionStreamState: DashboardSessionStreamState = {
  childSessions: [],
  descendants: [],
  hasSnapshot: false,
  rootSessions: []
};

export function createDashboardSessionStreamStateFromSessions(
  rootSessions: SessionNode[],
  childSessions: SessionNode[],
  descendants: SessionNode[] = [],
): DashboardSessionStreamState {
  return {
    childSessions,
    descendants,
    hasSnapshot: true,
    rootSessions
  };
}

export function createDashboardSessionStreamState(
  snapshot: DashboardSessionSnapshotDto
): DashboardSessionStreamState {
  return createDashboardSessionStreamStateFromSessions(
    snapshot.rootSessions.map((session) => toSessionNode(session)),
    snapshot.childSessions.map((session) => toSessionNode(session))
  );
}

export function applyDashboardSessionEvent(
  state: DashboardSessionStreamState,
  event: GatewayEventDto,
  selectedSessionId: string | null
): DashboardSessionStreamState {
  switch (event.eventType) {
    case "dashboard.snapshot":
      return createDashboardSessionStreamState(event.payload);
    case "session.created": {
      const session = toSessionNode(event.payload);
      return {
        ...state,
        childSessions:
          session.parentId === selectedSessionId
            ? upsertSession(state.childSessions, session)
            : state.childSessions,
        descendants:
          session.parentId !== null
            ? upsertSession(state.descendants, session)
            : state.descendants,
        rootSessions: session.parentId === null ? upsertSession(state.rootSessions, session) : state.rootSessions
      };
    }
    case "session.updated": {
      if ("id" in event.payload) {
        const session = toSessionNode(event.payload);
        return {
          ...state,
          childSessions:
            session.parentId === selectedSessionId
              ? upsertSession(state.childSessions, session)
              : patchSessionList(state.childSessions, session.id, session),
          descendants:
            session.parentId !== null
              ? upsertSession(state.descendants, session)
              : patchSessionList(state.descendants, session.id, session),
          rootSessions:
            session.parentId === null
              ? upsertSession(state.rootSessions, session)
              : patchSessionList(state.rootSessions, session.id, session)
        };
      }

      return {
        ...state,
        childSessions: patchSessionList(state.childSessions, event.payload.sessionId, event.payload),
        descendants: patchSessionList(state.descendants, event.payload.sessionId, event.payload),
        rootSessions: patchSessionList(state.rootSessions, event.payload.sessionId, event.payload)
      };
    }
    default:
      return state;
  }
}

function upsertSession(sessions: SessionNode[], session: SessionNode) {
  const next = sessions.filter((entry) => entry.id !== session.id);
  next.push(session);
  return next.sort((left, right) => right.startedAt.localeCompare(left.startedAt));
}

function patchSessionList(
  sessions: SessionNode[],
  sessionId: string,
  patch: Partial<SessionNode> | SessionNode
) {
  return sessions.map((session) => (session.id === sessionId ? { ...session, ...patch } : session));
}
