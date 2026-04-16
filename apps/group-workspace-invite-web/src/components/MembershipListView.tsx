import type { GroupWorkspaceMembershipRead } from "../lib/types";

type MembershipListViewProps = {
  memberships: GroupWorkspaceMembershipRead[];
  loading: boolean;
};

export function MembershipListView({ memberships, loading }: MembershipListViewProps) {
  return (
    <section className="panel-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Current memberships</p>
          <h2>Workspace memberships</h2>
        </div>
        <span className="pill">{memberships.length} workspace(s)</span>
      </div>
      {loading ? (
        <p className="soft-copy">Loading current memberships...</p>
      ) : memberships.length === 0 ? (
        <p className="soft-copy">
          No workspace memberships are attached to the current self-service grant yet.
        </p>
      ) : (
        <div className="list-stack">
          {memberships.map((membership) => (
            <article className="list-card" key={membership.member_id}>
              <div className="list-card-header">
                <div>
                  <h3>{membership.workspace_summary.name}</h3>
                  <p className="meta-copy">
                    {membership.workspace_summary.slug} · {membership.workspace_summary.status}
                  </p>
                </div>
                <span className="pill">{membership.role}</span>
              </div>
              <p>{membership.workspace_summary.description ?? "No description"}</p>
              <p className="soft-copy">Joined at: {membership.joined_at}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
