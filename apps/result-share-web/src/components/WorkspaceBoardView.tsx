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
