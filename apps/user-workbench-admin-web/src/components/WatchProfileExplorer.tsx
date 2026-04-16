import type {
  UserWorkbenchWatchProfileCardViewModel,
  UserWorkbenchWatchProfilesQuery,
} from "../lib/types";

type WatchProfileExplorerProps = {
  filters: UserWorkbenchWatchProfilesQuery;
  items: UserWorkbenchWatchProfileCardViewModel[];
  loading: boolean;
  onFiltersChange: (patch: Partial<UserWorkbenchWatchProfilesQuery>) => void;
  onSearch: () => void;
  onOpenUser: (userId: string) => void;
  onOpenPaper: (paperId: string) => void;
};

export function WatchProfileExplorer({
  filters,
  items,
  loading,
  onFiltersChange,
  onSearch,
  onOpenUser,
  onOpenPaper,
}: WatchProfileExplorerProps) {
  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <div>
          <p className="eyebrow">Watch profiles</p>
          <h2>Read-only watch profile explorer</h2>
        </div>
      </div>
      <div className="field-grid">
        <label className="field-stack">
          <span>Query</span>
          <input
            type="text"
            value={filters.q ?? ""}
            onChange={(event) => onFiltersChange({ q: event.target.value || undefined })}
            placeholder="watch label / topic / paper title"
          />
        </label>
        <label className="field-stack">
          <span>User ID</span>
          <input
            type="text"
            value={filters.userId ?? ""}
            onChange={(event) => onFiltersChange({ userId: event.target.value || undefined })}
            placeholder="Optional user_id"
          />
        </label>
        <label className="field-stack">
          <span>Paper ID</span>
          <input
            type="text"
            value={filters.paperId ?? ""}
            onChange={(event) => onFiltersChange({ paperId: event.target.value || undefined })}
            placeholder="Optional paper_id"
          />
        </label>
        <label className="field-stack">
          <span>Enabled</span>
          <select
            value={filters.enabled === undefined ? "" : String(filters.enabled)}
            onChange={(event) =>
              onFiltersChange({
                enabled:
                  event.target.value === ""
                    ? undefined
                    : event.target.value === "true",
              })
            }
          >
            <option value="">Any</option>
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>
        </label>
      </div>
      <div className="button-row">
        <button type="button" className="button-primary" disabled={loading} onClick={onSearch}>
          {loading ? "Loading..." : "Search watch profiles"}
        </button>
      </div>
      {items.length === 0 ? (
        <div className="empty-state">No watch profiles matched the current filters.</div>
      ) : (
        <ul className="data-list">
          {items.map((item) => (
            <li key={item.id} className="data-list-item multi">
              <div>
                <strong>{item.title}</strong>
                {item.subtitle ? <p>{item.subtitle}</p> : null}
                {item.userLabel ? <small>{item.userLabel}</small> : null}
                {item.paperLabel ? <small>{item.paperLabel}</small> : null}
              </div>
              <div className="button-row compact">
                {item.userLabel ? (
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => onOpenUser(item.userId)}
                  >
                    User
                  </button>
                ) : null}
                {item.paperLabel && item.paperId ? (
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => onOpenPaper(item.paperId!)}
                  >
                    Paper
                  </button>
                ) : null}
                <span className={item.enabled ? "status-pill ready" : "status-pill archived"}>
                  {item.enabled ? "enabled" : "disabled"}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
