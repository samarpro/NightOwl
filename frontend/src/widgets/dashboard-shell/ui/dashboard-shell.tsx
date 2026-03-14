import { buildSessionTree } from "entities/session/model/selectors";
import { useSelectionStore } from "features/session-controls/model/selection-store";
import { useDashboardData } from "features/dashboard/model/use-dashboard-data";
import { SessionCanvas } from "features/session-canvas/ui/session-canvas";
import { SessionTree } from "widgets/dashboard-shell/ui/session-tree";

export function DashboardShell() {
  const { data, isLoading } = useDashboardData();
  const { selectedSessionId, selectSession } = useSelectionStore();

  if (isLoading || !data) {
    return <div className="app-shell">Loading dashboard…</div>;
  }

  const tree = buildSessionTree(data.sessions);
  const activeSession = data.sessions.find((session) => session.id === selectedSessionId) ?? data.sessions[0];

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
            <span className="pill">{data.tasksActive} active tasks</span>
            <span className="pill">{data.pendingApprovals} pending approvals</span>
            <span className="pill">{data.liveChannels} healthy channels</span>
          </div>
        </header>

        <div className="dashboard-grid">
          <section className="panel panel--session-rail">
            <div className="panel__header">
              <div>
                <h2>Session Tree</h2>
                <p>Compact session goals with status-only focus selection.</p>
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
                <p>Click a session to expand its agent, thinking, and tool-call graph.</p>
              </div>
            </div>
            <div className="panel__body">
              {activeSession ? (
                <SessionCanvas
                  intents={data.intents}
                  selectedSession={activeSession}
                  sessions={data.sessions}
                  tokens={data.tokens}
                />
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
