import {
  ACCESS_MODE_FILTER_OPTIONS,
  DEFAULT_CONVERSION_FILTER_LIMIT,
  EVENT_TYPE_FILTER_OPTIONS,
  LIMIT_FILTER_OPTIONS,
  OUTCOME_FILTER_OPTIONS,
  SHARE_KIND_FILTER_OPTIONS,
} from "../lib/conversionFilters";
import type {
  ConversionFilterInput,
  ConversionFilterSummaryViewModel,
  ResultShareKind,
  ResultShareViewAccessMode,
  ResultShareViewEventType,
  ResultShareViewOutcome,
} from "../lib/types";

type ConversionFilterBarProps = {
  eyebrow: string;
  title: string;
  description: string;
  filters: ConversionFilterInput;
  summary: ConversionFilterSummaryViewModel;
  disabled: boolean;
  onChange: (patch: Partial<ConversionFilterInput>) => void;
  onApply: () => void;
  onReset: () => void;
};

export function ConversionFilterBar({
  eyebrow,
  title,
  description,
  filters,
  summary,
  disabled,
  onChange,
  onApply,
  onReset,
}: ConversionFilterBarProps) {
  return (
    <section className="panel-card filter-bar-card">
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
          <strong>{summary.windowLabel}</strong>
        </div>
        <div className="meta-chip">
          <span>Recent rows</span>
          <strong>{filters.limit ?? DEFAULT_CONVERSION_FILTER_LIMIT}</strong>
        </div>
      </div>

      <div className="filter-grid">
        <label className="field-stack">
          <span>Date from</span>
          <input
            type="date"
            value={filters.dateFrom ?? ""}
            onChange={(event) => onChange({ dateFrom: event.target.value || null })}
          />
        </label>
        <label className="field-stack">
          <span>Date to</span>
          <input
            type="date"
            value={filters.dateTo ?? ""}
            onChange={(event) => onChange({ dateTo: event.target.value || null })}
          />
        </label>
        <label className="field-stack">
          <span>Share kind</span>
          <select
            value={filters.shareKind ?? ""}
            onChange={(event) =>
              onChange({ shareKind: (event.target.value || null) as ResultShareKind | null })
            }
          >
            <option value="">All share kinds</option>
            {SHARE_KIND_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          <span>Access mode</span>
          <select
            value={filters.accessMode ?? ""}
            onChange={(event) =>
              onChange({
                accessMode: (event.target.value || null) as ResultShareViewAccessMode | null,
              })
            }
          >
            <option value="">All access modes</option>
            {ACCESS_MODE_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          <span>Event type</span>
          <select
            value={filters.eventType ?? ""}
            onChange={(event) =>
              onChange({
                eventType: (event.target.value || null) as ResultShareViewEventType | null,
              })
            }
          >
            <option value="">All event types</option>
            {EVENT_TYPE_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          <span>Outcome</span>
          <select
            value={filters.outcome ?? ""}
            onChange={(event) =>
              onChange({
                outcome: (event.target.value || null) as ResultShareViewOutcome | null,
              })
            }
          >
            <option value="">All outcomes</option>
            {OUTCOME_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field-stack">
          <span>Recent rows limit</span>
          <select
            value={String(filters.limit ?? DEFAULT_CONVERSION_FILTER_LIMIT)}
            onChange={(event) => onChange({ limit: Number(event.target.value) })}
          >
            {LIMIT_FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="button-row">
        <button type="button" className="button-primary" disabled={disabled} onClick={onApply}>
          Apply filters
        </button>
        <button type="button" className="button-secondary" disabled={disabled} onClick={onReset}>
          Reset defaults
        </button>
      </div>

      <section className="filter-summary-card">
        <div className="conversion-section-header">
          <h3>Applied filter summary</h3>
        </div>
        {summary.hasActiveFilters ? (
          <ul className="filter-chip-list">
            {summary.chips.map((chip) => (
              <li key={chip.key} className="filter-chip">
                <span>{chip.label}</span>
                <strong>{chip.value}</strong>
              </li>
            ))}
          </ul>
        ) : (
          <p className="section-subtle-copy">
            No dimension filters are active. The shell is using the default analytics window and
            recent-row limit.
          </p>
        )}
        <ul className="note-list">
          {summary.scopeNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}
