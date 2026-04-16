import type { UserWorkbenchUserDetailRead } from "../lib/types";

type UserDetailViewProps = {
  detail: UserWorkbenchUserDetailRead | null;
  loading: boolean;
  onOpenPaper: (paperId: string) => void;
  onOpenWatchProfilesForUser: (userId: string) => void;
};

export function UserDetailView({
  detail,
  loading,
  onOpenPaper,
  onOpenWatchProfilesForUser,
}: UserDetailViewProps) {
  if (!detail) {
    return (
      <section className="panel-card">
        <div className="empty-state large">
          {loading
            ? "Loading user detail..."
            : "Select a user to inspect papers, watch profiles, and the latest digest summary."}
        </div>
      </section>
    );
  }

  return (
    <section className="detail-root">
      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">User detail</p>
            <h2>{detail.user.name}</h2>
          </div>
          <div className="button-row compact">
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenWatchProfilesForUser(detail.user.id)}
            >
              View watch profiles
            </button>
          </div>
        </div>
        <div className="stat-grid">
          <article className="stat-card">
            <span>Email</span>
            <strong>{detail.user.email ?? "Unavailable"}</strong>
          </article>
          <article className="stat-card">
            <span>Field</span>
            <strong>{detail.user.field ?? "Unavailable"}</strong>
          </article>
          <article className="stat-card">
            <span>Papers</span>
            <strong>{detail.user.paper_count}</strong>
          </article>
          <article className="stat-card">
            <span>Watch profiles</span>
            <strong>{detail.user.watch_profile_count}</strong>
          </article>
        </div>
        {detail.user.latest_digest_issue_summary ? (
          <div className="info-block">
            <strong>Latest digest</strong>
            <p>{detail.user.latest_digest_issue_summary.title}</p>
            <small>{detail.user.latest_digest_issue_summary.summary}</small>
          </div>
        ) : null}
      </section>

      <section className="split-grid">
        <section className="panel-card">
          <div className="panel-card-header">
            <div>
              <p className="eyebrow">Papers</p>
              <h2>User papers</h2>
            </div>
          </div>
          {detail.papers.length === 0 ? (
            <div className="empty-state">No papers for this user yet.</div>
          ) : (
            <ul className="data-list">
              {detail.papers.map((paper) => (
                <li key={paper.id} className="data-list-item">
                  <div>
                    <strong>{paper.title}</strong>
                    <p>
                      {paper.stage}
                      {paper.venue ? ` · ${paper.venue}` : ""} · {paper.progress_percentage}% progress
                    </p>
                    {paper.next_action ? <p>Next: {paper.next_action}</p> : null}
                  </div>
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => onOpenPaper(paper.id)}
                  >
                    Open paper
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel-card">
          <div className="panel-card-header">
            <div>
              <p className="eyebrow">Watch profiles</p>
              <h2>User watch profiles</h2>
            </div>
          </div>
          {detail.watch_profiles.length === 0 ? (
            <div className="empty-state">No watch profiles for this user yet.</div>
          ) : (
            <ul className="data-list">
              {detail.watch_profiles.map((profile) => (
                <li key={profile.id} className="data-list-item">
                  <div>
                    <strong>{profile.label}</strong>
                    <p>
                      {profile.source_mode}
                      {profile.paper_title ? ` · ${profile.paper_title}` : ""}
                    </p>
                  </div>
                  <span className={profile.enabled ? "status-pill ready" : "status-pill archived"}>
                    {profile.enabled ? "enabled" : "disabled"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>

      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Workspace memberships</p>
            <h2>Group workspace links</h2>
          </div>
        </div>
        {detail.workspace_memberships.length === 0 ? (
          <div className="empty-state">No group workspace memberships for this user.</div>
        ) : (
          <ul className="data-list">
            {detail.workspace_memberships.map((membership) => (
              <li key={membership.workspace_id} className="data-list-item">
                <div>
                  <strong>{membership.name}</strong>
                  <p>
                    {membership.slug} · {membership.role}
                  </p>
                </div>
                <span className={`status-pill ${membership.status}`}>{membership.status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
