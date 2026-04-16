import type { PaperSnapshotViewModel } from "../lib/types";

type PaperSnapshotViewProps = {
  viewModel: PaperSnapshotViewModel;
};

export function PaperSnapshotView({ viewModel }: PaperSnapshotViewProps) {
  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Paper Snapshot Share</p>
          <h2>{viewModel.pageTitle}</h2>
          <p className="lede">
            Structured read-only paper snapshot with safe metadata only.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>Status</span>
            <strong>{viewModel.status}</strong>
          </div>
          <div className="hero-chip">
            <span>Owner</span>
            <strong>{viewModel.ownerName ?? "Hidden"}</strong>
          </div>
        </div>
      </section>

      <section className="summary-grid">
        {viewModel.metadataRows.map((row) => (
          <article className="summary-card" key={row.label}>
            <p className="eyebrow">{row.label}</p>
            <strong>{row.value}</strong>
          </article>
        ))}
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Current paper state</p>
            <h3>Next action & blockers</h3>
          </div>
        </div>
        <dl className="summary-list compact">
          <div>
            <dt>Next action</dt>
            <dd>{viewModel.nextAction ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Blocker</dt>
            <dd>{viewModel.blocker ?? "None"}</dd>
          </div>
        </dl>
      </section>

      {viewModel.latestSignalSummary ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Latest signal summary</p>
              <h3>{viewModel.latestSignalSummary.source}</h3>
            </div>
          </div>
          <dl className="summary-list compact">
            <div>
              <dt>Citations</dt>
              <dd>{viewModel.latestSignalSummary.citation_count ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Downloads</dt>
              <dd>{viewModel.latestSignalSummary.download_count ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Reads</dt>
              <dd>{viewModel.latestSignalSummary.read_count ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Fetched at</dt>
              <dd>{viewModel.latestSignalSummary.fetched_at}</dd>
            </div>
          </dl>
        </section>
      ) : null}
    </div>
  );
}
