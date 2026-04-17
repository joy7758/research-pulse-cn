import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  startTransition,
} from "react";

import "./App.css";
import { FieldIssueList } from "./components/FieldIssueList";
import { PreviewPanel } from "./components/PreviewPanel";
import { TokenEntryView } from "./components/TokenEntryView";
import {
  buildContractFieldMap,
  buildDraftFingerprint,
  buildFormStateFromBootstrap,
  buildSettingsPatchPayload,
  createQuietHoursWindowDraft,
  groupValidationIssuesByField,
  normalizeWeekdaySelection,
  weekdayOptions,
} from "./lib/editorModel";
import {
  createSubscriptionEditorApiClient,
  SubscriptionEditorApiError,
  type SubscriptionEditorApiClient,
} from "./lib/apiClient";
import {
  clearHandoffTokenFromVisibleUrl,
  extractHandoffTokenFromFragment,
} from "./lib/token";
import type {
  EditorFormState,
  SafeBindingSummaryRead,
  SubscriptionEditorBootstrapRead,
  SubscriptionSelfServiceEditorContractRead,
  SubscriptionSettingsPreviewRead,
  SubscriptionSettingsSaveResultRead,
  SubscriptionSettingsValidationIssueRead,
} from "./lib/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_SUBSCRIPTION_EDITOR_API_BASE_URL?.trim() ||
  "http://127.0.0.1:8000";

type SubscriptionEditorShellProps = {
  initialApiBaseUrl?: string;
  initialHash?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  apiClientFactory?: typeof createSubscriptionEditorApiClient;
};

type ConnectedState = {
  apiBaseUrl: string;
  handoffToken: string;
  client: SubscriptionEditorApiClient;
  bootstrap: SubscriptionEditorBootstrapRead;
  contract: SubscriptionSelfServiceEditorContractRead;
};

function App() {
  return <SubscriptionEditorShell />;
}

export function SubscriptionEditorShell({
  initialApiBaseUrl,
  initialHash,
  locationLike,
  historyLike,
  apiClientFactory = createSubscriptionEditorApiClient,
}: SubscriptionEditorShellProps) {
  const resolvedLocation =
    locationLike ?? (typeof window === "undefined" ? undefined : window.location);
  const resolvedHistory =
    historyLike ?? (typeof window === "undefined" ? undefined : window.history);
  const [apiBaseUrlInput, setApiBaseUrlInput] = useState(
    initialApiBaseUrl ?? DEFAULT_API_BASE_URL,
  );
  const [handoffTokenInput, setHandoffTokenInput] = useState("");
  const [connectedState, setConnectedState] = useState<ConnectedState | null>(null);
  const [formState, setFormState] = useState<EditorFormState | null>(null);
  const [previewResult, setPreviewResult] = useState<SubscriptionSettingsPreviewRead | null>(null);
  const [saveResult, setSaveResult] = useState<SubscriptionSettingsSaveResultRead | null>(null);
  const [fieldIssues, setFieldIssues] = useState<SubscriptionSettingsValidationIssueRead[]>([]);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastPreviewFingerprint, setLastPreviewFingerprint] = useState<string | null>(null);
  const [lastSavedFingerprint, setLastSavedFingerprint] = useState<string | null>(null);
  const fragmentConsumedRef = useRef(false);

  const contractFieldMap = useMemo(() => {
    if (!connectedState) {
      return new Map();
    }
    return buildContractFieldMap(connectedState.contract);
  }, [connectedState]);

  const fieldIssuesById = useMemo(() => groupValidationIssuesByField(fieldIssues), [fieldIssues]);

  const currentFingerprint = useMemo(() => {
    if (!formState) {
      return null;
    }
    return buildDraftFingerprint(formState);
  }, [formState]);

  const previewStale =
    previewResult !== null &&
    lastPreviewFingerprint !== null &&
    currentFingerprint !== lastPreviewFingerprint;
  const saveResultStale =
    saveResult !== null &&
    lastSavedFingerprint !== null &&
    currentFingerprint !== lastSavedFingerprint;

  const readOnlyBindingSummary: SafeBindingSummaryRead | null =
    connectedState?.bootstrap.official_account_binding_summary ?? null;

  const handleDisconnect = useCallback(() => {
    setConnectedState(null);
    setFormState(null);
    setPreviewResult(null);
    setSaveResult(null);
    setFieldIssues([]);
    setGlobalError(null);
    setNoticeMessage("Cleared the in-memory handoff token.");
    setHandoffTokenInput("");
    setLastPreviewFingerprint(null);
    setLastSavedFingerprint(null);
  }, []);

  const connectWithToken = useCallback(
    async ({
      handoffToken,
      apiBaseUrl,
      source,
    }: {
      handoffToken: string;
      apiBaseUrl: string;
      source: "manual" | "fragment";
    }) => {
      const trimmedToken = handoffToken.trim();
      const trimmedApiBaseUrl = apiBaseUrl.trim();
      if (!trimmedToken) {
        setGlobalError("A handoff token is required.");
        return;
      }
      if (!trimmedApiBaseUrl) {
        setGlobalError("An API base URL is required.");
        return;
      }

      setConnecting(true);
      setGlobalError(null);
      setNoticeMessage(
        source === "fragment"
          ? "Handoff token was ingested from the URL fragment and moved into in-memory state."
          : null,
      );

      const client = apiClientFactory({
        apiBaseUrl: trimmedApiBaseUrl,
        handoffToken: trimmedToken,
      });

      try {
        const [bootstrap, contract] = await Promise.all([
          client.getBootstrap(),
          client.getContract(),
        ]);
        const nextFormState = buildFormStateFromBootstrap(bootstrap);
        const nextFingerprint = buildDraftFingerprint(nextFormState);
        startTransition(() => {
          setConnectedState({
            apiBaseUrl: trimmedApiBaseUrl,
            handoffToken: trimmedToken,
            client,
            bootstrap,
            contract,
          });
          setFormState(nextFormState);
          setPreviewResult(null);
          setSaveResult(null);
          setFieldIssues([]);
          setLastPreviewFingerprint(null);
          setLastSavedFingerprint(nextFingerprint);
          setHandoffTokenInput("");
        });
      } catch (error) {
        const detail =
          error instanceof SubscriptionEditorApiError
            ? error.message
            : error instanceof Error
              ? error.message
              : String(error);
        startTransition(() => {
          setConnectedState(null);
          setFormState(null);
          setPreviewResult(null);
          setSaveResult(null);
          setFieldIssues(
            error instanceof SubscriptionEditorApiError ? error.fieldErrors : [],
          );
          setGlobalError(detail);
          setLastPreviewFingerprint(null);
          setLastSavedFingerprint(null);
          setHandoffTokenInput(source === "manual" ? trimmedToken : "");
        });
      } finally {
        setConnecting(false);
      }
    },
    [apiClientFactory],
  );

  useEffect(() => {
    if (fragmentConsumedRef.current) {
      return;
    }
    fragmentConsumedRef.current = true;

    const fragment = initialHash ?? resolvedLocation?.hash ?? "";
    const extracted = extractHandoffTokenFromFragment(fragment);
    if (!extracted.handoffToken) {
      return;
    }

    if (resolvedLocation && resolvedHistory && !initialHash) {
      clearHandoffTokenFromVisibleUrl(resolvedLocation, resolvedHistory);
    }

    void connectWithToken({
      handoffToken: extracted.handoffToken,
      apiBaseUrl: apiBaseUrlInput,
      source: "fragment",
    });
  }, [apiBaseUrlInput, connectWithToken, initialHash, resolvedHistory, resolvedLocation]);

  const handlePreview = useCallback(async () => {
    if (!connectedState || !formState) {
      return;
    }
    setPreviewing(true);
    setGlobalError(null);
    try {
      const preview = await connectedState.client.previewSettings(
        buildSettingsPatchPayload(formState),
      );
      setPreviewResult(preview);
      setFieldIssues(preview.validation_errors);
      setSaveResult(null);
      setLastPreviewFingerprint(currentFingerprint);
    } catch (error) {
      const detail =
        error instanceof SubscriptionEditorApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : String(error);
      if (error instanceof SubscriptionEditorApiError && error.status === 401) {
        handleDisconnect();
      }
      setFieldIssues(
        error instanceof SubscriptionEditorApiError ? error.fieldErrors : [],
      );
      setGlobalError(detail);
    } finally {
      setPreviewing(false);
    }
  }, [connectedState, currentFingerprint, formState, handleDisconnect]);

  const handleSave = useCallback(async () => {
    if (!connectedState || !formState) {
      return;
    }
    setSaving(true);
    setGlobalError(null);
    try {
      const result = await connectedState.client.saveSettings(
        buildSettingsPatchPayload(formState),
        { includePreview: true },
      );
      const nextBootstrap: SubscriptionEditorBootstrapRead = {
        ...connectedState.bootstrap,
        current_settings_draft: {
          ...result.saved_settings,
          self_service_grant_status:
            connectedState.bootstrap.current_settings_draft.self_service_grant_status,
        },
      };
      const nextFormState = buildFormStateFromBootstrap(nextBootstrap);
      const nextFingerprint = buildDraftFingerprint(nextFormState);
      setConnectedState({
        ...connectedState,
        bootstrap: nextBootstrap,
      });
      setFormState(nextFormState);
      setFieldIssues([]);
      setPreviewResult(
        result.authoritative_preview
          ? {
              contract_version: connectedState.contract.contract_version,
              normalized_draft: nextBootstrap.current_settings_draft,
              changed_fields: result.changed_fields,
              validation_errors: [],
              validation_warnings: [],
              authoritative_preview: result.authoritative_preview,
            }
          : null,
      );
      setSaveResult(result);
      setLastSavedFingerprint(nextFingerprint);
      setLastPreviewFingerprint(nextFingerprint);
      setNoticeMessage("Saved the safe editable subset to the authoritative subscription policy.");
    } catch (error) {
      const detail =
        error instanceof SubscriptionEditorApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : String(error);
      if (error instanceof SubscriptionEditorApiError && error.status === 401) {
        handleDisconnect();
      }
      setFieldIssues(
        error instanceof SubscriptionEditorApiError ? error.fieldErrors : [],
      );
      setGlobalError(detail);
    } finally {
      setSaving(false);
    }
  }, [connectedState, formState, handleDisconnect]);

  const handleAddQuietHoursWindow = useCallback(() => {
    setFormState((current) =>
      current
        ? {
            ...current,
            quietHoursWindows: [
              ...current.quietHoursWindows,
              createQuietHoursWindowDraft(current.quietHoursWindows.length),
            ],
          }
        : current,
    );
  }, []);

  const renderFieldIssues = (fieldId: string) => (
    <FieldIssueList issues={fieldIssuesById[fieldId] ?? []} />
  );

  if (!connectedState || !formState) {
    return (
      <TokenEntryView
        apiBaseUrl={apiBaseUrlInput}
        handoffToken={handoffTokenInput}
        connecting={connecting}
        errorMessage={globalError}
        noticeMessage={noticeMessage}
        onApiBaseUrlChange={setApiBaseUrlInput}
        onHandoffTokenChange={setHandoffTokenInput}
        onSubmit={() =>
          void connectWithToken({
            handoffToken: handoffTokenInput,
            apiBaseUrl: apiBaseUrlInput,
            source: "manual",
          })
        }
      />
    );
  }

  return (
    <main className="editor-root">
      <header className="hero-card">
        <div>
          <p className="eyebrow">Thin web shell</p>
          <h1>Subscription editor</h1>
          <p className="lede">
            Handoff token stays in memory only. This shell calls the existing
            <code>/subscription-editor/*</code> APIs and keeps the backend authoritative.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>API base</span>
            <strong>{connectedState.apiBaseUrl}</strong>
          </div>
          <button className="button-secondary" onClick={handleDisconnect} type="button">
            Clear token
          </button>
        </div>
      </header>

      {globalError ? <div className="inline-banner error">{globalError}</div> : null}
      {noticeMessage ? <div className="inline-banner success">{noticeMessage}</div> : null}

      <section className="summary-grid">
        <article className="editor-card">
          <p className="eyebrow">User</p>
          <h2>{connectedState.bootstrap.user.name}</h2>
          <dl className="summary-list">
            <div>
              <dt>Email</dt>
              <dd>{connectedState.bootstrap.user.email ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Field</dt>
              <dd>{connectedState.bootstrap.user.field ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Channel</dt>
              <dd>{connectedState.bootstrap.current_settings_draft.channel}</dd>
            </div>
            <div>
              <dt>Grant status</dt>
              <dd>{connectedState.bootstrap.current_settings_draft.self_service_grant_status}</dd>
            </div>
          </dl>
        </article>

        <article className="editor-card">
          <p className="eyebrow">Binding</p>
          <h2>{readOnlyBindingSummary?.display_label ?? "No binding summary"}</h2>
          <dl className="summary-list">
            <div>
              <dt>App ID</dt>
              <dd>{readOnlyBindingSummary?.app_id ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Bind state</dt>
              <dd>{readOnlyBindingSummary?.bind_state ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Subscribed</dt>
              <dd>{readOnlyBindingSummary ? String(readOnlyBindingSummary.subscribed) : "Unavailable"}</dd>
            </div>
            <div>
              <dt>Digest enabled</dt>
              <dd>
                {readOnlyBindingSummary
                  ? String(readOnlyBindingSummary.digest_enabled)
                  : "Unavailable"}
              </dd>
            </div>
          </dl>
        </article>

        <article className="editor-card">
          <p className="eyebrow">Handoff grant</p>
          <h2>{connectedState.bootstrap.handoff_grant.display_label ?? "Mini editor handoff"}</h2>
          <dl className="summary-list">
            <div>
              <dt>Status</dt>
              <dd>{connectedState.bootstrap.handoff_grant.status}</dd>
            </div>
            <div>
              <dt>Issued by</dt>
              <dd>{connectedState.bootstrap.handoff_grant.issued_by}</dd>
            </div>
            <div>
              <dt>Expires at</dt>
              <dd>{connectedState.bootstrap.handoff_grant.expires_at ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Supported endpoints</dt>
              <dd>{connectedState.bootstrap.supported_editor_endpoints.join(", ")}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section className="editor-layout">
        <div className="editor-column">
          {connectedState.contract.sections.map((section) => (
            <article className="editor-card" key={section.section_id}>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{section.section_id}</p>
                  <h2>{section.title}</h2>
                  {section.description ? <p className="section-copy">{section.description}</p> : null}
                </div>
              </div>

              {section.field_ids.map((fieldId) => {
                const field = contractFieldMap.get(fieldId);
                if (!field) {
                  return null;
                }

                if (fieldId === "channel") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>{field.label}</label>
                      <div className="read-only-value">
                        {connectedState.bootstrap.current_settings_draft.channel}
                      </div>
                      {field.description ? <p className="field-copy">{field.description}</p> : null}
                    </div>
                  );
                }

                if (fieldId === "official_account_binding_summary") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>{field.label}</label>
                      <div className="read-only-panel">
                        {readOnlyBindingSummary ? (
                          <dl className="summary-list compact">
                            <div>
                              <dt>Display label</dt>
                              <dd>{readOnlyBindingSummary.display_label ?? "Unavailable"}</dd>
                            </div>
                            <div>
                              <dt>Subscribed</dt>
                              <dd>{String(readOnlyBindingSummary.subscribed)}</dd>
                            </div>
                            <div>
                              <dt>Last seen</dt>
                              <dd>{readOnlyBindingSummary.last_seen_at ?? "Unavailable"}</dd>
                            </div>
                          </dl>
                        ) : (
                          <div className="empty-state">No official-account binding is attached yet.</div>
                        )}
                      </div>
                    </div>
                  );
                }

                if (fieldId === "self_service_grant_status") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>{field.label}</label>
                      <div className="read-only-value">
                        {connectedState.bootstrap.current_settings_draft.self_service_grant_status}
                      </div>
                    </div>
                  );
                }

                if (fieldId === "latest_digest_summary") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>{field.label}</label>
                      <div className="read-only-panel">
                        {connectedState.bootstrap.latest_digest_summary ? (
                          <dl className="summary-list compact">
                            <div>
                              <dt>Title</dt>
                              <dd>{connectedState.bootstrap.latest_digest_summary.title}</dd>
                            </div>
                            <div>
                              <dt>Issue date</dt>
                              <dd>{connectedState.bootstrap.latest_digest_summary.issue_date}</dd>
                            </div>
                            <div>
                              <dt>Selected cards</dt>
                              <dd>
                                {connectedState.bootstrap.latest_digest_summary.selected_card_count}
                              </dd>
                            </div>
                          </dl>
                        ) : (
                          <div className="empty-state">
                            No latest digest summary is available for authoritative preview context.
                          </div>
                        )}
                      </div>
                    </div>
                  );
                }

                if (fieldId === "authoritative_preview_supported") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>{field.label}</label>
                      <div className="read-only-value">
                        {String(connectedState.bootstrap.authoritative_preview_supported)}
                      </div>
                    </div>
                  );
                }

                if (fieldId === "enabled") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label className="checkbox-row">
                        <input
                          checked={formState.enabled}
                          onChange={(event) =>
                            setFormState({ ...formState, enabled: event.target.checked })
                          }
                          type="checkbox"
                        />
                        <span>{field.label}</span>
                      </label>
                      {field.description ? <p className="field-copy">{field.description}</p> : null}
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                if (fieldId === "quiet_hours") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <div className="field-heading-row">
                        <label>{field.label}</label>
                        <button
                          className="button-secondary small-button"
                          onClick={handleAddQuietHoursWindow}
                          type="button"
                        >
                          Add window
                        </button>
                      </div>
                      {field.description ? <p className="field-copy">{field.description}</p> : null}
                      {formState.quietHoursWindows.length === 0 ? (
                        <div className="empty-state">
                          No quiet-hour windows configured. Add one if you want delivery silence.
                        </div>
                      ) : (
                        <div className="quiet-hours-list">
                          {formState.quietHoursWindows.map((window, index) => (
                            <div className="quiet-hours-row" key={window.id}>
                              <label>
                                Start
                                <input
                                  type="time"
                                  value={window.start}
                                  onChange={(event) =>
                                    setFormState({
                                      ...formState,
                                      quietHoursWindows: formState.quietHoursWindows.map(
                                        (candidate) =>
                                          candidate.id === window.id
                                            ? { ...candidate, start: event.target.value }
                                            : candidate,
                                      ),
                                    })
                                  }
                                />
                              </label>
                              <label>
                                End
                                <input
                                  type="time"
                                  value={window.end}
                                  onChange={(event) =>
                                    setFormState({
                                      ...formState,
                                      quietHoursWindows: formState.quietHoursWindows.map(
                                        (candidate) =>
                                          candidate.id === window.id
                                            ? { ...candidate, end: event.target.value }
                                            : candidate,
                                      ),
                                    })
                                  }
                                />
                              </label>
                              <button
                                className="button-secondary small-button"
                                onClick={() =>
                                  setFormState({
                                    ...formState,
                                    quietHoursWindows: formState.quietHoursWindows.filter(
                                      (candidate) => candidate.id !== window.id,
                                    ),
                                  })
                                }
                                type="button"
                              >
                                Remove
                              </button>
                              <span className="quiet-hours-index">Window {index + 1}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                if (fieldId === "timezone") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>
                        {field.label}
                        <input
                          value={formState.timezone}
                          onChange={(event) =>
                            setFormState({ ...formState, timezone: event.target.value })
                          }
                          placeholder="Asia/Shanghai"
                        />
                      </label>
                      {field.description ? <p className="field-copy">{field.description}</p> : null}
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                if (fieldId === "allowed_weekdays") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>{field.label}</label>
                      <p className="field-copy">
                        {connectedState.contract.weekday_numbering_note}
                      </p>
                      <div className="weekday-grid">
                        {weekdayOptions.map((day) => {
                          const checked = formState.allowedWeekdays.includes(day.value);
                          return (
                            <label className="weekday-pill" key={day.value}>
                              <input
                                checked={checked}
                                onChange={() => {
                                  const nextDays = checked
                                    ? formState.allowedWeekdays.filter(
                                        (value) => value !== day.value,
                                      )
                                    : [...formState.allowedWeekdays, day.value];
                                  setFormState({
                                    ...formState,
                                    allowedWeekdays: normalizeWeekdaySelection(nextDays),
                                  });
                                }}
                                type="checkbox"
                              />
                              <span>{day.label}</span>
                            </label>
                          );
                        })}
                      </div>
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                if (fieldId === "muted_until") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>
                        {field.label}
                        <input
                          type="datetime-local"
                          value={formState.mutedUntil}
                          onChange={(event) =>
                            setFormState({ ...formState, mutedUntil: event.target.value })
                          }
                        />
                      </label>
                      <div className="button-row">
                        <button
                          className="button-secondary small-button"
                          onClick={() => setFormState({ ...formState, mutedUntil: "" })}
                          type="button"
                        >
                          Clear mute
                        </button>
                      </div>
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                if (fieldId === "minimum_selected_cards") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label>
                        {field.label}
                        <input
                          inputMode="numeric"
                          type="number"
                          min="0"
                          step="1"
                          value={formState.minimumSelectedCards}
                          onChange={(event) =>
                            setFormState({
                              ...formState,
                              minimumSelectedCards: event.target.value,
                            })
                          }
                        />
                      </label>
                      {field.description ? <p className="field-copy">{field.description}</p> : null}
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                if (fieldId === "skip_if_no_today_focus") {
                  return (
                    <div className="field-block" key={fieldId}>
                      <label className="checkbox-row">
                        <input
                          checked={formState.skipIfNoTodayFocus}
                          onChange={(event) =>
                            setFormState({
                              ...formState,
                              skipIfNoTodayFocus: event.target.checked,
                            })
                          }
                          type="checkbox"
                        />
                        <span>{field.label}</span>
                      </label>
                      {field.description ? <p className="field-copy">{field.description}</p> : null}
                      {renderFieldIssues(fieldId)}
                    </div>
                  );
                }

                return null;
              })}
            </article>
          ))}
        </div>

        <div className="editor-column side-column">
          <PreviewPanel
            preview={previewResult}
            previewStale={previewStale}
            saveResult={saveResult}
            saveResultStale={saveResultStale}
          />

          <section className="editor-card">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Actions</p>
                <h2>Draft actions</h2>
              </div>
            </div>
            <p className="section-copy">
              Local edits stay in this browser tab until you explicitly preview or save them.
            </p>
            <div className="button-row">
              <button disabled={previewing || saving} onClick={() => void handlePreview()} type="button">
                {previewing ? "Previewing..." : "Preview changes"}
              </button>
              <button disabled={previewing || saving} onClick={() => void handleSave()} type="button">
                {saving ? "Saving..." : "Save changes"}
              </button>
              <button
                className="button-secondary"
                disabled={previewing || saving}
                onClick={() =>
                  setFormState(buildFormStateFromBootstrap(connectedState.bootstrap))
                }
                type="button"
              >
                Reset to saved state
              </button>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

export default App;
