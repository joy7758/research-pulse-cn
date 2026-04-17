import type { FormEvent } from "react";
import type { ResultShareAccessMode } from "../lib/types";

type TokenEntryViewProps = {
  apiBaseUrl: string;
  shareAccessMode: ResultShareAccessMode;
  shareValue: string;
  loading: boolean;
  errorTitle: string | null;
  errorMessage: string | null;
  noticeMessage: string | null;
  onApiBaseUrlChange: (value: string) => void;
  onShareAccessModeChange: (value: ResultShareAccessMode) => void;
  onShareValueChange: (value: string) => void;
  onSubmit: () => void;
};

export function TokenEntryView({
  apiBaseUrl,
  shareAccessMode,
  shareValue,
  loading,
  errorTitle,
  errorMessage,
  noticeMessage,
  onApiBaseUrlChange,
  onShareAccessModeChange,
  onShareValueChange,
  onSubmit,
}: TokenEntryViewProps) {
  const accessLabel = shareAccessMode === "alias" ? "Share Alias" : "Share Token";
  const accessPlaceholder =
    shareAccessMode === "alias" ? "Paste a share alias" : "Paste a share token";
  const accessRoute =
    shareAccessMode === "alias" ? "/share-alias/<alias>" : "/share/<token>";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <main className="connect-shell">
      <section className="connect-card">
        <p className="eyebrow">Result Share</p>
        <h1>Open a read-only structured share</h1>
        <p className="lede">
          Paste a share token or alias, or open the shell with a <code>{accessRoute}</code> URL.
          This shell only consumes public read-only share endpoints and never stores tokens or
          aliases in browser storage. After bootstrap loads, you can optionally connect a
          self-service token in memory to preview or perform collect actions.
        </p>

        {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
        {errorMessage ? (
          <div className="inline-banner danger" role="alert">
            <strong>{errorTitle ?? "Unable to load share"}</strong>
            <span>{errorMessage}</span>
          </div>
        ) : null}

        <form className="token-form" onSubmit={handleSubmit}>
          <label>
            API Base URL
            <input
              autoComplete="off"
              name="apiBaseUrl"
              placeholder="http://127.0.0.1:8000"
              value={apiBaseUrl}
              onChange={(event) => onApiBaseUrlChange(event.target.value)}
            />
          </label>

          <label>
            Share Access Mode
            <select
              name="shareAccessMode"
              value={shareAccessMode}
              onChange={(event) =>
                onShareAccessModeChange(event.target.value as ResultShareAccessMode)
              }
            >
              <option value="token">Raw share token</option>
              <option value="alias">Opaque share alias</option>
            </select>
          </label>

          <label>
            {accessLabel}
            <textarea
              name="shareValue"
              placeholder={accessPlaceholder}
              rows={4}
              value={shareValue}
              onChange={(event) => onShareValueChange(event.target.value)}
            />
          </label>

          <div className="button-row">
            <button disabled={loading} type="submit">
              {loading ? "Opening share..." : "Open share"}
            </button>
          </div>
        </form>

        <div className="summary-grid">
          <article className="summary-card">
            <p className="eyebrow">Supported kinds</p>
            <ul className="bullet-list">
              <li>
                <code>digest_issue</code> structured digest
              </li>
              <li>
                <code>paper_snapshot</code> safe paper summary
              </li>
              <li>
                <code>workspace_board</code> shared board overview
              </li>
            </ul>
          </article>
          <article className="summary-card">
            <p className="eyebrow">Safety exclusions</p>
            <ul className="bullet-list">
              <li>No source-file or PDF sharing</li>
              <li>No local attachment paths or downloads</li>
              <li>No local note contents or edit actions</li>
            </ul>
          </article>
        </div>
      </section>
    </main>
  );
}
