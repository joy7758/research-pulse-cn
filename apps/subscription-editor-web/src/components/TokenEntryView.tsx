import type { FormEvent } from "react";

type TokenEntryViewProps = {
  apiBaseUrl: string;
  handoffToken: string;
  connecting: boolean;
  errorMessage: string | null;
  noticeMessage: string | null;
  onApiBaseUrlChange: (value: string) => void;
  onHandoffTokenChange: (value: string) => void;
  onSubmit: () => void;
};

export function TokenEntryView({
  apiBaseUrl,
  handoffToken,
  connecting,
  errorMessage,
  noticeMessage,
  onApiBaseUrlChange,
  onHandoffTokenChange,
  onSubmit,
}: TokenEntryViewProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <main className="connect-shell">
      <section className="connect-card">
        <p className="eyebrow">Mini Editor Handoff</p>
        <h1>Subscription editor web shell</h1>
        <p className="lede">
          Paste a short-lived handoff token, or open this shell with a
          <code>#handoff_token=...</code> URL fragment. The token stays in memory only.
        </p>

        {noticeMessage ? <div className="inline-banner success">{noticeMessage}</div> : null}
        {errorMessage ? <div className="inline-banner error">{errorMessage}</div> : null}

        <form className="token-form" onSubmit={handleSubmit}>
          <label>
            API base URL
            <input
              autoComplete="off"
              name="api-base-url"
              value={apiBaseUrl}
              onChange={(event) => onApiBaseUrlChange(event.target.value)}
              placeholder="http://127.0.0.1:8000"
            />
          </label>
          <label>
            Handoff token
            <textarea
              name="handoff-token"
              rows={4}
              value={handoffToken}
              onChange={(event) => onHandoffTokenChange(event.target.value)}
              placeholder="Paste the plaintext handoff token from /mini/subscription-reserve/editor-handoff"
            />
          </label>
          <div className="button-row">
            <button disabled={connecting} type="submit">
              {connecting ? "Connecting..." : "Connect handoff token"}
            </button>
          </div>
        </form>

        <ul className="token-notes">
          <li>No token is stored in localStorage, sessionStorage, or cookies.</li>
          <li>This shell calls only the existing `/subscription-editor/*` APIs.</li>
          <li>Mini grants remain read-only; only handoff grants can enter the editor shell.</li>
        </ul>
      </section>
    </main>
  );
}
