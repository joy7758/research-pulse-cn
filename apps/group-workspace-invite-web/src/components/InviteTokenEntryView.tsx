type InviteTokenEntryViewProps = {
  apiBaseUrl: string;
  inviteToken: string;
  loading: boolean;
  errorTitle: string | null;
  errorMessage: string | null;
  noticeMessage: string | null;
  onApiBaseUrlChange: (value: string) => void;
  onInviteTokenChange: (value: string) => void;
  onSubmit: () => void;
};

export function InviteTokenEntryView({
  apiBaseUrl,
  inviteToken,
  loading,
  errorTitle,
  errorMessage,
  noticeMessage,
  onApiBaseUrlChange,
  onInviteTokenChange,
  onSubmit,
}: InviteTokenEntryViewProps) {
  return (
    <main className="connect-shell">
      <section className="connect-card">
        <p className="eyebrow">Workspace Invite</p>
        <h1>Open a safe workspace invite</h1>
        <p className="lede">
          This shell only previews a safe workspace summary and uses the existing self-service
          claim boundary. It does not expose source files, local attachments, or note contents.
        </p>

        <div className="banner-row">
          {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
          {errorTitle && errorMessage ? (
            <div className="inline-banner danger" role="alert">
              <strong>{errorTitle}</strong>
              <span>{errorMessage}</span>
            </div>
          ) : null}
        </div>

        <div className="token-form">
          <label>
            API base URL
            <input
              autoComplete="off"
              inputMode="url"
              onChange={(event) => onApiBaseUrlChange(event.target.value)}
              placeholder="http://127.0.0.1:8000"
              spellCheck={false}
              type="text"
              value={apiBaseUrl}
            />
          </label>
          <label>
            Invite token
            <input
              autoComplete="off"
              onChange={(event) => onInviteTokenChange(event.target.value)}
              placeholder="Paste invite token or open /invite/<token>"
              spellCheck={false}
              type="text"
              value={inviteToken}
            />
          </label>
        </div>

        <div className="action-row">
          <button disabled={loading} onClick={onSubmit} type="button">
            {loading ? "Opening invite..." : "Open invite"}
          </button>
        </div>
      </section>
    </main>
  );
}
