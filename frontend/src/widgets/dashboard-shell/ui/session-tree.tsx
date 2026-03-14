import type { SessionTreeNode } from "entities/session/model/types";
import { cn } from "shared/lib/cn";

type SessionTreeProps = {
  sessions: SessionTreeNode[];
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
};

export function SessionTree({ sessions, selectedSessionId, onSelectSession }: SessionTreeProps) {
  return (
    <div className="tree">
      {sessions.map((session) => (
        <SessionTreeItem
          key={session.id}
          onSelectSession={onSelectSession}
          selectedSessionId={selectedSessionId}
          session={session}
        />
      ))}
    </div>
  );
}

type SessionTreeItemProps = {
  session: SessionTreeNode;
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
};

function SessionTreeItem({ session, selectedSessionId, onSelectSession }: SessionTreeItemProps) {
  return (
    <div>
      <button
        className="session-card"
        data-selected={selectedSessionId === session.id}
        onClick={() => onSelectSession(session.id)}
        type="button"
      >
        <div className="session-card__row">
          <div className="session-card__title">
            <strong>{session.label}</strong>
            <span>{session.taskSummary}</span>
          </div>
          <span
            className={cn(
              "badge",
              session.status === "running" && "badge--running",
              session.status === "waiting" && "badge--waiting",
              session.status === "blocked" && "badge--blocked",
            )}
          >
            {session.status}
          </span>
        </div>
        <div className="detail-row">
          <span className="muted">
            {session.role} via {session.channel}
          </span>
          <span className="muted">{session.currentIntent}</span>
        </div>
      </button>
      {session.children.length > 0 ? (
        <div className="session-card__children">
          {session.children.map((child) => (
            <SessionTreeItem
              key={child.id}
              onSelectSession={onSelectSession}
              selectedSessionId={selectedSessionId}
              session={child}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
