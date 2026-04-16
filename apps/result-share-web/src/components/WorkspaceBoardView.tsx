import type { WorkspaceBoardViewModel } from "../lib/types";

type WorkspaceBoardViewProps = {
  viewModel: WorkspaceBoardViewModel;
};

export function WorkspaceBoardView({ viewModel }: WorkspaceBoardViewProps) {
  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Workspace Board Share</p>
          <h2>{viewModel.pageTitle}</h2>
          <p className="lede">{viewModel.description ?? "No workspace description available."}</p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>Status</span>
            <strong>{viewModel.statusLabel}</strong>
          </div>
          <div className="hero-chip">
            <span>Members / Papers</span>
            <strong>
              {viewModel.memberCount} / {viewModel.paperCount}
            </strong>
          </div>
        </div>
      </section>

      <section className="summary-grid">
        <article className="summary-card">
          <p className="eyebrow">Quick stats</p>
          <dl className="summary-list compact">
            <div>
              <dt>Blocked papers</dt>
              <dd>{viewModel.quickStats.blocked_paper_count}</dd>
            </div>
            <div>
              <dt>Papers with signals</dt>
              <dd>{viewModel.quickStats.papers_with_signals_count}</dd>
            </div>
          </dl>
        </article>
        <article className="summary-card">
          <p className="eyebrow">Members</p>
          <strong>{viewModel.memberCount}</strong>
        </article>
        <article className="summary-card">
          <p className="eyebrow">Papers</p>
          <strong>{viewModel.paperCount}</strong>
        </article>
      </section>

      {viewModel.workspaceInviteHandoff ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Workspace access handoff</p>
              <h3>Invite and join stay in a separate flow</h3>
            </div>
            <span className="pill">
              {viewModel.workspaceInviteHandoff.directClaimViaSharePage
                ? "Direct join available"
                : "Read-only handoff"}
            </span>
          </div>
          <dl className="summary-list compact">
            <div>
              <dt>Separate invite token required</dt>
              <dd>
                {viewModel.workspaceInviteHandoff.separateInviteTokenRequired ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Self-service claim supported</dt>
              <dd>
                {viewModel.workspaceInviteHandoff.selfServiceClaimSupported ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Direct claim via share page</dt>
              <dd>
                {viewModel.workspaceInviteHandoff.directClaimViaSharePage ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Invite handoff redirect supported</dt>
              <dd>{viewModel.workspaceInviteHandoff.handoffRedirectSupported ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Source files included</dt>
              <dd>{viewModel.workspaceInviteHandoff.sourceFilesIncluded ? "Yes" : "No"}</dd>
            </div>
          </dl>
          <ul className="bullet-list">
            <li>This workspace-board share is read-only and cannot join membership directly.</li>
            {viewModel.workspaceInviteHandoff.notes.map((note, index) => (
              <li key={`${index}:${note}`}>{note}</li>
            ))}
          </ul>
          {viewModel.workspaceInviteHandoff.inviteHandoffUrl ? (
            <p className="action-row">
              <a
                className="button-link"
                href={viewModel.workspaceInviteHandoff.inviteHandoffUrl}
                rel="noreferrer"
                target="_blank"
              >
                Open invite entry
              </a>
            </p>
          ) : null}
          {viewModel.workspaceInviteHandoff.inviteShellEntryUrl ? (
            <p className="soft-copy">
              Invite shell entry:{" "}
              <a
                href={viewModel.workspaceInviteHandoff.inviteShellEntryUrl}
                rel="noreferrer"
                target="_blank"
              >
                {viewModel.workspaceInviteHandoff.inviteShellEntryUrl}
              </a>
            </p>
          ) : (
            <p className="soft-copy">
              Ask a workspace owner or operator for a separate invite token to continue.
            </p>
          )}
        </section>
      ) : null}

      {viewModel.resultCollectHandoff ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Result collect handoff</p>
              <h3>Next step: collect papers into this workspace</h3>
            </div>
            <span className="pill">
              {viewModel.resultCollectHandoff.directCollectViaCurrentShare
                ? "Direct collect available"
                : "Read-only handoff"}
            </span>
          </div>
          <dl className="summary-list compact">
            <div>
              <dt>Separate result share token required</dt>
              <dd>
                {viewModel.resultCollectHandoff.separateResultShareTokenRequired ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Collect supported via self-service</dt>
              <dd>
                {viewModel.resultCollectHandoff.collectSupportedViaSelfService ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Direct collect via current share</dt>
              <dd>
                {viewModel.resultCollectHandoff.directCollectViaCurrentShare ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Collect handoff redirect supported</dt>
              <dd>{viewModel.resultCollectHandoff.handoffRedirectSupported ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Supported share kinds</dt>
              <dd>{viewModel.resultCollectHandoff.supportedShareKinds.join(", ")}</dd>
            </div>
            <div>
              <dt>Source files included</dt>
              <dd>{viewModel.resultCollectHandoff.sourceFilesIncluded ? "Yes" : "No"}</dd>
            </div>
          </dl>
          <ul className="bullet-list">
            <li>This workspace-board share is read-only and cannot collect papers directly.</li>
            {viewModel.resultCollectHandoff.notes.map((note, index) => (
              <li key={`${index}:${note}`}>{note}</li>
            ))}
          </ul>
          {viewModel.resultCollectHandoff.collectHandoffUrl ? (
            <p className="action-row">
              <a
                className="button-link"
                href={viewModel.resultCollectHandoff.collectHandoffUrl}
                rel="noreferrer"
                target="_blank"
              >
                Open result collect entry
              </a>
            </p>
          ) : null}
          {viewModel.resultCollectHandoff.resultShareShellEntryUrl ? (
            <p className="soft-copy">
              Result-share shell entry:{" "}
              <a
                href={viewModel.resultCollectHandoff.resultShareShellEntryUrl}
                rel="noreferrer"
                target="_blank"
              >
                {viewModel.resultCollectHandoff.resultShareShellEntryUrl}
              </a>
            </p>
          ) : (
            <p className="soft-copy">
              Open the existing result-share shell with a separate digest or paper share token to
              continue.
            </p>
          )}
        </section>
      ) : null}

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Members</p>
            <h3>Safe workspace member summaries</h3>
          </div>
        </div>
        <div className="list-stack">
          {viewModel.members.map((member) => (
            <article className="list-card" key={member.member_id}>
              <div className="list-card-header">
                <div>
                  <h4>{member.name}</h4>
                  <p className="meta-copy">Role: {member.role}</p>
                </div>
                <span className="pill">{member.email ? "Admin context only" : "Public safe"}</span>
              </div>
              <p className="soft-copy">Joined at: {member.joined_at}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Papers</p>
            <h3>Structured paper snapshots</h3>
          </div>
        </div>
        <div className="list-stack">
          {viewModel.papers.map((paper) => (
            <article className="list-card" key={paper.paper_id}>
              <div className="list-card-header">
                <div>
                  <h4>{paper.title}</h4>
                  <p className="meta-copy">
                    {paper.stage} · {paper.type} · {paper.venue ?? "No venue"}
                  </p>
                </div>
                <span className="pill">{paper.progress_percentage}%</span>
              </div>
              <p className="soft-copy">Priority: {paper.priority}</p>
              <p>{paper.next_action ?? "No next action available."}</p>
              {paper.blocker ? <p className="soft-copy">Blocker: {paper.blocker}</p> : null}
              {paper.latest_signal_summary ? (
                <p className="soft-copy">
                  Latest signal: {paper.latest_signal_summary.source} · citations{" "}
                  {paper.latest_signal_summary.citation_count ?? "n/a"} · reads{" "}
                  {paper.latest_signal_summary.read_count ?? "n/a"}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
