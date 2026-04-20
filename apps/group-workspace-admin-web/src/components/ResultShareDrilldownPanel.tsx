import type { ReactNode } from "react";

import { ConversionFilterBar } from "./ConversionFilterBar";
import type {
  ApiErrorViewModel,
  ConversionFilterInput,
  ConversionFilterSummaryViewModel,
  ConversionFilterSupportViewModel,
  ConversionMetricBucketViewModel,
  ResultShareAliasDrilldownViewModel,
  ResultShareDirectCollectRecordViewModel,
  ResultShareGrantDrilldownViewModel,
  ResultShareRecentEventViewModel,
} from "../lib/types";

type ResultShareDrilldownPanelProps = {
  grantLookupId: string;
  aliasLookupId: string;
  currentTargetLabel: string | null;
  drilldownContextLabel: string;
  filters: ConversionFilterInput;
  filterSummary: ConversionFilterSummaryViewModel;
  filterSupport: ConversionFilterSupportViewModel;
  filterDisabled: boolean;
  grantDrilldown: ResultShareGrantDrilldownViewModel | null;
  aliasDrilldown: ResultShareAliasDrilldownViewModel | null;
  loading: boolean;
  error: ApiErrorViewModel | null;
  onGrantLookupIdChange: (value: string) => void;
  onAliasLookupIdChange: (value: string) => void;
  onOpenGrantDrilldown: () => void;
  onOpenAliasDrilldown: () => void;
  onClearDrilldown: () => void;
  onFilterChange: (patch: Partial<ConversionFilterInput>) => void;
  onApplyFilters: () => void;
  onResetFilters: () => void;
  onOpenAliasFromGrant: (aliasId: string) => void;
  onOpenGrantFromAlias: (grantId: string) => void;
};

type RecentActivityItem = ResultShareRecentEventViewModel | ResultShareDirectCollectRecordViewModel;

function renderTimestampRange(windowStart: string | null, windowEnd: string | null): string {
  if (!windowStart && !windowEnd) {
    return "Default analytics window";
  }
  if (windowStart && windowEnd) {
    return `${windowStart} → ${windowEnd}`;
  }
  if (windowStart) {
    return `${windowStart} → now`;
  }
  return `Until ${windowEnd}`;
}

function MetricRows({
  rows,
  emptyLabel,
}: {
  rows: ConversionMetricBucketViewModel[];
  emptyLabel: string;
}) {
  if (rows.length === 0) {
    return <div className="empty-state">{emptyLabel}</div>;
  }

  return (
    <dl className="metric-kv-list">
      {rows.map((row) => (
        <div key={row.key} className="metric-kv-item">
          <dt>{row.label}</dt>
          <dd>{row.count}</dd>
        </div>
      ))}
    </dl>
  );
}

function ActivityList({
  rows,
  emptyLabel,
}: {
  rows: RecentActivityItem[];
  emptyLabel: string;
}) {
  if (rows.length === 0) {
    return <div className="empty-state">{emptyLabel}</div>;
  }

  return (
    <ul className="activity-list">
      {rows.map((row) => (
        <li key={row.id} className="activity-card">
          <div className="activity-card-header">
            <div>
              <strong>{row.title}</strong>
              <p>{row.subtitle}</p>
            </div>
            <div className="ranked-item-time">
              <span>Occurred at</span>
              <strong>{row.occurredAt}</strong>
            </div>
          </div>
          <dl className="detail-row-grid">
            {row.detailRows.map((detailRow) => (
              <div key={`${row.id}-${detailRow.label}`} className="metric-kv-item">
                <dt>{detailRow.label}</dt>
                <dd>{detailRow.value}</dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function SummaryBlock({
  title,
  rows,
  action,
}: {
  title: string;
  rows: Array<{ label: string; value: string }>;
  action?: ReactNode;
}) {
  return (
    <section className="conversion-section-card">
      <div className="conversion-section-header">
        <h3>{title}</h3>
        {action}
      </div>
      <dl className="detail-row-grid">
        {rows.map((row) => (
          <div key={`${title}-${row.label}`} className="metric-kv-item">
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function AliasListSection({
  rows,
  onOpenAlias,
}: {
  rows: ResultShareGrantDrilldownViewModel["aliases"];
  onOpenAlias: (aliasId: string) => void;
}) {
  if (rows.length === 0) {
    return <div className="empty-state">No aliases are attached to this share grant.</div>;
  }

  return (
    <ul className="data-list">
      {rows.map((row) => (
        <li key={row.aliasId} className="data-list-item">
          <div>
            <strong>{row.title}</strong>
            <p>{row.subtitle}</p>
            <p>
              Prefix {row.aliasPrefix ?? "Hidden"} · last used {row.lastUsedAt ?? "Never"}
            </p>
          </div>
          <button
            type="button"
            className="button-secondary"
            onClick={() => onOpenAlias(row.aliasId)}
          >
            Open alias drilldown
          </button>
        </li>
      ))}
    </ul>
  );
}

function AttributionScopeSection({
  scope,
  notes,
}: {
  scope:
    | ResultShareGrantDrilldownViewModel["attributionScope"]
    | ResultShareAliasDrilldownViewModel["attributionScope"];
  notes: string[];
}) {
  return (
    <section className="conversion-section-card">
      <div className="conversion-section-header">
        <h3>Attribution scope</h3>
        <p className="section-subtle-copy">
          Direct event metrics, direct collect linkage, and non-attribution context stay separate.
        </p>
      </div>
      <div className="attribution-grid">
        <div className="attribution-block">
          <strong>Direct event metrics</strong>
          <ul className="note-list">
            {scope.directEventMetrics.length > 0 ? (
              scope.directEventMetrics.map((metric) => <li key={metric}>{metric}</li>)
            ) : (
              <li>No direct event metrics were returned.</li>
            )}
          </ul>
        </div>
        <div className="attribution-block">
          <strong>Direct collect linkage</strong>
          <ul className="note-list">
            {scope.directCollectMetrics.length > 0 ? (
              scope.directCollectMetrics.map((metric) => <li key={metric}>{metric}</li>)
            ) : (
              <li>No direct collect linkage was returned.</li>
            )}
          </ul>
        </div>
        <div className="attribution-block">
          <strong>Non-attribution context</strong>
          <ul className="note-list">
            {scope.nonAttributionFields.map((metric) => (
              <li key={metric}>{metric}</li>
            ))}
          </ul>
        </div>
      </div>
      <ul className="note-list">
        {scope.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
        {notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

function GrantDrilldownContent({
  viewModel,
  onOpenAlias,
}: {
  viewModel: ResultShareGrantDrilldownViewModel;
  onOpenAlias: (aliasId: string) => void;
}) {
  return (
    <section className="panel-card conversion-panel">
      <div className="panel-card-header">
        <div>
          <p className="eyebrow">Per-share grant drilldown</p>
          <h2>{viewModel.shareGrant.title}</h2>
          <p className="panel-copy">
            Direct share-event counts and direct collect linkage for one share grant only.
          </p>
        </div>
        <span className={`status-pill ${viewModel.shareGrant.status}`}>
          {viewModel.shareGrant.status}
        </span>
      </div>

      <div className="conversion-meta-row">
        <div className="meta-chip">
          <span>Window</span>
          <strong>{renderTimestampRange(viewModel.windowStart, viewModel.windowEnd)}</strong>
        </div>
        <div className="meta-chip">
          <span>Last activity</span>
          <strong>{viewModel.lastActivityAt ?? "No activity yet"}</strong>
        </div>
      </div>

      {viewModel.empty ? (
        <div className="empty-state">
          No events, aliases, or direct collect records were returned for this share grant.
        </div>
      ) : null}

      {!viewModel.empty ? (
        <>
          <div className="stat-grid conversion-stat-grid">
            {viewModel.summaryMetrics.map((metric) => (
              <article key={metric.label} className="stat-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                {metric.hint ? <p className="stat-hint">{metric.hint}</p> : null}
              </article>
            ))}
          </div>

          <div className="conversion-section-grid">
            <SummaryBlock
              title="Share grant summary"
              rows={[
                { label: "Grant", value: viewModel.shareGrant.grantId },
                { label: "Share kind", value: viewModel.shareGrant.shareKind },
                { label: "Display label", value: viewModel.shareGrant.displayLabel ?? "None" },
                { label: "Expires at", value: viewModel.shareGrant.expiresAt ?? "No expiry" },
                { label: "Last used", value: viewModel.shareGrant.lastUsedAt ?? "Never" },
                { label: "Created at", value: viewModel.shareGrant.createdAt },
              ]}
            />

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>By access mode</h3>
                <p className="section-subtle-copy">Direct event counts grouped by access path.</p>
              </div>
              <MetricRows
                rows={viewModel.byAccessModeRows}
                emptyLabel="No access-mode counts were returned."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>By event type</h3>
                <p className="section-subtle-copy">Direct event counts grouped by event type.</p>
              </div>
              <MetricRows
                rows={viewModel.byEventTypeRows}
                emptyLabel="No event-type counts were returned."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>By outcome</h3>
                <p className="section-subtle-copy">Resolved and rejected rows for this grant.</p>
              </div>
              <MetricRows
                rows={viewModel.byOutcomeRows}
                emptyLabel="No outcome counts were returned."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Aliases</h3>
                <p className="section-subtle-copy">
                  Safe alias summaries linked to this grant. Alias rows stay read-only.
                </p>
              </div>
              <AliasListSection rows={viewModel.aliases} onOpenAlias={onOpenAlias} />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Recent events</h3>
                <p className="section-subtle-copy">
                  Most recent persisted share events linked to this grant.
                </p>
              </div>
              <ActivityList
                rows={viewModel.recentEvents}
                emptyLabel="No recent events were returned for this grant."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Direct collect records</h3>
                <p className="section-subtle-copy">
                  Grant-linked collect outcomes only. This section does not infer alias-level
                  collect attribution.
                </p>
              </div>
              <ActivityList
                rows={viewModel.directCollectRecords}
                emptyLabel="No direct collect records were returned for this grant."
              />
            </section>

            <AttributionScopeSection scope={viewModel.attributionScope} notes={viewModel.notes} />
          </div>
        </>
      ) : null}
    </section>
  );
}

function AliasDrilldownContent({
  viewModel,
  onOpenGrant,
}: {
  viewModel: ResultShareAliasDrilldownViewModel;
  onOpenGrant: (grantId: string) => void;
}) {
  return (
    <section className="panel-card conversion-panel">
      <div className="panel-card-header">
        <div>
          <p className="eyebrow">Per-share alias drilldown</p>
          <h2>{viewModel.alias.title}</h2>
          <p className="panel-copy">
            Alias-scoped access behavior only. Grant-level collect linkage remains separate.
          </p>
        </div>
        <span className={`status-pill ${viewModel.alias.status}`}>{viewModel.alias.status}</span>
      </div>

      <div className="conversion-meta-row">
        <div className="meta-chip">
          <span>Window</span>
          <strong>{renderTimestampRange(viewModel.windowStart, viewModel.windowEnd)}</strong>
        </div>
        <div className="meta-chip">
          <span>Last activity</span>
          <strong>{viewModel.lastActivityAt ?? "No activity yet"}</strong>
        </div>
      </div>

      {viewModel.empty ? (
        <div className="empty-state">No alias-scoped events were returned for this alias.</div>
      ) : null}

      {!viewModel.empty ? (
        <>
          <div className="stat-grid conversion-stat-grid">
            {viewModel.summaryMetrics.map((metric) => (
              <article key={metric.label} className="stat-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                {metric.hint ? <p className="stat-hint">{metric.hint}</p> : null}
              </article>
            ))}
          </div>

          <div className="conversion-section-grid">
            <SummaryBlock
              title="Alias summary"
              rows={[
                { label: "Alias", value: viewModel.alias.aliasId },
                { label: "Prefix", value: viewModel.alias.aliasPrefix ?? "Hidden" },
                { label: "Share kind", value: viewModel.alias.shareKind },
                { label: "Display label", value: viewModel.alias.displayLabel ?? "None" },
                { label: "Expires at", value: viewModel.alias.expiresAt ?? "No expiry" },
                { label: "Last used", value: viewModel.alias.lastUsedAt ?? "Never" },
                { label: "Created at", value: viewModel.alias.createdAt },
              ]}
            />

            <SummaryBlock
              title="Underlying grant summary"
              rows={[
                { label: "Grant", value: viewModel.resultShareGrant.grantId },
                { label: "Share kind", value: viewModel.resultShareGrant.shareKind },
                {
                  label: "Display label",
                  value: viewModel.resultShareGrant.displayLabel ?? "None",
                },
                {
                  label: "Expires at",
                  value: viewModel.resultShareGrant.expiresAt ?? "No expiry",
                },
                {
                  label: "Last used",
                  value: viewModel.resultShareGrant.lastUsedAt ?? "Never",
                },
              ]}
              action={
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onOpenGrant(viewModel.resultShareGrant.grantId)}
                >
                  Open grant drilldown
                </button>
              }
            />

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>By event type</h3>
                <p className="section-subtle-copy">Alias-scoped event counts only.</p>
              </div>
              <MetricRows
                rows={viewModel.byEventTypeRows}
                emptyLabel="No event-type counts were returned for this alias."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>By outcome</h3>
                <p className="section-subtle-copy">Resolved and rejected alias rows only.</p>
              </div>
              <MetricRows
                rows={viewModel.byOutcomeRows}
                emptyLabel="No outcome counts were returned for this alias."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Recent events</h3>
                <p className="section-subtle-copy">
                  Access-path behavior for this alias only. Collect linkage is not inferred here.
                </p>
              </div>
              <ActivityList
                rows={viewModel.recentEvents}
                emptyLabel="No recent alias events were returned."
              />
            </section>

            <AttributionScopeSection scope={viewModel.attributionScope} notes={viewModel.notes} />
          </div>
        </>
      ) : null}
    </section>
  );
}

export function ResultShareDrilldownPanel({
  grantLookupId,
  aliasLookupId,
  currentTargetLabel,
  drilldownContextLabel,
  filters,
  filterSummary,
  filterSupport,
  filterDisabled,
  grantDrilldown,
  aliasDrilldown,
  loading,
  error,
  onGrantLookupIdChange,
  onAliasLookupIdChange,
  onOpenGrantDrilldown,
  onOpenAliasDrilldown,
  onClearDrilldown,
  onFilterChange,
  onApplyFilters,
  onResetFilters,
  onOpenAliasFromGrant,
  onOpenGrantFromAlias,
}: ResultShareDrilldownPanelProps) {
  const hasSelection = currentTargetLabel !== null;

  return (
    <>
      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Per-share dashboard</p>
            <h2>Share grant and alias drilldown</h2>
            <p className="panel-copy">
              Open one share grant or alias at a time to inspect direct event counts and, for
              grants only, direct collect linkage.
            </p>
          </div>
        </div>

        <div className="conversion-meta-row">
          <div className="meta-chip">
            <span>Current view</span>
            <strong>{currentTargetLabel ?? "No share selected"}</strong>
          </div>
          <div className="meta-chip">
            <span>Filter context</span>
            <strong>{drilldownContextLabel}</strong>
          </div>
        </div>

        <div className="field-grid">
          <label className="field-stack">
            <span>Share grant id</span>
            <input
              type="text"
              value={grantLookupId}
              onChange={(event) => onGrantLookupIdChange(event.target.value)}
              placeholder="Paste a result-share grant id"
            />
          </label>
          <label className="field-stack">
            <span>Alias id</span>
            <input
              type="text"
              value={aliasLookupId}
              onChange={(event) => onAliasLookupIdChange(event.target.value)}
              placeholder="Paste a result-share alias id"
            />
          </label>
        </div>

        <div className="button-row">
          <button
            type="button"
            className="button-primary"
            disabled={loading || grantLookupId.trim().length === 0}
            onClick={onOpenGrantDrilldown}
          >
            Open share grant drilldown
          </button>
          <button
            type="button"
            className="button-secondary"
            disabled={loading || aliasLookupId.trim().length === 0}
            onClick={onOpenAliasDrilldown}
          >
            Open alias drilldown
          </button>
          <button
            type="button"
            className="button-secondary"
            disabled={loading || !hasSelection}
            onClick={onClearDrilldown}
          >
            Clear per-share view
          </button>
        </div>
      </section>

      <ConversionFilterBar
        eyebrow="Per-share filters"
        title="Per-share drilldown filters"
        description="Read-only filters for the current grant or alias drilldown. Share kind stays fixed by the selected target."
        filters={filters}
        support={filterSupport}
        summary={filterSummary}
        disabled={filterDisabled || !hasSelection}
        onChange={onFilterChange}
        onApply={onApplyFilters}
        onReset={onResetFilters}
      />

      {error ? (
        <div className="inline-banner error" role="alert">
          <strong>{error.title}</strong>
          <span>{error.message}</span>
        </div>
      ) : null}

      {loading ? <div className="panel-card empty-state">Loading per-share drilldown...</div> : null}

      {!loading && !error && !hasSelection ? (
        <section className="panel-card">
          <div className="empty-state large">
            Open a share grant or alias to inspect its read-only drilldown dashboard.
          </div>
        </section>
      ) : null}

      {!loading && !error && grantDrilldown ? (
        <GrantDrilldownContent
          viewModel={grantDrilldown}
          onOpenAlias={onOpenAliasFromGrant}
        />
      ) : null}

      {!loading && !error && aliasDrilldown ? (
        <AliasDrilldownContent
          viewModel={aliasDrilldown}
          onOpenGrant={onOpenGrantFromAlias}
        />
      ) : null}
    </>
  );
}
