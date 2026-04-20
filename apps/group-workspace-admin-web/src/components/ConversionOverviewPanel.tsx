import type {
  ApiErrorViewModel,
  ConversionAttributionScopeViewModel,
  ConversionMetricSectionViewModel,
  ConversionSummaryMetricViewModel,
} from "../lib/types";

type ConversionOverviewPanelProps = {
  eyebrow: string;
  title: string;
  description: string;
  summaryMetrics: ConversionSummaryMetricViewModel[];
  sections: ConversionMetricSectionViewModel[];
  attributionScope: ConversionAttributionScopeViewModel | null;
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
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

export function ConversionOverviewPanel({
  eyebrow,
  title,
  description,
  summaryMetrics,
  sections,
  attributionScope,
  windowStart,
  windowEnd,
  lastActivityAt,
  loading,
  error,
  empty,
  emptyMessage,
}: ConversionOverviewPanelProps) {
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

      {loading ? <div className="empty-state">Loading conversion overview...</div> : null}

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
            {sections.map((section) => (
              <section key={section.title} className="conversion-section-card">
                <div className="conversion-section-header">
                  <h3>{section.title}</h3>
                </div>
                {section.rows.length === 0 ? (
                  <div className="empty-state">{section.emptyLabel}</div>
                ) : (
                  <dl className="metric-kv-list">
                    {section.rows.map((row) => (
                      <div key={row.key} className="metric-kv-item">
                        <dt>{row.label}</dt>
                        <dd>{row.count}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </section>
            ))}
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
              <strong>Workspace-level aggregates</strong>
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
    </section>
  );
}
