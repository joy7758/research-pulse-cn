type TokenEntryViewProps = {
  apiBaseUrl: string;
  adminToken: string;
  loading: boolean;
  errorTitle: string | null;
  errorMessage: string | null;
  noticeMessage: string | null;
  onApiBaseUrlChange: (value: string) => void;
  onAdminTokenChange: (value: string) => void;
  onSubmit: () => void;
};

export function TokenEntryView({
  apiBaseUrl,
  adminToken,
  loading,
  errorTitle,
  errorMessage,
  noticeMessage,
  onApiBaseUrlChange,
  onAdminTokenChange,
  onSubmit,
}: TokenEntryViewProps) {
  return (
    <main className="connect-shell">
      <section className="connect-card">
        <p className="eyebrow">Internal Admin Shell</p>
        <h1>Manage group workspaces and workspace-board shares</h1>
        <p className="lede">
          Paste an admin/operator bearer token to manage workspaces, members, papers, and
          workspace-board share grants. Tokens stay in memory only.
        </p>

        {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
        {errorTitle && errorMessage ? (
          <div className="inline-banner error" role="alert">
            <strong>{errorTitle}</strong>
            <span>{errorMessage}</span>
          </div>
        ) : null}

        <label className="field-stack">
          <span>API base URL</span>
          <input
            type="text"
            value={apiBaseUrl}
            onChange={(event) => onApiBaseUrlChange(event.target.value)}
            placeholder="http://127.0.0.1:8000"
          />
        </label>

        <label className="field-stack">
          <span>Admin bearer token</span>
          <textarea
            value={adminToken}
            onChange={(event) => onAdminTokenChange(event.target.value)}
            rows={6}
            placeholder="Paste the bearer token from POST /auth/login"
          />
        </label>

        <div className="button-row">
          <button type="button" className="button-primary" disabled={loading} onClick={onSubmit}>
            {loading ? "Connecting..." : "Open workspace shell"}
          </button>
        </div>
      </section>
    </main>
  );
}
