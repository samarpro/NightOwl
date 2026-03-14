import { createRootRoute, createRoute, createRouter, Outlet, redirect } from "@tanstack/react-router";
import { DashboardPage } from "pages/dashboard";
import { ChannelsPage } from "pages/channels";
import { SettingsPage } from "pages/settings";
import { AppNavbar } from "widgets/app-navbar/ui/app-navbar";

function AppShell() {
  return (
    <div className="app-layout">
      <AppNavbar />
      <main className="app-layout__content">
        <Outlet />
      </main>
    </div>
  );
}

const rootRoute = createRootRoute({
  component: AppShell
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/sessions" });
  }
});

const sessionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/sessions",
  component: DashboardPage
});

const channelsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/channels",
  component: ChannelsPage
});

const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  component: SettingsPage
});

const routeTree = rootRoute.addChildren([indexRoute, sessionsRoute, channelsRoute, settingsRoute]);

export const router = createRouter({
  routeTree
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
