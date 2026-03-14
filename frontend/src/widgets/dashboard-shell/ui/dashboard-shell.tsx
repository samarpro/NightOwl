import { useEffect } from "react";
import { buildSessionTree } from "entities/session/model/selectors";
import { useSelectionStore } from "features/session-controls/model/selection-store";
import { useDashboardData } from "features/dashboard/model/use-dashboard-data";
import { SessionCanvas } from "features/session-canvas/ui/session-canvas";
import { SessionTree } from "widgets/dashboard-shell/ui/session-tree";

export function DashboardShell() {
  const { selectedSessionId, selectSession } = useSelectionStore();
  const {
    childSessions,
    childSessionsError,
    isLoading,
    liveChannels,
    pendingApprovals,
    rootSessions,
    rootSessionsError,
    tasksActive
  } = useDashboardData(selectedSessionId);

  useEffect(() => {
    if (rootSessions.length === 0) {
      return;
    }

    const selectionStillExists = rootSessions.some((session) => session.id === selectedSessionId);
    if (!selectionStillExists) {
      selectSession(rootSessions[0].id);
    }
  }, [rootSessions, selectSession, selectedSessionId]);

  if (isLoading && rootSessions.length === 0) {
    return <div className="app-shell">Loading dashboard…</div>;
  }

  if (rootSessionsError) {
    return (
      <div className="app-shell">
        <div className="app-frame">
          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>Dashboard Unavailable</h2>
                <p>The sessions API could not be reached.</p>
              </div>
            </div>
            <div className="panel__body">
              <div className="empty-state">
                <strong>Request failed</strong>
                <p>
                  Check that the backend is running and that `VITE_API_BASE_URL` in the frontend env points to it.
                </p>
                <p>Example: `VITE_API_BASE_URL=http://127.0.0.1:8000`.</p>
                <p>{rootSessionsError instanceof Error ? rootSessionsError.message : "Unknown sessions error."}</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    );
  }

  if (rootSessions.length === 0) {
    return (
      <div className="app-shell">
        <div className="app-frame">
          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>No Sessions Yet</h2>
                <p>`GET /api/v1/sessions/` returned an empty list.</p>
              </div>
            </div>
            <div className="panel__body">
              <div className="empty-state">
                <strong>The dashboard is connected but there are no root sessions to show.</strong>
                <p>Start a session in the backend, then reload this page.</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    );
  }

  const tree = buildSessionTree(rootSessions);
  const activeSession = rootSessions.find((session) => session.id === selectedSessionId) ?? rootSessions[0];
  const canvasSessions = activeSession ? [activeSession, ...childSessions] : [];

  return (
    <div className="app-shell">
      <div className="app-frame">
        <header className="topbar">
          <div className="topbar__title">
            <span className="eyebrow">NightOwl Control Tower</span>
            <h1>Sessions, intent graph, approvals, and token drill-down.</h1>
            <p>
              This first slice executes the frontend spec inside a real `frontend/` app: React,
              TanStack Query, typed contracts, event translation, and a three-panel dashboard.
            </p>
          </div>
          <div className="status-row">
            <span className="pill pill--live">WebSocket live</span>
            <span className="pill">{tasksActive} active tasks</span>
            <span className="pill">{pendingApprovals} waiting roots</span>
            <span className="pill">{liveChannels} routed channels</span>
          </div>
        </header>

        <div className="dashboard-grid">
          <section className="panel panel--session-rail">
            <div className="panel__header">
              <div>
                <h2>Session Tree</h2>
                <p>Top-level sessions from `/api/v1/sessions/`.</p>
              </div>
            </div>
            <div className="panel__body">
              <SessionTree
                onSelectSession={selectSession}
                selectedSessionId={selectedSessionId}
                sessions={tree}
              />
            </div>
          </section>

          <section className="panel panel--canvas">
            <div className="panel__header">
              <div>
                <h2>Execution Canvas</h2>
                <p>Direct child sessions from `/api/v1/sessions/?parentId=&lt;session-id&gt;`.</p>
              </div>
            </div>
            <div className="panel__body">
              {childSessionsError ? (
                <div className="empty-state">
                  <strong>Child sessions failed to load.</strong>
                  <p>{childSessionsError instanceof Error ? childSessionsError.message : "Unknown child session error."}</p>
                </div>
              ) : activeSession ? (
                <SessionCanvas selectedSession={activeSession} sessions={canvasSessions} />
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
