import type { InvitePageViewModel } from "../lib/types";

type InviteSummaryViewProps = {
  viewModel: InvitePageViewModel;
  apiBaseUrl: string;
  onOpenAnother: () => void;
};

export function InviteSummaryView({
  viewModel,
  apiBaseUrl,
  onOpenAnother,
}: InviteSummaryViewProps) {
  return (
    <>
      <section className="hero-card">
        <div>
          <p className="eyebrow">Public Invite Bootstrap</p>
          <h1>{viewModel.pageTitle}</h1>
          <p className="lede">{viewModel.pageSubtitle}</p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>Status</span>
            <strong>{viewModel.workspaceStatus}</strong>
          </div>
          <div className="hero-chip">
            <span>Role</span>
            <strong>{viewModel.roleToAssign}</strong>
          </div>
          <div className="hero-chip">
            <span>API base</span>
            <strong>{apiBaseUrl}</strong>
          </div>
        </div>
      </section>

      <section className="summary-grid">
        <article className="summary-card">
          <p className="eyebrow">Workspace summary</p>
          <dl className="summary-list">
            <div>
              <dt>Name</dt>
              <dd>{viewModel.workspaceName}</dd>
            </div>
            <div>
              <dt>Slug</dt>
              <dd>{viewModel.workspaceSlug}</dd>
            </div>
            <div>
              <dt>Description</dt>
              <dd>{viewModel.workspaceDescription ?? "No description"}</dd>
            </div>
          </dl>
        </article>

        <article className="summary-card">
          <p className="eyebrow">Invite summary</p>
          <dl className="summary-list">
            <div>
              <dt>Role to assign</dt>
              <dd>{viewModel.roleToAssign}</dd>
            </div>
            <div>
              <dt>Invite status</dt>
              <dd>{viewModel.inviteStatus}</dd>
            </div>
            <div>
              <dt>Remaining claims</dt>
              <dd>{viewModel.remainingClaimsText}</dd>
            </div>
            <div>
              <dt>Expires at</dt>
              <dd>{viewModel.expiresAtText}</dd>
            </div>
          </dl>
        </article>

        <article className="summary-card">
          <p className="eyebrow">Boundary notes</p>
          <ul className="bullet-list">
            {viewModel.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </article>
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Invite label</p>
            <h2>{viewModel.displayLabel ?? "No display label"}</h2>
          </div>
          <button onClick={onOpenAnother} type="button">
            Open another invite
          </button>
        </div>
        <p className="soft-copy">
          This shell stays read-only except for the explicit self-service claim action below.
        </p>
      </section>
    </>
  );
}
