import type { Approval } from "entities/approval/model/types";
import { cn } from "shared/lib/cn";

type ApprovalListProps = {
  approvals: Approval[];
};

export function ApprovalList({ approvals }: ApprovalListProps) {
  return (
    <div className="stack">
      {approvals.map((approval) => (
        <article className="approval-card" key={approval.id}>
          <div className="approval-card__row">
            <div>
              <div className="small-label">{approval.toolName}</div>
              <strong>{approval.title}</strong>
            </div>
            <span className={cn("badge", approval.riskLevel === "high" && "badge--high")}>
              {approval.riskLevel} risk
            </span>
          </div>
          <p className="approval-card__justification">{approval.justification}</p>
          <div className="detail-row">
            <span className="muted">Expires {new Date(approval.expiresAt).toLocaleTimeString()}</span>
            <div className="button-row">
              <button className="button button--ghost" type="button">
                Reject
              </button>
              <button className="button button--primary" type="button">
                Approve
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
