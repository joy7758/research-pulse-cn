import type { UserWorkbenchUserCardViewModel } from "../lib/types";

type UserListPanelProps = {
  search: string;
  items: UserWorkbenchUserCardViewModel[];
  selectedUserId: string | null;
  loading: boolean;
  onSearchChange: (value: string) => void;
  onSearchSubmit: () => void;
  onSelect: (userId: string) => void;
  onOpenPapers: () => void;
  onOpenWatchProfiles: () => void;
};

export function UserListPanel({
  search,
  items,
  selectedUserId,
  loading,
  onSearchChange,
  onSearchSubmit,
  onSelect,
  onOpenPapers,
  onOpenWatchProfiles,
}: UserListPanelProps) {
  return (
    <aside className="workbench-sidebar">
      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Users</p>
            <h2>User search</h2>
          </div>
          <div className="button-row compact">
            <button type="button" className="button-secondary" onClick={onOpenPapers}>
              Browse papers
            </button>
            <button type="button" className="button-secondary" onClick={onOpenWatchProfiles}>
              Browse watch profiles
            </button>
          </div>
        </div>
        <div className="field-grid single">
          <label className="field-stack">
            <span>Search by name, email, or field</span>
            <input
              type="text"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="materials / user@example.com"
            />
          </label>
        </div>
        <div className="button-row">
          <button type="button" className="button-primary" disabled={loading} onClick={onSearchSubmit}>
            {loading ? "Searching..." : "Search users"}
          </button>
        </div>
        {items.length === 0 ? (
          <div className="empty-state">No users matched the current search.</div>
        ) : (
          <ul className="user-list">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={item.id === selectedUserId ? "user-card active" : "user-card"}
                  onClick={() => onSelect(item.id)}
                >
                  <div className="user-card-header">
                    <strong>{item.title}</strong>
                    {item.latestDigestTitle ? <span className="status-pill ready">digest</span> : null}
                  </div>
                  {item.subtitle ? <p>{item.subtitle}</p> : null}
                  <div className="meta-row">
                    <span>{item.paperCount} papers</span>
                    <span>{item.watchProfileCount} watch profiles</span>
                    <span>{item.workspaceCount} workspaces</span>
                  </div>
                  {item.latestDigestTitle ? <small>Latest digest: {item.latestDigestTitle}</small> : null}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}
