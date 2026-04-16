import type {
  UserWorkbenchPaperCardViewModel,
  UserWorkbenchPaperDetailRead,
} from "../lib/types";

type PaperDetailViewProps = {
  search: string;
  stage: string;
  typeFilter: string;
  userIdFilter: string;
  listItems: UserWorkbenchPaperCardViewModel[];
  detail: UserWorkbenchPaperDetailRead | null;
  loading: boolean;
  onSearchChange: (value: string) => void;
  onStageChange: (value: string) => void;
  onTypeChange: (value: string) => void;
  onUserIdFilterChange: (value: string) => void;
  onSearchSubmit: () => void;
  onSelectPaper: (paperId: string) => void;
  onOpenWatchProfilesForPaper: (paperId: string) => void;
};

export function PaperDetailView({
  search,
  stage,
  typeFilter,
  userIdFilter,
  listItems,
  detail,
  loading,
  onSearchChange,
  onStageChange,
  onTypeChange,
  onUserIdFilterChange,
  onSearchSubmit,
  onSelectPaper,
  onOpenWatchProfilesForPaper,
}: PaperDetailViewProps) {
  return (
    <section className="detail-root">
      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Paper explorer</p>
            <h2>Paper search</h2>
          </div>
        </div>
        <div className="field-grid">
          <label className="field-stack">
            <span>Search</span>
            <input
              type="text"
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="paper title / venue / owner"
            />
          </label>
          <label className="field-stack">
            <span>User ID filter</span>
            <input
              type="text"
              value={userIdFilter}
              onChange={(event) => onUserIdFilterChange(event.target.value)}
              placeholder="Optional user_id"
            />
          </label>
          <label className="field-stack">
            <span>Stage</span>
            <input
              type="text"
              value={stage}
              onChange={(event) => onStageChange(event.target.value)}
              placeholder="published / draft"
            />
          </label>
          <label className="field-stack">
            <span>Type</span>
            <input
              type="text"
              value={typeFilter}
              onChange={(event) => onTypeChange(event.target.value)}
              placeholder="published / revision"
            />
          </label>
        </div>
        <div className="button-row">
          <button type="button" className="button-primary" disabled={loading} onClick={onSearchSubmit}>
            {loading ? "Loading..." : "Search papers"}
          </button>
        </div>
        {listItems.length === 0 ? (
          <div className="empty-state">No papers matched the current filters.</div>
        ) : (
          <ul className="data-list">
            {listItems.map((item) => (
              <li key={item.id} className="data-list-item">
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.subtitle}</p>
                  {item.ownerLabel ? <small>{item.ownerLabel}</small> : null}
                </div>
                <button type="button" className="button-secondary" onClick={() => onSelectPaper(item.id)}>
                  Open detail
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel-card">
        {detail ? (
          <>
            <div className="panel-card-header">
              <div>
                <p className="eyebrow">Paper detail</p>
                <h2>{detail.paper.title}</h2>
              </div>
              <button
                type="button"
                className="button-secondary"
                onClick={() => onOpenWatchProfilesForPaper(detail.paper.id)}
              >
                View watch profiles
              </button>
            </div>
            <div className="stat-grid">
              <article className="stat-card">
                <span>Owner</span>
                <strong>{detail.owner.email ?? detail.owner.name}</strong>
              </article>
              <article className="stat-card">
                <span>Stage</span>
                <strong>{detail.paper.stage}</strong>
              </article>
              <article className="stat-card">
                <span>Priority</span>
                <strong>{detail.paper.priority}</strong>
              </article>
              <article className="stat-card">
                <span>Progress</span>
                <strong>{detail.paper.progress_percentage}%</strong>
              </article>
            </div>
            {detail.paper.next_action ? (
              <div className="info-block">
                <strong>Next action</strong>
                <p>{detail.paper.next_action}</p>
              </div>
            ) : null}
            {detail.linked_watch_profiles.length === 0 ? (
              <div className="empty-state">No linked watch profiles for this paper.</div>
            ) : (
              <ul className="data-list">
                {detail.linked_watch_profiles.map((profile) => (
                  <li key={profile.id} className="data-list-item">
                    <div>
                      <strong>{profile.label}</strong>
                      <p>
                        {profile.source_mode}
                        {profile.user_email ? ` · ${profile.user_email}` : ""}
                      </p>
                    </div>
                    <span className={profile.enabled ? "status-pill ready" : "status-pill archived"}>
                      {profile.enabled ? "enabled" : "disabled"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <div className="empty-state large">
            {loading ? "Loading paper detail..." : "Select a paper to inspect its safe detail and linked watch profiles."}
          </div>
        )}
      </section>
    </section>
  );
}
