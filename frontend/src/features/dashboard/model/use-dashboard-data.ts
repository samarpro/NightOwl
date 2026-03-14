import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchDashboardSnapshot, subscribeMockEvents } from "shared/api/mock-gateway";
import { toDashboardState, applyGatewayEvent } from "entities/dashboard/model/adapters";
import type { DashboardState } from "entities/dashboard/model/types";
import { translateGatewayEvent } from "shared/websocket/translate-event";

const dashboardQueryKey = ["dashboard"];

export function useDashboardData() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: dashboardQueryKey,
    queryFn: async () => toDashboardState(await fetchDashboardSnapshot())
  });

  useEffect(() => {
    const unsubscribe = subscribeMockEvents((rawEvent) => {
      const event = translateGatewayEvent(rawEvent);
      queryClient.setQueryData<DashboardState>(dashboardQueryKey, (current) => {
        if (!current) {
          return current;
        }

        return applyGatewayEvent(current, event);
      });
    });

    return unsubscribe;
  }, [queryClient]);

  return query;
}
