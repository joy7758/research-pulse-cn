import { formatReasonCode } from "../lib/shareModel";
import type { GroupWorkspaceResultCollectionRead } from "../lib/types";

type WorkspaceResultCollectionsViewProps = {
  collections: GroupWorkspaceResultCollectionRead[];
};

export function WorkspaceResultCollectionsView({
  collections,
}: WorkspaceResultCollectionsViewProps) {
  if (collections.length === 0) {
    return (
      <div className="empty-state">
        No workspace collect records are available for the current self-service token yet.
      </div>
    );
  }

  return (
    <div className="list-stack">
      {collections.map((item) => (
        <article className="list-card" key={item.record.id}>
          <div className="list-card-header">
            <div>
              <h4>{item.paper.title}</h4>
              <p className="meta-copy">
                {item.workspace.name} ({item.workspace.slug}) · {item.paper.stage} · {item.paper.type}
              </p>
            </div>
            <span className="pill">{item.record.status}</span>
          </div>
          <dl className="summary-list compact">
            <div>
              <dt>Workspace status</dt>
              <dd>{item.workspace.status}</dd>
            </div>
            <div>
              <dt>Priority</dt>
              <dd>{item.paper.priority}</dd>
            </div>
            <div>
              <dt>Collected at</dt>
              <dd>{item.record.created_at}</dd>
            </div>
          </dl>
          {item.record.reason_codes.length > 0 ? (
            <p className="soft-copy">
              Reason codes: {item.record.reason_codes.map(formatReasonCode).join(", ")}
            </p>
          ) : null}
        </article>
      ))}
    </div>
  );
}
