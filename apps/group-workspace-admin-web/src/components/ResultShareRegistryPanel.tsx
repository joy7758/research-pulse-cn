import {
  parseResultShareRegistrySectionSortInput,
  RESULT_SHARE_REGISTRY_ALIAS_STATUS_OPTIONS,
  RESULT_SHARE_REGISTRY_GRANT_STATUS_OPTIONS,
  RESULT_SHARE_REGISTRY_SHARE_KIND_OPTIONS,
  RESULT_SHARE_REGISTRY_SORT_OPTIONS,
  serializeResultShareRegistrySectionSortInput,
} from "../lib/resultShareRegistryFilters";
import type {
  ApiErrorViewModel,
  ResultShareAliasRegistryItemViewModel,
  ResultShareGrantRegistryItemViewModel,
  ResultShareRegistryFilterInput,
  ResultShareRegistryFilterSummaryViewModel,
  ResultShareRegistrySortInput,
  ResultShareRegistrySummaryViewModel,
  ResultShareRegistryViewModel,
} from "../lib/types";

type ResultShareRegistryPanelProps = {
  filters: ResultShareRegistryFilterInput;
  sorts: ResultShareRegistrySortInput;
  filterSummary: ResultShareRegistryFilterSummaryViewModel;
  registry: ResultShareRegistryViewModel | null;
  currentTargetLabel: string | null;
  loading: boolean;
  error: ApiErrorViewModel | null;
  onFilterChange: (patch: Partial<ResultShareRegistryFilterInput>) => void;
  onSortChange: (patch: Partial<ResultShareRegistrySortInput>) => void;
  onApplyFilters: () => void;
  onResetFilters: () => void;
  onOpenGrantDrilldown: (grantId: string) => void;
  onOpenAliasDrilldown: (aliasId: string) => void;
  onFilterAliasesForGrant: (grantId: string, shareKind: ResultShareGrantRegistryItemViewModel["shareKind"]) => void;
};

function SummaryCardList({ items }: { items: ResultShareRegistrySummaryViewModel[] }) {
  return (
    <div className="stat-grid">
      {items.map((item) => (
        <article key={item.label} className="stat-card">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          {item.hint ? <p className="stat-hint">{item.hint}</p> : null}
        </article>
      ))}
    </div>
  );
}

function GrantRegistryList({
  items,
  emptyState,
  onOpenGrantDrilldown,
  onFilterAliasesForGrant,
}: {
  items: ResultShareGrantRegistryItemViewModel[];
  emptyState: ResultShareRegistryViewModel["grants"]["emptyState"];
  onOpenGrantDrilldown: (grantId: string) => void;
  onFilterAliasesForGrant: (grantId: string, shareKind: ResultShareGrantRegistryItemViewModel["shareKind"]) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong>{emptyState.title}</strong>
        <p>{emptyState.message}</p>
      </div>
    );
  }

  return (
    <ul className="data-list">
      {items.map((item) => (
        <li key={item.grantId} className="data-list-item">
          <div className="registry-item-stack">
            <div className="registry-item-header">
              <div>
                <strong>{item.title}</strong>
                <p>{item.subtitle}</p>
              </div>
              <span className={`status-pill ${item.status}`}>{item.status}</span>
            </div>
            <dl className="registry-meta-grid">
              <div className="metric-kv-item">
                <dt>Grant</dt>
                <dd>{item.grantId}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Share kind</dt>
                <dd>{item.shareKind}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Relation</dt>
                <dd>{item.relationshipHint}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Expires at</dt>
                <dd>{item.expiresAt ?? "No expiry"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Last used</dt>
                <dd>{item.lastUsedAt ?? "Never"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Created at</dt>
                <dd>{item.createdAt}</dd>
              </div>
            </dl>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenGrantDrilldown(item.grantId)}
            >
              Open grant drilldown
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => onFilterAliasesForGrant(item.grantId, item.shareKind)}
            >
              Show aliases for this grant
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function AliasRegistryList({
  items,
  emptyState,
  onOpenGrantDrilldown,
  onOpenAliasDrilldown,
}: {
  items: ResultShareAliasRegistryItemViewModel[];
  emptyState: ResultShareRegistryViewModel["aliases"]["emptyState"];
  onOpenGrantDrilldown: (grantId: string) => void;
  onOpenAliasDrilldown: (aliasId: string) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong>{emptyState.title}</strong>
        <p>{emptyState.message}</p>
      </div>
    );
  }

  return (
    <ul className="data-list">
      {items.map((item) => (
        <li key={item.aliasId} className="data-list-item">
          <div className="registry-item-stack">
            <div className="registry-item-header">
              <div>
                <strong>{item.title}</strong>
                <p>{item.subtitle}</p>
              </div>
              <span className={`status-pill ${item.status}`}>{item.status}</span>
            </div>
            <dl className="registry-meta-grid">
              <div className="metric-kv-item">
                <dt>Alias</dt>
                <dd>{item.aliasId}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Prefix</dt>
                <dd>{item.aliasPrefix ?? "Hidden"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Linked grant</dt>
                <dd>{item.relationshipHint}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Grant listed</dt>
                <dd>{item.linkedGrantInRegistry ? "Yes" : "Not in current grant rows"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Expires at</dt>
                <dd>{item.expiresAt ?? "No expiry"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Last used</dt>
                <dd>{item.lastUsedAt ?? "Never"}</dd>
              </div>
            </dl>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenAliasDrilldown(item.aliasId)}
            >
              Open alias drilldown
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenGrantDrilldown(item.grantId)}
            >
              Open linked grant
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ResultShareRegistryPanel({
  filters,
  sorts,
  filterSummary,
  registry,
  currentTargetLabel,
  loading,
  error,
  onFilterChange,
  onSortChange,
  onApplyFilters,
  onResetFilters,
  onOpenGrantDrilldown,
  onOpenAliasDrilldown,
  onFilterAliasesForGrant,
}: ResultShareRegistryPanelProps) {
  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <div>
          <p className="eyebrow">Per-share registry</p>
          <h2>Result share registry</h2>
          <p className="panel-copy">
            Browse safe share-grant and alias rows, then quick-open the existing read-only
            per-share drilldown without manual ID entry.
          </p>
        </div>
        {currentTargetLabel ? (
          <div className="hero-chip registry-current-target">
            <span>Current drilldown</span>
            <strong>{currentTargetLabel}</strong>
          </div>
        ) : null}
      </div>

      <div className="filter-grid">
        <label className="field-stack">
          <span>Share kind</span>
          <select
            value={filters.shareKind ?? ""}
            onChange={(event) =>
              onFilterChange({
                shareKind: event.target.value === "" ? null : (event.target.value as ResultShareRegistryFilterInput["shareKind"]),
              })
            }
          >
            <option value="">All share kinds</option>
            {RESULT_SHARE_REGISTRY_SHARE_KIND_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Grant status</span>
          <select
            value={filters.grantStatus ?? ""}
            onChange={(event) =>
              onFilterChange({
                grantStatus:
                  event.target.value === ""
                    ? null
                    : (event.target.value as ResultShareRegistryFilterInput["grantStatus"]),
              })
            }
          >
            <option value="">All grant statuses</option>
            {RESULT_SHARE_REGISTRY_GRANT_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Alias status</span>
          <select
            value={filters.aliasStatus ?? ""}
            onChange={(event) =>
              onFilterChange({
                aliasStatus:
                  event.target.value === ""
                    ? null
                    : (event.target.value as ResultShareRegistryFilterInput["aliasStatus"]),
              })
            }
          >
            <option value="">All alias statuses</option>
            {RESULT_SHARE_REGISTRY_ALIAS_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Workspace ID</span>
          <input
            type="text"
            placeholder="grant registry only"
            value={filters.workspaceId ?? ""}
            onChange={(event) => onFilterChange({ workspaceId: event.target.value })}
          />
        </label>

        <label className="field-stack">
          <span>Grant ID</span>
          <input
            type="text"
            placeholder="alias registry only"
            value={filters.resultShareGrantId ?? ""}
            onChange={(event) => onFilterChange({ resultShareGrantId: event.target.value })}
          />
        </label>

        <label className="field-stack">
          <span>Grant sort</span>
          <select
            value={serializeResultShareRegistrySectionSortInput(sorts.grants)}
            onChange={(event) =>
              onSortChange({
                grants: parseResultShareRegistrySectionSortInput(event.target.value),
              })
            }
          >
            {RESULT_SHARE_REGISTRY_SORT_OPTIONS.map((option) => (
              <option key={`grant-${option.key}`} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Alias sort</span>
          <select
            value={serializeResultShareRegistrySectionSortInput(sorts.aliases)}
            onChange={(event) =>
              onSortChange({
                aliases: parseResultShareRegistrySectionSortInput(event.target.value),
              })
            }
          >
            {RESULT_SHARE_REGISTRY_SORT_OPTIONS.map((option) => (
              <option key={`alias-${option.key}`} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="button-row">
        <button type="button" className="button-primary" disabled={loading} onClick={onApplyFilters}>
          {loading ? "Loading..." : "Apply filters"}
        </button>
        <button type="button" className="button-secondary" disabled={loading} onClick={onResetFilters}>
          Reset defaults
        </button>
      </div>

      <section className="filter-summary-card">
        <div className="conversion-section-header">
          <h3>Applied registry filters and sort</h3>
          <p className="section-subtle-copy">
            Grant-only and alias-only filters stay explicit, while each registry keeps its own stable sort mode.
          </p>
        </div>
        {filterSummary.chips.length > 0 ? (
          <ul className="filter-chip-list">
            {filterSummary.chips.map((chip) => (
              <li key={chip.key} className="filter-chip">
                <span>{chip.label}</span>
                <strong>{chip.value}</strong>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">No registry filters are active.</div>
        )}
        <ul className="note-list">
          {filterSummary.scopeNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>

      {error ? (
        <div className="inline-banner error" role="alert">
          <strong>{error.title}</strong>
          <span>{error.message}</span>
        </div>
      ) : null}

      {loading && registry === null ? (
        <div className="empty-state">Loading read-only share registries...</div>
      ) : null}

      {registry ? (
        <div className="split-grid">
          <section className="conversion-section-card">
            <div className="conversion-section-header">
              <h3>{registry.grants.title}</h3>
              <p className="section-subtle-copy">{registry.grants.description}</p>
            </div>
            <SummaryCardList items={registry.grants.summaryMetrics} />
            <GrantRegistryList
              items={registry.grants.items}
              emptyState={registry.grants.emptyState}
              onOpenGrantDrilldown={onOpenGrantDrilldown}
              onFilterAliasesForGrant={onFilterAliasesForGrant}
            />
          </section>

          <section className="conversion-section-card">
            <div className="conversion-section-header">
              <h3>{registry.aliases.title}</h3>
              <p className="section-subtle-copy">{registry.aliases.description}</p>
            </div>
            <SummaryCardList items={registry.aliases.summaryMetrics} />
            <AliasRegistryList
              items={registry.aliases.items}
              emptyState={registry.aliases.emptyState}
              onOpenGrantDrilldown={onOpenGrantDrilldown}
              onOpenAliasDrilldown={onOpenAliasDrilldown}
            />
          </section>
        </div>
      ) : null}
    </section>
  );
}
