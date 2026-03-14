import { useQuery } from "@tanstack/react-query";
import { fetchIntentGraph } from "shared/api/observability";

export function useIntentGraph(sessionId: string) {
  return useQuery({
    queryKey: ["intent-graph", sessionId],
    queryFn: () => fetchIntentGraph(sessionId),
    enabled: !!sessionId,
    refetchInterval: 3000,
  });
}
