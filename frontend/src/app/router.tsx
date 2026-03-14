import { createRootRoute, createRoute, createRouter, Outlet } from "@tanstack/react-router";
import { DashboardPage } from "pages/dashboard";

function AppShell() {
  return <Outlet />;
}

const rootRoute = createRootRoute({
  component: AppShell
});

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage
});

const routeTree = rootRoute.addChildren([dashboardRoute]);

export const router = createRouter({
  routeTree
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
