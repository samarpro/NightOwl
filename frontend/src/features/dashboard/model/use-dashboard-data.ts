import { useQuery } from "@tanstack/react-query";
import { fetchChildSessions, fetchRootSessions } from "shared/api/sessions";

const rootSessionsQueryKey = ["sessions", "roots"] as const;

export function useDashboardData(selectedSessionId: string | null) {
  const rootSessionsQuery = useQuery({
    queryKey: rootSessionsQueryKey,
    queryFn: fetchRootSessions
  });

  const childSessionsQuery = useQuery({
    queryKey: [...rootSessionsQueryKey, selectedSessionId, "children"],
    queryFn: () => fetchChildSessions(selectedSessionId as string),
    enabled: selectedSessionId !== null
  });

  const rootSessions = rootSessionsQuery.data ?? [];
  const childSessions = childSessionsQuery.data ?? [];
  const activeStatuses = new Set(["running", "waiting", "blocked"]);
  const activeRootCount = rootSessions.filter((session) => activeStatuses.has(session.status)).length;
  const routedChannels = new Set(rootSessions.map((session) => session.channel).filter(Boolean));
  const pendingRoots = rootSessions.filter((session) => session.waitReason !== null).length;

  return {
    rootSessions,
    childSessions,
    tasksActive: activeRootCount,
    pendingApprovals: pendingRoots,
    liveChannels: routedChannels.size,
    isLoading: rootSessionsQuery.isLoading || childSessionsQuery.isLoading,
    isFetching: rootSessionsQuery.isFetching || childSessionsQuery.isFetching,
    rootSessionsError: rootSessionsQuery.error,
    childSessionsError: childSessionsQuery.error
  };
}
