type TokenEntryViewProps = {
  apiBaseUrl: string;
  adminToken: string;
  loading: boolean;
  onApiBaseUrlChange: (value: string) => void;
  onAdminTokenChange: (value: string) => void;
  onConnect: () => void;
};

export function TokenEntryView({
  apiBaseUrl,
  adminToken,
  loading,
  onApiBaseUrlChange,
  onAdminTokenChange,
  onConnect,
}: TokenEntryViewProps) {
  return (
    <div className="connect-shell">
      <section className="connect-card">
        <p className="eyebrow">Internal admin shell</p>
        <h1>Open the read-only user workbench</h1>
        <p className="lede">
          Search users, inspect papers, and trace research watch profiles without exposing file-level
          data or creating a new login system.
        </p>
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
            placeholder="Paste a viewer/operator/super_admin bearer token"
            rows={4}
          />
        </label>
        <div className="button-row">
          <button type="button" className="button-primary" disabled={loading} onClick={onConnect}>
            {loading ? "Opening..." : "Open workbench"}
          </button>
        </div>
      </section>
    </div>
  );
}
