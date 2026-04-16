import type { ResultCollectHandoffViewModel } from "../lib/types";

type ResultCollectHandoffViewProps = {
  viewModel: ResultCollectHandoffViewModel;
  variant?: "claim" | "membership";
};

export function ResultCollectHandoffView({
  viewModel,
  variant = "claim",
}: ResultCollectHandoffViewProps) {
  return (
    <section className="panel-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Result collect handoff</p>
          <h2>{viewModel.title}</h2>
        </div>
        <span className="pill">{variant === "claim" ? "After membership" : "Membership next step"}</span>
      </div>
      <p className="status-copy">{viewModel.message}</p>
      <dl className="summary-list compact">
        <div>
          <dt>Separate result-share token required</dt>
          <dd>{viewModel.separateResultShareTokenRequired ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Result-share bootstrap available</dt>
          <dd>{viewModel.resultShareBootstrapAvailable ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Collect supported via self-service</dt>
          <dd>{viewModel.collectSupportedViaSelfService ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Direct collect via invite page</dt>
          <dd>{viewModel.directCollectViaInvitePage ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Source files included</dt>
          <dd>{viewModel.sourceFilesIncluded ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Supported share kinds</dt>
          <dd>{viewModel.supportedShareKindsText}</dd>
        </div>
      </dl>
      <ul className="bullet-list">
        {viewModel.notes.map((note, index) => (
          <li key={`${index}:${note}`}>{note}</li>
        ))}
      </ul>
      {viewModel.resultShareShellEntryUrl ? (
        <p className="soft-copy">
          Result-share shell entry:{" "}
          <a href={viewModel.resultShareShellEntryUrl} rel="noreferrer" target="_blank">
            {viewModel.resultShareShellEntryUrl}
          </a>
        </p>
      ) : (
        <p className="soft-copy">
          Ask the workspace owner to share a separate digest or paper result token when you are
          ready to collect results.
        </p>
      )}
    </section>
  );
}
