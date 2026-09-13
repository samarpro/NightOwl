import { useQuery } from "@tanstack/react-query";
import { useDashboardSessionStream } from "features/dashboard/model/use-dashboard-session-stream";
import type { SessionNode } from "entities/session/model/types";
import { fetchChildSessions, fetchDescendants, fetchRootSessions } from "shared/api/sessions";

const EMPTY_SESSIONS: SessionNode[] = [];

export function useDashboardData(selectedSessionId: string | null) {
  const rootSessionsQuery = useQuery({
    queryKey: ["sessions", "roots"],
    queryFn: fetchRootSessions
  });

  const childSessionsQuery = useQuery({
    queryKey: ["sessions", "children", selectedSessionId],
    queryFn: () => fetchChildSessions(selectedSessionId as string),
    enabled: selectedSessionId !== null
  });

  const descendantsQuery = useQuery({
    queryKey: ["sessions", "descendants", selectedSessionId],
    queryFn: () => fetchDescendants(selectedSessionId as string),
    enabled: selectedSessionId !== null
  });

  const fetchedRootSessions = rootSessionsQuery.data ?? EMPTY_SESSIONS;
  const fetchedChildSessions = childSessionsQuery.data ?? EMPTY_SESSIONS;
  const fetchedDescendants = descendantsQuery.data ?? EMPTY_SESSIONS;

  const {
    childSessions,
    descendants,
    rootSessions,
    websocketError,
    websocketLabel,
    websocketStatus
  } = useDashboardSessionStream(
    selectedSessionId,
    fetchedRootSessions,
    fetchedChildSessions,
    fetchedDescendants,
  );
  const activeStatuses = new Set(["running", "waiting", "blocked"]);
  const activeRootCount = rootSessions.filter((session) => activeStatuses.has(session.status)).length;
  const routedChannels = new Set(rootSessions.map((session) => session.channel).filter(Boolean));
  const pendingRoots = rootSessions.filter((session) => session.waitReason !== null).length;
  const rootSessionsError = rootSessionsQuery.error ?? websocketError;
  const childSessionsError = childSessionsQuery.error ?? websocketError;

  return {
    rootSessions,
    childSessions,
    descendants,
    tasksActive: activeRootCount,
    pendingApprovals: pendingRoots,
    liveChannels: routedChannels.size,
    isLoading: rootSessionsQuery.isLoading || (selectedSessionId !== null && childSessionsQuery.isLoading),
    isFetching: rootSessionsQuery.isFetching || childSessionsQuery.isFetching,
    rootSessionsError,
    childSessionsError,
    websocketStatus,
    websocketLabel
  };
}
