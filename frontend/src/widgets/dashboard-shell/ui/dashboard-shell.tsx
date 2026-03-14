import { buildSessionTree } from "entities/session/model/selectors";
import { useSelectionStore } from "features/session-controls/model/selection-store";
import { useDashboardData } from "features/dashboard/model/use-dashboard-data";
import { SessionTree } from "widgets/dashboard-shell/ui/session-tree";
import { IntentList } from "features/intention-graph/ui/intent-list";
import { ApprovalList } from "features/approvals/ui/approval-list";
import { TokenViewer } from "features/token-viewer/ui/token-viewer";

export function DashboardShell() {
  const { data, isLoading } = useDashboardData();
  const { selectedIntentId, selectedSessionId, selectIntent, selectSession } = useSelectionStore();

  if (isLoading || !data) {
    return <div className="app-shell">Loading dashboard…</div>;
  }

  const tree = buildSessionTree(data.sessions);
  const activeSession = data.sessions.find((session) => session.id === selectedSessionId) ?? data.sessions[0];
  const visibleIntents = data.intents.filter((intent) => intent.sessionId === activeSession?.id);
  const activeIntent = data.intents.find((intent) => intent.id === selectedIntentId) ?? visibleIntents[0];
  const visibleTokens = data.tokens.filter((token) => token.intentId === activeIntent?.id);

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
          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>Session Tree</h2>
                <p>Infinite nesting, task summaries, state badges, and focus selection.</p>
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

          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>Intent Graph Surface</h2>
                <p>List fallback for graph-heavy exploration, wired to token-range detail.</p>
              </div>
            </div>
            <div className="panel__body">
              <div className="metric-strip">
                <article className="metric-card">
                  <span>Focused Session</span>
                  <strong>{activeSession?.label ?? "n/a"}</strong>
                </article>
                <article className="metric-card">
                  <span>Session State</span>
                  <strong>{activeSession?.status ?? "n/a"}</strong>
                </article>
                <article className="metric-card">
                  <span>Current Intent</span>
                  <strong>{visibleIntents.length}</strong>
                </article>
              </div>
              <IntentList
                intents={visibleIntents}
                onSelectIntent={selectIntent}
                selectedIntentId={selectedIntentId}
              />
            </div>
          </section>

          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>Detail Rail</h2>
                <p>Approval queue, event timeline, and raw token viewer for the selected intent.</p>
              </div>
            </div>
            <div className="panel__body">
              <div className="detail-grid">
                <section>
                  <div className="panel__header" style={{ padding: 0, borderBottom: "none" }}>
                    <div>
                      <h3>Approval Queue</h3>
                      <p>Human-in-the-loop decisions before risky actions execute.</p>
                    </div>
                  </div>
                  <ApprovalList approvals={data.approvals} />
                </section>

                <section>
                  <div className="panel__header" style={{ padding: 0, borderBottom: "none" }}>
                    <div>
                      <h3>Raw Tokens</h3>
                      <p>
                        Token-range drill-down for <strong>{activeIntent?.title ?? "selected intent"}</strong>.
                      </p>
                    </div>
                  </div>
                  <TokenViewer tokens={visibleTokens} />
                </section>

                <section>
                  <div className="panel__header" style={{ padding: 0, borderBottom: "none" }}>
                    <div>
                      <h3>Latest Events</h3>
                      <p>Realtime summary cards translated from the gateway contract.</p>
                    </div>
                  </div>
                  <div className="timeline">
                    {data.events.map((event) => (
                      <article className="event-card" key={event.id}>
                        <div className="detail-row">
                          <strong>{event.title}</strong>
                          <span className="muted">{new Date(event.happenedAt).toLocaleTimeString()}</span>
                        </div>
                        <p className="approval-card__justification">{event.detail}</p>
                      </article>
                    ))}
                  </div>
                </section>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
