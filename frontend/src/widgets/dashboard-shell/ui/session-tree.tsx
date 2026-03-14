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
        title={session.label}
        type="button"
      >
        <div className="session-card__row">
          <span className="session-card__goal">{session.taskSummary}</span>
          <span
            className={cn(
              "badge",
              session.status === "running" && "badge--running",
              session.status === "waiting" && "badge--waiting",
              session.status === "blocked" && "badge--blocked",
              session.status === "completed" && "badge--completed",
            )}
          >
            {session.status}
          </span>
        </div>
      </button>
      {session.children.length > 0 && (
        <div className="tree__children">
          {session.children.map((child) => (
            <SessionTreeItem
              key={child.id}
              onSelectSession={onSelectSession}
              selectedSessionId={selectedSessionId}
              session={child}
            />
          ))}
        </div>
      )}
    </div>
  );
}
