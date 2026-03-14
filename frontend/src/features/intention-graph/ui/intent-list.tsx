import type { IntentNode } from "entities/intent/model/types";
import { cn } from "shared/lib/cn";

type IntentListProps = {
  intents: IntentNode[];
  selectedIntentId: string | null;
  onSelectIntent: (intentId: string) => void;
};

export function IntentList({ intents, selectedIntentId, onSelectIntent }: IntentListProps) {
  return (
    <div className="stack">
      {intents.map((intent) => (
        <button
          className="intent-card"
          key={intent.id}
          onClick={() => onSelectIntent(intent.id)}
          type="button"
        >
          <div className="intent-card__row">
            <div className="intent-card__title">
              <strong>{intent.service}</strong>
              <span>{intent.title}</span>
            </div>
            <span
              className={cn(
                "badge",
                intent.status === "running" && "badge--running",
                intent.status === "waiting" && "badge--waiting",
                intent.riskLevel === "high" && "badge--high",
              )}
            >
              {intent.status}
            </span>
          </div>
          <div className="detail-row">
            <span className="muted">
              token range {intent.tokenRange.start}-{intent.tokenRange.end}
            </span>
            <span className="muted">{Math.round(intent.elapsedMs / 1000)}s</span>
          </div>
          {selectedIntentId === intent.id ? (
            <div className="detail-row">
              <span className="small-label">Selected for token drill-down</span>
            </div>
          ) : null}
        </button>
      ))}
    </div>
  );
}
