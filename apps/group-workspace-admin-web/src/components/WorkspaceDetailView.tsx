import type {
  GroupWorkspaceRead,
  GroupWorkspaceMemberRole,
  GroupWorkspaceStatus,
  LookupOption,
  ResultShareGrantRead,
  ShareGrantOneTimeDisplayModel,
  WorkspaceBoardShareCreateInput,
  WorkspaceBoardViewModel,
  WorkspaceMemberAddInput,
  WorkspacePaperAddInput,
  WorkspaceUpdateInput,
} from "../lib/types";

type WorkspaceDetailViewProps = {
  workspace: GroupWorkspaceRead | null;
  board: WorkspaceBoardViewModel | null;
  updateInput: WorkspaceUpdateInput;
  memberInput: WorkspaceMemberAddInput;
  paperInput: WorkspacePaperAddInput;
  shareInput: WorkspaceBoardShareCreateInput;
  userOptions: LookupOption[];
  paperOptions: LookupOption[];
  shareGrants: ResultShareGrantRead[];
  actionLoading: boolean;
  oneTimeGrant: ShareGrantOneTimeDisplayModel | null;
  onUpdateInputChange: (patch: Partial<WorkspaceUpdateInput>) => void;
  onMemberInputChange: (patch: Partial<WorkspaceMemberAddInput>) => void;
  onPaperInputChange: (patch: Partial<WorkspacePaperAddInput>) => void;
  onShareInputChange: (patch: Partial<WorkspaceBoardShareCreateInput>) => void;
  onSaveWorkspace: () => void;
  onAddMember: () => void;
  onRemoveMember: (memberId: string) => void;
  onAddPaper: () => void;
  onRemovePaper: (paperId: string) => void;
  onCreateShareGrant: () => void;
  onRevokeShareGrant: (grantId: string) => void;
  onDismissOneTimeGrant: () => void;
};

const memberRoles: GroupWorkspaceMemberRole[] = ["owner", "editor", "viewer"];
const workspaceStatuses: GroupWorkspaceStatus[] = ["active", "archived"];

export function WorkspaceDetailView({
  workspace,
  board,
  updateInput,
  memberInput,
  paperInput,
  shareInput,
  userOptions,
  paperOptions,
  shareGrants,
  actionLoading,
  oneTimeGrant,
  onUpdateInputChange,
  onMemberInputChange,
  onPaperInputChange,
  onShareInputChange,
  onSaveWorkspace,
  onAddMember,
  onRemoveMember,
  onAddPaper,
  onRemovePaper,
  onCreateShareGrant,
  onRevokeShareGrant,
  onDismissOneTimeGrant,
}: WorkspaceDetailViewProps) {
  if (!workspace || !board) {
    return (
      <section className="detail-root">
        <div className="empty-state large">Select a workspace to inspect its board and manage members, papers, and shares.</div>
      </section>
    );
  }

  return (
    <section className="detail-root">
      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Workspace summary</p>
            <h2>{board.title}</h2>
          </div>
          <span className={`status-pill ${board.status}`}>{board.status}</span>
        </div>
        <div className="stat-grid">
          <article className="stat-card">
            <span>Members</span>
            <strong>{board.memberCount}</strong>
          </article>
          <article className="stat-card">
            <span>Papers</span>
            <strong>{board.paperCount}</strong>
          </article>
          <article className="stat-card">
            <span>Blocked papers</span>
            <strong>{board.blockedPaperCount}</strong>
          </article>
          <article className="stat-card">
            <span>Papers with signals</span>
            <strong>{board.papersWithSignalsCount}</strong>
          </article>
        </div>
        <div className="field-grid">
          <label className="field-stack">
            <span>Name</span>
            <input
              type="text"
              value={updateInput.name}
              onChange={(event) => onUpdateInputChange({ name: event.target.value })}
            />
          </label>
          <label className="field-stack">
            <span>Status</span>
            <select
              value={updateInput.status}
              onChange={(event) =>
                onUpdateInputChange({ status: event.target.value as GroupWorkspaceStatus })
              }
            >
              {workspaceStatuses.map((statusValue) => (
                <option key={statusValue} value={statusValue}>
                  {statusValue}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="field-stack">
          <span>Description</span>
          <textarea
            rows={3}
            value={updateInput.description}
            onChange={(event) => onUpdateInputChange({ description: event.target.value })}
          />
        </label>
        <div className="button-row">
          <button type="button" className="button-primary" disabled={actionLoading} onClick={onSaveWorkspace}>
            {actionLoading ? "Saving..." : "Save workspace"}
          </button>
        </div>
      </section>

      <section className="split-grid">
        <section className="panel-card">
          <div className="panel-card-header">
            <div>
              <p className="eyebrow">Members</p>
              <h2>Workspace members</h2>
            </div>
          </div>
          <div className="field-grid">
            <label className="field-stack">
              <span>Add user</span>
              <select
                value={memberInput.user_id}
                onChange={(event) => onMemberInputChange({ user_id: event.target.value })}
              >
                <option value="">Select a user</option>
                {userOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-stack">
              <span>Role</span>
              <select
                value={memberInput.role}
                onChange={(event) =>
                  onMemberInputChange({ role: event.target.value as GroupWorkspaceMemberRole })
                }
              >
                {memberRoles.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="button-row">
            <button type="button" className="button-primary" disabled={actionLoading} onClick={onAddMember}>
              Add member
            </button>
          </div>
          {board.members.length === 0 ? (
            <div className="empty-state">No members in this workspace yet.</div>
          ) : (
            <ul className="data-list">
              {board.members.map((member) => (
                <li key={member.member_id} className="data-list-item">
                  <div>
                    <strong>{member.name}</strong>
                    <p>
                      {member.role}
                      {member.email ? ` · ${member.email}` : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="button-danger"
                    disabled={actionLoading}
                    onClick={() => onRemoveMember(member.member_id)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel-card">
          <div className="panel-card-header">
            <div>
              <p className="eyebrow">Papers</p>
              <h2>Structured paper snapshots</h2>
            </div>
          </div>
          <label className="field-stack">
            <span>Add paper</span>
            <select
              value={paperInput.paper_id}
              onChange={(event) => onPaperInputChange({ paper_id: event.target.value })}
            >
              <option value="">Select a paper</option>
              {paperOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="button-row">
            <button type="button" className="button-primary" disabled={actionLoading} onClick={onAddPaper}>
              Add paper
            </button>
          </div>
          {board.papers.length === 0 ? (
            <div className="empty-state">No papers added to this workspace yet.</div>
          ) : (
            <ul className="data-list">
              {board.papers.map((paper) => (
                <li key={paper.paper_id} className="data-list-item">
                  <div>
                    <strong>{paper.title}</strong>
                    <p>
                      {paper.stage}
                      {paper.venue ? ` · ${paper.venue}` : ""} · priority {paper.priority}
                    </p>
                    {paper.next_action ? <p>Next: {paper.next_action}</p> : null}
                  </div>
                  <button
                    type="button"
                    className="button-danger"
                    disabled={actionLoading}
                    onClick={() => onRemovePaper(paper.paper_id)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>

      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Workspace-board shares</p>
            <h2>Read-only share grants</h2>
          </div>
        </div>

        {oneTimeGrant ? (
          <div className="inline-banner success">
            <div className="inline-banner-copy">
              <strong>Share token created</strong>
              <span>{oneTimeGrant.copyHint}</span>
            </div>
            <textarea readOnly rows={3} value={oneTimeGrant.plainTextToken} />
            <div className="button-row">
              <button type="button" className="button-secondary" onClick={onDismissOneTimeGrant}>
                Dismiss token
              </button>
            </div>
          </div>
        ) : null}

        <div className="field-grid">
          <label className="field-stack">
            <span>Display label</span>
            <input
              type="text"
              value={shareInput.display_label}
              onChange={(event) => onShareInputChange({ display_label: event.target.value })}
              placeholder="Optional workspace-board label"
            />
          </label>
          <label className="field-stack">
            <span>Expires at</span>
            <input
              type="datetime-local"
              value={shareInput.expires_at ?? ""}
              onChange={(event) =>
                onShareInputChange({ expires_at: event.target.value || null })
              }
            />
          </label>
        </div>
        <div className="button-row">
          <button
            type="button"
            className="button-primary"
            disabled={actionLoading}
            onClick={onCreateShareGrant}
          >
            Create workspace_board share grant
          </button>
        </div>

        {shareGrants.length === 0 ? (
          <div className="empty-state">No workspace-board share grants issued for this workspace yet.</div>
        ) : (
          <ul className="data-list">
            {shareGrants.map((grant) => (
              <li key={grant.id} className="data-list-item">
                <div>
                  <strong>{grant.display_label ?? grant.id}</strong>
                  <p>
                    {grant.share_kind} · {grant.status}
                    {grant.expires_at ? ` · expires ${grant.expires_at}` : ""}
                  </p>
                </div>
                <button
                  type="button"
                  className="button-danger"
                  disabled={actionLoading || grant.status === "revoked"}
                  onClick={() => onRevokeShareGrant(grant.id)}
                >
                  {grant.status === "revoked" ? "Revoked" : "Revoke"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
