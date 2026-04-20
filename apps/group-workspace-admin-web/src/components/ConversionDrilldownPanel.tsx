import type {
  ApiErrorViewModel,
  ConversionDailyBucketViewModel,
  ConversionMetricBucketViewModel,
  ConversionRecentCollectRecordViewModel,
  ConversionRecentInviteClaimViewModel,
  ConversionRecentShareEventViewModel,
  ConversionSummaryMetricViewModel,
  ConversionTopResultShareGrantViewModel,
  ConversionTopWorkspaceViewModel,
  DrilldownAttributionScopeViewModel,
} from "../lib/types";

type RecentActivityItem =
  | ConversionRecentShareEventViewModel
  | ConversionRecentInviteClaimViewModel
  | ConversionRecentCollectRecordViewModel;

type RankedMetricItem = ConversionTopWorkspaceViewModel | ConversionTopResultShareGrantViewModel;

type ConversionDrilldownPanelProps = {
  eyebrow: string;
  title: string;
  description: string;
  summaryMetrics: ConversionSummaryMetricViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  dailyBuckets: ConversionDailyBucketViewModel[];
  topWorkspaces?: ConversionTopWorkspaceViewModel[];
  topResultShareGrants?: ConversionTopResultShareGrantViewModel[];
  recentShareEvents: ConversionRecentShareEventViewModel[];
  recentInviteClaims: ConversionRecentInviteClaimViewModel[];
  recentCollectRecords: ConversionRecentCollectRecordViewModel[];
  activeShareGrantSnapshotRows?: ConversionMetricBucketViewModel[];
  activeInviteGrantSnapshotRows?: ConversionMetricBucketViewModel[];
  attributionScope: DrilldownAttributionScopeViewModel | null;
  notes: string[];
  loading: boolean;
  error: ApiErrorViewModel | null;
  empty: boolean;
  emptyMessage: string;
};

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

function DailyBucketTable({ rows }: { rows: ConversionDailyBucketViewModel[] }) {
  if (rows.length === 0) {
    return <div className="empty-state">No daily buckets recorded in this window.</div>;
  }

  const headers = rows[0]?.metrics ?? [];

  return (
    <div className="drilldown-table-wrap">
      <table className="drilldown-table">
        <thead>
          <tr>
            <th scope="col">Day</th>
            {headers.map((metric) => (
              <th key={metric.key} scope="col">
                {metric.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.day}>
              <th scope="row">{row.day}</th>
              {row.metrics.map((metric) => (
                <td key={metric.key}>{metric.count}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RankedListSection({
  rows,
  emptyLabel,
}: {
  rows: RankedMetricItem[];
  emptyLabel: string;
}) {
  if (rows.length === 0) {
    return <div className="empty-state">{emptyLabel}</div>;
  }

  return (
    <ul className="ranked-list">
      {rows.map((row) => (
        <li
          key={"workspaceId" in row ? row.workspaceId : row.resultShareGrantId}
          className="ranked-item"
        >
          <div className="ranked-item-header">
            <div>
              <strong>{row.title}</strong>
              <p>{row.subtitle}</p>
            </div>
            <div className="ranked-item-time">
              <span>Last activity</span>
              <strong>{row.lastActivityAt ?? "No activity yet"}</strong>
            </div>
          </div>
          <MetricRows rows={row.metrics} emptyLabel={emptyLabel} />
        </li>
      ))}
    </ul>
  );
}

function RecentActivitySection({
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
              <strong>{row.occurredAt ?? "Timestamp not recorded"}</strong>
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

export function ConversionDrilldownPanel({
  eyebrow,
  title,
  description,
  summaryMetrics,
  windowStart,
  windowEnd,
  lastActivityAt,
  dailyBuckets,
  topWorkspaces,
  topResultShareGrants,
  recentShareEvents,
  recentInviteClaims,
  recentCollectRecords,
  activeShareGrantSnapshotRows,
  activeInviteGrantSnapshotRows,
  attributionScope,
  notes,
  loading,
  error,
  empty,
  emptyMessage,
}: ConversionDrilldownPanelProps) {
  return (
    <section className="panel-card conversion-panel">
      <div className="panel-card-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p className="panel-copy">{description}</p>
        </div>
      </div>

      <div className="conversion-meta-row">
        <div className="meta-chip">
          <span>Window</span>
          <strong>{renderTimestampRange(windowStart, windowEnd)}</strong>
        </div>
        <div className="meta-chip">
          <span>Last activity</span>
          <strong>{lastActivityAt ?? "No activity yet"}</strong>
        </div>
      </div>

      {error ? (
        <div className="inline-banner error" role="alert">
          <strong>{error.title}</strong>
          <span>{error.message}</span>
        </div>
      ) : null}

      {loading ? <div className="empty-state">Loading conversion drilldown...</div> : null}
      {!loading && !error && empty ? <div className="empty-state">{emptyMessage}</div> : null}

      {!loading && !error && !empty ? (
        <>
          <div className="stat-grid conversion-stat-grid">
            {summaryMetrics.map((metric) => (
              <article key={metric.label} className="stat-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                {metric.hint ? <p className="stat-hint">{metric.hint}</p> : null}
              </article>
            ))}
          </div>

          <div className="conversion-section-grid">
            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Daily buckets</h3>
                <p className="section-subtle-copy">Windowed counts grouped by day.</p>
              </div>
              <DailyBucketTable rows={dailyBuckets} />
            </section>

            {topWorkspaces ? (
              <section className="conversion-section-card">
                <div className="conversion-section-header">
                  <h3>Top workspaces</h3>
                  <p className="section-subtle-copy">
                    Highest-activity workspaces in the current drilldown window.
                  </p>
                </div>
                <RankedListSection
                  rows={topWorkspaces}
                  emptyLabel="No workspaces surfaced in this drilldown response."
                />
              </section>
            ) : null}

            {topResultShareGrants ? (
              <section className="conversion-section-card">
                <div className="conversion-section-header">
                  <h3>Top result-share grants</h3>
                  <p className="section-subtle-copy">
                    Highest-activity result-share grant rows returned by the reserve.
                  </p>
                </div>
                <RankedListSection
                  rows={topResultShareGrants}
                  emptyLabel="No result-share grants surfaced in this drilldown response."
                />
              </section>
            ) : null}

            {activeShareGrantSnapshotRows ? (
              <section className="conversion-section-card">
                <div className="conversion-section-header">
                  <h3>Active share-grant snapshot</h3>
                  <p className="section-subtle-copy">
                    Current active grant inventory for this workspace.
                  </p>
                </div>
                <MetricRows
                  rows={activeShareGrantSnapshotRows}
                  emptyLabel="No active share grants recorded for this workspace."
                />
              </section>
            ) : null}

            {activeInviteGrantSnapshotRows ? (
              <section className="conversion-section-card">
                <div className="conversion-section-header">
                  <h3>Active invite-grant snapshot</h3>
                  <p className="section-subtle-copy">
                    Current active workspace invite inventory in this window.
                  </p>
                </div>
                <MetricRows
                  rows={activeInviteGrantSnapshotRows}
                  emptyLabel="No active invite grants recorded for this workspace."
                />
              </section>
            ) : null}

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Recent share events</h3>
                <p className="section-subtle-copy">
                  Most recent persisted share-view and redirect events.
                </p>
              </div>
              <RecentActivitySection
                rows={recentShareEvents}
                emptyLabel="No recent share events were returned."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Recent invite claims</h3>
                <p className="section-subtle-copy">
                  Workspace-level aggregate invite outcomes kept separate from direct share data.
                </p>
              </div>
              <RecentActivitySection
                rows={recentInviteClaims}
                emptyLabel="No recent invite claims were returned."
              />
            </section>

            <section className="conversion-section-card">
              <div className="conversion-section-header">
                <h3>Recent collect records</h3>
                <p className="section-subtle-copy">
                  Recent result-collect outcomes with direct links only when grant ids are present.
                </p>
              </div>
              <RecentActivitySection
                rows={recentCollectRecords}
                emptyLabel="No recent collect records were returned."
              />
            </section>
          </div>
        </>
      ) : null}

      {attributionScope ? (
        <section className="conversion-notes-card">
          <div className="conversion-section-header">
            <h3>Attribution scope</h3>
          </div>
          <div className="conversion-notes-grid">
            <div>
              <strong>Direct attribution</strong>
              <ul className="note-list">
                {attributionScope.directMetrics.map((metric) => (
                  <li key={metric}>{metric}</li>
                ))}
              </ul>
            </div>
            <div>
              <strong>Workspace-level aggregate only</strong>
              <ul className="note-list">
                {attributionScope.workspaceLevelAggregateMetrics.map((metric) => (
                  <li key={metric}>{metric}</li>
                ))}
              </ul>
            </div>
          </div>
          {attributionScope.notes.length > 0 ? (
            <ul className="note-list">
              {attributionScope.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {notes.length > 0 ? (
        <section className="conversion-notes-card">
          <div className="conversion-section-header">
            <h3>Read-model notes</h3>
          </div>
          <ul className="note-list">
            {notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
