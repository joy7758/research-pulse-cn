import type { FormEvent } from "react";

type TokenEntryViewProps = {
  apiBaseUrl: string;
  shareToken: string;
  loading: boolean;
  errorTitle: string | null;
  errorMessage: string | null;
  noticeMessage: string | null;
  onApiBaseUrlChange: (value: string) => void;
  onShareTokenChange: (value: string) => void;
  onSubmit: () => void;
};

export function TokenEntryView({
  apiBaseUrl,
  shareToken,
  loading,
  errorTitle,
  errorMessage,
  noticeMessage,
  onApiBaseUrlChange,
  onShareTokenChange,
  onSubmit,
}: TokenEntryViewProps) {
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
          Paste a share token or open the shell with a <code>/share/&lt;token&gt;</code> URL.
          This shell only consumes public read-only share endpoints and never stores tokens in
          browser storage.
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
            Share Token
            <textarea
              name="shareToken"
              placeholder="Paste a share token"
              rows={4}
              value={shareToken}
              onChange={(event) => onShareTokenChange(event.target.value)}
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
