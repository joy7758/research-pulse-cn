import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import { DigestShareView } from "./components/DigestShareView";
import { PaperSnapshotView } from "./components/PaperSnapshotView";
import { TokenEntryView } from "./components/TokenEntryView";
import { WorkspaceBoardView } from "./components/WorkspaceBoardView";
import { WorkspaceResultCollectionsView } from "./components/WorkspaceResultCollectionsView";
import {
  createResultShareApiClient,
  ResultShareApiError,
  type ResultShareApiClient,
} from "./lib/apiClient";
import {
  buildCollectActionResultViewModel,
  buildResultCollectViewModel,
  buildResultShareViewModel,
  buildShareErrorViewModel,
  formatReasonCode,
} from "./lib/shareModel";
import {
  clearVisibleShareAndSelfServiceTokenHints,
  extractShareAccessFromLocation,
  type ShareTokenSource,
} from "./lib/token";
import type {
  CollectActionResultViewModel,
  GroupWorkspaceResultCollectionRead,
  ResultCollectViewModel,
  ResultShareAccessMode,
  ResultShareCollectPreviewRead,
  ResultShareCollectResponseRead,
  ResultShareViewModel,
  ShareErrorViewModel,
  ShareGrantBootstrapRead,
  SharedResultContentRead,
} from "./lib/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_RESULT_SHARE_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

type ResultShareShellProps = {
  initialApiBaseUrl?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  apiClientFactory?: typeof createResultShareApiClient;
};

type ConnectedState = {
  apiBaseUrl: string;
  shareAccess: {
    mode: ResultShareAccessMode;
    value: string;
  };
  client: ResultShareApiClient;
  bootstrap: ShareGrantBootstrapRead;
  content: SharedResultContentRead;
  viewModel: ResultShareViewModel;
};

type SelfServiceState = {
  token: string;
  preview: ResultShareCollectPreviewRead;
  previewViewModel: ResultCollectViewModel;
  collections: GroupWorkspaceResultCollectionRead[];
  actionResponse: ResultShareCollectResponseRead | null;
  actionViewModel: CollectActionResultViewModel | null;
};

function getDefaultPaperSelection(preview: ResultShareCollectPreviewRead): string[] {
  if (preview.share?.share_kind === "paper_snapshot") {
    return [];
  }
  if (preview.collectable_items.length === 1) {
    return [preview.collectable_items[0].paper_id];
  }
  return [];
}

function reconcilePaperSelection(
  preview: ResultShareCollectPreviewRead,
  existingSelection: string[],
): string[] {
  if (preview.share?.share_kind === "paper_snapshot") {
    return [];
  }
  const validPaperIds = new Set(preview.collectable_items.map((item) => item.paper_id));
  const retained = existingSelection.filter((paperId) => validPaperIds.has(paperId));
  return retained.length > 0 ? retained : getDefaultPaperSelection(preview);
}

function reconcileWorkspaceSelection(
  preview: ResultShareCollectPreviewRead,
  existingWorkspaceId: string,
): string {
  const validWorkspaceIds = new Set(
    preview.eligible_workspaces.map((item) => item.workspace.id),
  );
  if (existingWorkspaceId && validWorkspaceIds.has(existingWorkspaceId)) {
    return existingWorkspaceId;
  }
  return preview.eligible_workspaces[0]?.workspace.id ?? "";
}

function App() {
  return <ResultShareShell />;
}

export function ResultShareShell({
  initialApiBaseUrl,
  locationLike,
  historyLike,
  apiClientFactory = createResultShareApiClient,
}: ResultShareShellProps) {
  const resolvedLocation =
    locationLike ?? (typeof window === "undefined" ? undefined : window.location);
  const resolvedHistory =
    historyLike ?? (typeof window === "undefined" ? undefined : window.history);
  const [apiBaseUrlInput, setApiBaseUrlInput] = useState(
    initialApiBaseUrl ?? DEFAULT_API_BASE_URL,
  );
  const [shareAccessMode, setShareAccessMode] = useState<ResultShareAccessMode>("token");
  const [shareValueInput, setShareValueInput] = useState("");
  const [selfServiceTokenInput, setSelfServiceTokenInput] = useState("");
  const [connectedState, setConnectedState] = useState<ConnectedState | null>(null);
  const [selfServiceState, setSelfServiceState] = useState<SelfServiceState | null>(null);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [selfServiceLoading, setSelfServiceLoading] = useState(false);
  const [collectSubmitting, setCollectSubmitting] = useState(false);
  const [errorState, setErrorState] = useState<ShareErrorViewModel | null>(null);
  const [selfServiceError, setSelfServiceError] = useState<ShareErrorViewModel | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const locationConsumedRef = useRef(false);

  const loadSelfServiceState = useCallback(
    async ({
      client,
      shareAccess,
      bootstrap,
      selfServiceToken,
      source,
    }: {
      client: ResultShareApiClient;
      shareAccess: ConnectedState["shareAccess"];
      bootstrap: ShareGrantBootstrapRead;
      selfServiceToken: string;
      source: Exclude<ShareTokenSource, "path" | "none">;
    }) => {
      const trimmedToken = selfServiceToken.trim();
      if (!trimmedToken) {
        setSelfServiceError({
          kind: "unauthorized_self_service",
          title: "Missing self-service token",
          message: "Paste an existing self-service token before previewing collect actions.",
        });
        return;
      }

      setSelfServiceLoading(true);
      setSelfServiceError(null);
      setNoticeMessage(
        source === "query" || source === "fragment"
          ? "Self-service token was moved from the URL into in-memory state."
          : null,
      );

      try {
        const [preview, collections] = await Promise.all([
          shareAccess.mode === "alias"
            ? client.getAliasCollectPreview(shareAccess.value, trimmedToken)
            : client.getCollectPreview(shareAccess.value, trimmedToken),
          client.listWorkspaceResultCollections(trimmedToken),
        ]);
        setSelectedWorkspaceId((current) => reconcileWorkspaceSelection(preview, current));
        setSelectedPaperIds((current) => reconcilePaperSelection(preview, current));
        setSelfServiceState({
          token: trimmedToken,
          preview,
          previewViewModel: buildResultCollectViewModel(bootstrap, preview),
          collections,
          actionResponse: null,
          actionViewModel: null,
        });
        setSelfServiceTokenInput("");
      } catch (error) {
        const shareError =
          error instanceof ResultShareApiError
            ? buildShareErrorViewModel(error)
            : buildShareErrorViewModel({
                kind: "request_failed",
                detail: error instanceof Error ? error.message : String(error),
              });
        setSelfServiceState(null);
        setSelectedWorkspaceId("");
        setSelectedPaperIds([]);
        setSelfServiceError(shareError);
      } finally {
        setSelfServiceLoading(false);
      }
    },
    [],
  );

  const connectWithAccess = useCallback(
    async ({
      shareMode,
      shareValue,
      apiBaseUrl,
      source,
      selfServiceToken,
      selfServiceSource,
    }: {
      shareMode: ResultShareAccessMode;
      shareValue: string;
      apiBaseUrl: string;
      source: Exclude<ShareTokenSource, "none">;
      selfServiceToken?: string | null;
      selfServiceSource?: Exclude<ShareTokenSource, "path" | "none"> | null;
    }) => {
      const trimmedShareValue = shareValue.trim();
      const trimmedApiBaseUrl = apiBaseUrl.trim();
      if (!trimmedShareValue) {
        setErrorState({
          kind: "invalid_token",
          title: shareMode === "alias" ? "Missing share alias" : "Missing share token",
          message:
            shareMode === "alias"
              ? "Paste a share alias or open a share-alias URL first."
              : "Paste a share token or open a share URL first.",
        });
        return;
      }
      if (!trimmedApiBaseUrl) {
        setErrorState({
          kind: "request_failed",
          title: "Missing API base URL",
          message: "Set an API base URL before opening a share.",
        });
        return;
      }

      setLoading(true);
      setShareAccessMode(shareMode);
      setErrorState(null);
      setSelfServiceError(null);
      setSelfServiceState(null);
      setSelectedWorkspaceId("");
      setSelectedPaperIds([]);
      setNoticeMessage(
        source === "query" || source === "fragment"
          ? `${
              shareMode === "alias" ? "Share alias" : "Share token"
            } was moved from the URL into in-memory state.`
          : null,
      );

      const client = apiClientFactory({ apiBaseUrl: trimmedApiBaseUrl });

      try {
        const [bootstrap, content] = await Promise.all([
          shareMode === "alias"
            ? client.getAliasBootstrap(trimmedShareValue)
            : client.getShareBootstrap(trimmedShareValue),
          shareMode === "alias"
            ? client.getAliasContent(trimmedShareValue)
            : client.getShareContent(trimmedShareValue),
        ]);
        const nextConnectedState = {
          apiBaseUrl: trimmedApiBaseUrl,
          shareAccess: {
            mode: shareMode,
            value: trimmedShareValue,
          },
          client,
          bootstrap,
          content,
          viewModel: buildResultShareViewModel(bootstrap, content),
        };
        setConnectedState(nextConnectedState);
        setShareValueInput("");

        if (selfServiceToken && selfServiceSource) {
          await loadSelfServiceState({
            client,
            shareAccess: {
              mode: shareMode,
              value: trimmedShareValue,
            },
            bootstrap,
            selfServiceToken,
            source: selfServiceSource,
          });
        }
      } catch (error) {
        const shareError =
          error instanceof ResultShareApiError
            ? buildShareErrorViewModel(error)
            : buildShareErrorViewModel({
              kind: "request_failed",
              detail: error instanceof Error ? error.message : String(error),
            });
        setConnectedState(null);
        setErrorState(shareError);
        setShareValueInput(source === "manual" ? trimmedShareValue : "");
      } finally {
        setLoading(false);
      }
    },
    [apiClientFactory, loadSelfServiceState],
  );

  useEffect(() => {
    if (locationConsumedRef.current || !resolvedLocation) {
      return;
    }
    locationConsumedRef.current = true;

    const extracted = extractShareAccessFromLocation(resolvedLocation);
    const shouldClearVisibleHints =
      extracted.shareSource === "query" ||
      extracted.shareSource === "fragment" ||
      extracted.selfServiceSource === "query" ||
      extracted.selfServiceSource === "fragment";

    if (shouldClearVisibleHints && resolvedHistory) {
      clearVisibleShareAndSelfServiceTokenHints(resolvedLocation, resolvedHistory);
    }

    if (
      !extracted.shareValue ||
      extracted.shareMode === null ||
      extracted.shareSource === "none"
    ) {
      if (extracted.selfServiceToken) {
        setNoticeMessage(
          "A self-service token was found, but no share token or alias was present to open.",
        );
      }
      return;
    }

    void connectWithAccess({
      shareMode: extracted.shareMode,
      shareValue: extracted.shareValue,
      apiBaseUrl: apiBaseUrlInput,
      source: extracted.shareSource,
      selfServiceToken: extracted.selfServiceToken,
      selfServiceSource:
        extracted.selfServiceSource === "query" ||
        extracted.selfServiceSource === "fragment"
          ? extracted.selfServiceSource
          : null,
    });
  }, [apiBaseUrlInput, connectWithAccess, resolvedHistory, resolvedLocation]);

  const handleOpenShare = useCallback(() => {
    void connectWithAccess({
      shareMode: shareAccessMode,
      shareValue: shareValueInput,
      apiBaseUrl: apiBaseUrlInput,
      source: "manual",
    });
  }, [apiBaseUrlInput, connectWithAccess, shareAccessMode, shareValueInput]);

  const handleConnectSelfService = useCallback(() => {
    if (!connectedState) {
      setSelfServiceError({
        kind: "request_failed",
        title: "Open a share first",
        message: "Load a public share bootstrap before connecting a self-service token.",
      });
      return;
    }
    void loadSelfServiceState({
      client: connectedState.client,
      shareAccess: connectedState.shareAccess,
      bootstrap: connectedState.bootstrap,
      selfServiceToken: selfServiceTokenInput,
      source: "manual",
    });
  }, [connectedState, loadSelfServiceState, selfServiceTokenInput]);

  const handleTogglePaper = useCallback((paperId: string) => {
    setSelectedPaperIds((current) =>
      current.includes(paperId)
        ? current.filter((candidate) => candidate !== paperId)
        : [...current, paperId],
    );
  }, []);

  const handleCollect = useCallback(async () => {
    if (!connectedState || !selfServiceState) {
      return;
    }
    if (!selectedWorkspaceId) {
      setSelfServiceError({
        kind: "request_failed",
        title: "Select a workspace",
        message: "Choose one eligible workspace before collecting a shared result.",
      });
      return;
    }

    const shareKind =
      selfServiceState.preview.share?.share_kind ?? connectedState.bootstrap.grant.share_kind;
    let paperIdsPayload: string[] | undefined;
    if (shareKind === "digest_issue") {
      if (
        selfServiceState.preview.collectable_items.length > 1 &&
        selectedPaperIds.length === 0
      ) {
        setSelfServiceError({
          kind: "request_failed",
          title: "Select paper summaries",
          message:
            "This digest share has multiple collectable papers. Choose at least one paper before collecting.",
        });
        return;
      }
      if (selectedPaperIds.length > 0) {
        paperIdsPayload = selectedPaperIds;
      }
    } else if (shareKind === "workspace_board") {
      setSelfServiceError({
        kind: "request_failed",
        title: "Share kind not collectable",
        message: "Workspace-board shares cannot be collected in this phase.",
      });
      return;
    }

    setCollectSubmitting(true);
    setSelfServiceError(null);
    try {
      const response =
        connectedState.shareAccess.mode === "alias"
          ? await connectedState.client.postAliasCollect(
              connectedState.shareAccess.value,
              selfServiceState.token,
              {
                workspace_id: selectedWorkspaceId,
                ...(paperIdsPayload ? { paper_ids: paperIdsPayload } : {}),
              },
            )
          : await connectedState.client.postCollect(
              connectedState.shareAccess.value,
              selfServiceState.token,
              {
                workspace_id: selectedWorkspaceId,
                ...(paperIdsPayload ? { paper_ids: paperIdsPayload } : {}),
              },
            );
      const [preview, collections] = await Promise.all([
        connectedState.shareAccess.mode === "alias"
          ? connectedState.client.getAliasCollectPreview(
              connectedState.shareAccess.value,
              selfServiceState.token,
            )
          : connectedState.client.getCollectPreview(
              connectedState.shareAccess.value,
              selfServiceState.token,
            ),
        connectedState.client.listWorkspaceResultCollections(selfServiceState.token),
      ]);
      setSelectedWorkspaceId((current) => reconcileWorkspaceSelection(preview, current));
      setSelectedPaperIds((current) => reconcilePaperSelection(preview, current));
      setSelfServiceState({
        token: selfServiceState.token,
        preview,
        previewViewModel: buildResultCollectViewModel(connectedState.bootstrap, preview),
        collections,
        actionResponse: response,
        actionViewModel: buildCollectActionResultViewModel(response),
      });
    } catch (error) {
      const shareError =
        error instanceof ResultShareApiError
          ? buildShareErrorViewModel(error)
          : buildShareErrorViewModel({
              kind: "request_failed",
              detail: error instanceof Error ? error.message : String(error),
            });
      setSelfServiceError(shareError);
    } finally {
      setCollectSubmitting(false);
    }
  }, [connectedState, selectedPaperIds, selectedWorkspaceId, selfServiceState]);

  const handleOpenAnother = useCallback(() => {
    setConnectedState(null);
    setSelfServiceState(null);
    setShareValueInput("");
    setShareAccessMode("token");
    setSelfServiceTokenInput("");
    setSelectedWorkspaceId("");
    setSelectedPaperIds([]);
    setErrorState(null);
    setSelfServiceError(null);
    setNoticeMessage("Cleared the in-memory share and self-service tokens.");
  }, []);

  const readyHeader = useMemo(() => {
    if (!connectedState) {
      return null;
    }
    return {
      shareKind: connectedState.bootstrap.grant.share_kind,
      targetTitle:
        connectedState.bootstrap.target.title ?? connectedState.viewModel.pageTitle,
      createdAt: connectedState.bootstrap.grant.created_at,
      expiresAt: connectedState.bootstrap.grant.expires_at,
      status: connectedState.bootstrap.grant.status,
      notes: connectedState.bootstrap.notes,
      collectionReserve: connectedState.bootstrap.collection_reserve,
    };
  }, [connectedState]);

  const collectViewModel = selfServiceState?.previewViewModel ?? null;
  const actionViewModel = selfServiceState?.actionViewModel ?? null;
  const requiresPaperSelection = collectViewModel?.requiresPaperSelection ?? false;
  const canSubmitCollect =
    Boolean(selfServiceState) &&
    Boolean(collectViewModel) &&
    Boolean(selectedWorkspaceId) &&
    Boolean(collectViewModel?.collectionSupported) &&
    Boolean(collectViewModel?.shareKindCollectable) &&
    Boolean(collectViewModel?.canCollect) &&
    (!requiresPaperSelection || selectedPaperIds.length > 0) &&
    !collectSubmitting;

  if (!connectedState) {
    if (loading) {
      return (
        <main className="connect-shell">
          <section className="connect-card">
            <p className="eyebrow">Loading Share</p>
            <h1>Resolving public share content</h1>
            <p className="lede">
              Fetching share bootstrap and structured content before any self-service collect
              flow is connected.
            </p>
            {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
          </section>
        </main>
      );
    }

    return (
      <TokenEntryView
        apiBaseUrl={apiBaseUrlInput}
        shareAccessMode={shareAccessMode}
        shareValue={shareValueInput}
        loading={loading}
        errorTitle={errorState?.title ?? null}
        errorMessage={errorState?.message ?? null}
        noticeMessage={noticeMessage}
        onApiBaseUrlChange={setApiBaseUrlInput}
        onShareAccessModeChange={setShareAccessMode}
        onShareValueChange={setShareValueInput}
        onSubmit={handleOpenShare}
      />
    );
  }

  return (
    <main className="share-root">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Public Result Share</p>
          <h1>{readyHeader?.targetTitle ?? "Shared result"}</h1>
          <p className="lede">
            This shell remains read-only for public share content. Collect-preview and collect
            actions only become available through a separate in-memory self-service token.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>Kind</span>
            <strong>{readyHeader?.shareKind}</strong>
          </div>
          <div className="hero-chip">
            <span>Status</span>
            <strong>{readyHeader?.status}</strong>
          </div>
          <div className="hero-chip">
            <span>Access</span>
            <strong>{connectedState.shareAccess.mode}</strong>
          </div>
          <div className="hero-chip">
            <span>API base</span>
            <strong>{connectedState.apiBaseUrl}</strong>
          </div>
        </div>
      </section>

      <section className="summary-grid">
        <article className="summary-card">
          <p className="eyebrow">Share summary</p>
          <dl className="summary-list compact">
            <div>
              <dt>Created at</dt>
              <dd>{readyHeader?.createdAt ?? "Unavailable"}</dd>
            </div>
            <div>
              <dt>Expires at</dt>
              <dd>{readyHeader?.expiresAt ?? "Never"}</dd>
            </div>
          </dl>
        </article>
        <article className="summary-card">
          <p className="eyebrow">Safety</p>
          <ul className="bullet-list">
            <li>Public bootstrap remains read-only</li>
            <li>No source-file or attachment sharing</li>
            <li>Collect stays behind self-service auth only</li>
          </ul>
        </article>
        <article className="summary-card">
          <p className="eyebrow">Actions</p>
          <div className="button-row">
            <button className="button-secondary" onClick={handleOpenAnother} type="button">
              Open another share
            </button>
          </div>
        </article>
      </section>

      {noticeMessage ? (
        <div className="banner-row">
          <div className="inline-banner info">{noticeMessage}</div>
        </div>
      ) : null}

      {readyHeader?.notes.length ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Share notes</p>
              <h3>Read-only boundary reminders</h3>
            </div>
          </div>
          <ul className="bullet-list">
            {readyHeader.notes.map((note, index) => (
              <li key={`${index}:${note}`}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {readyHeader?.collectionReserve ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Collection reserve</p>
              <h3>Share-to-workspace intake hint</h3>
            </div>
            <span className="pill">
              {readyHeader.collectionReserve.share_kind_collectable
                ? readyHeader.collectionReserve.supported
                  ? "Collectable via self-service"
                  : "Collect disabled"
                : "Not collectable in v1"}
            </span>
          </div>
          <dl className="summary-list compact">
            <div>
              <dt>Share kind collectable</dt>
              <dd>{readyHeader.collectionReserve.share_kind_collectable ? "Yes" : "No"}</dd>
            </div>
            <div>
              <dt>Self-service collect</dt>
              <dd>
                {readyHeader.collectionReserve.collect_supported_via_self_service ? "Yes" : "No"}
              </dd>
            </div>
            <div>
              <dt>Source files included</dt>
              <dd>{readyHeader.collectionReserve.source_files_included ? "Yes" : "No"}</dd>
            </div>
          </dl>
          {readyHeader.collectionReserve.notes.length > 0 ? (
            <ul className="bullet-list">
              {readyHeader.collectionReserve.notes.map((note, index) => (
                <li key={`${index}:${note}`}>{note}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Self-service collect</p>
            <h3>Connect an existing self-service token</h3>
          </div>
          <span className="pill">{selfServiceState ? "Connected in memory" : "Token required"}</span>
        </div>
        <p className="soft-copy">
          This shell does not introduce a new login system. It only uses the existing
          self-service grant boundary for collect-preview, collect, and collection-history reads.
        </p>
        <label>
          Self-service token
          <input
            autoComplete="off"
            onChange={(event) => setSelfServiceTokenInput(event.target.value)}
            placeholder="Paste existing self-service token"
            spellCheck={false}
            type="text"
            value={selfServiceTokenInput}
          />
        </label>
        <div className="button-row">
          <button
            disabled={selfServiceLoading}
            onClick={handleConnectSelfService}
            type="button"
          >
            {selfServiceLoading ? "Connecting..." : "Connect self-service token"}
          </button>
        </div>
        {selfServiceError ? (
          <div className="inline-banner danger" role="alert">
            <strong>{selfServiceError.title}</strong>
            <span>{selfServiceError.message}</span>
          </div>
        ) : null}
      </section>

      {selfServiceState && collectViewModel ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Collect preview</p>
              <h3>Review workspace intake options</h3>
            </div>
            <span className="pill">
              {collectViewModel.shareKindCollectable
                ? collectViewModel.canCollect
                  ? "Ready to collect"
                  : "Review constraints"
                : "Not collectable"}
            </span>
          </div>

          {collectViewModel.reasonCodes.length > 0 ? (
            <div className="inline-banner warning">
              <strong>Collect preview returned reason codes</strong>
              <span>{collectViewModel.reasonCodes.map(formatReasonCode).join(", ")}</span>
            </div>
          ) : null}

          {collectViewModel.notes.length > 0 ? (
            <ul className="bullet-list">
              {collectViewModel.notes.map((note, index) => (
                <li key={`${index}:${note}`}>{note}</li>
              ))}
            </ul>
          ) : null}

          <div className="collect-layout">
            <section className="collect-column">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Collectable papers</p>
                  <h4>Structured paper objects only</h4>
                </div>
                {collectViewModel.requiresPaperSelection ? (
                  <span className="pill">Explicit paper selection required</span>
                ) : null}
              </div>
              {collectViewModel.collectableItems.length === 0 ? (
                <div className="empty-state">
                  No collectable paper summaries are available for this share in v1.
                </div>
              ) : (
                <div className="list-stack">
                  {collectViewModel.collectableItems.map((item) => {
                    const selected = selectedPaperIds.includes(item.paperId);
                    return (
                      <article
                        className={`list-card ${selected ? "list-card-selected" : ""}`}
                        key={item.paperId}
                      >
                        <div className="list-card-header">
                          <div>
                            <h4>{item.title}</h4>
                            <p className="meta-copy">{item.subtitle}</p>
                          </div>
                          {collectViewModel.requiresPaperSelection ? (
                            <label className="checkbox-chip">
                              <input
                                checked={selected}
                                onChange={() => handleTogglePaper(item.paperId)}
                                type="checkbox"
                              />
                              <span>{selected ? "Selected" : "Select"}</span>
                            </label>
                          ) : (
                            <span className="pill">Single paper flow</span>
                          )}
                        </div>
                        {item.nextAction ? (
                          <p className="soft-copy">Next action: {item.nextAction}</p>
                        ) : null}
                        {item.blocker ? <p className="soft-copy">Blocker: {item.blocker}</p> : null}
                        {item.sourceSummary ? (
                          <p className="soft-copy">Source context: {item.sourceSummary}</p>
                        ) : null}
                        {item.notes.length > 0 ? (
                          <p className="soft-copy">{item.notes.join(" ")}</p>
                        ) : null}
                      </article>
                    );
                  })}
                </div>
              )}
            </section>

            <section className="collect-column">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Eligible workspaces</p>
                  <h4>Select one workspace</h4>
                </div>
              </div>
              {collectViewModel.eligibleWorkspaces.length === 0 ? (
                <div className="empty-state">
                  The current self-service token has no eligible owner/editor workspace memberships
                  for collect in this phase.
                </div>
              ) : (
                <label>
                  Target workspace
                  <select
                    onChange={(event) => setSelectedWorkspaceId(event.target.value)}
                    value={selectedWorkspaceId}
                  >
                    {collectViewModel.eligibleWorkspaces.map((workspace) => (
                      <option key={workspace.workspaceId} value={workspace.workspaceId}>
                        {workspace.label} · {workspace.membershipRole}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <div className="button-row">
                <button disabled={!canSubmitCollect} onClick={handleCollect} type="button">
                  {collectSubmitting ? "Collecting..." : "Collect into workspace"}
                </button>
              </div>

              {requiresPaperSelection && selectedPaperIds.length === 0 ? (
                <p className="soft-copy">
                  This digest share contains multiple collectable papers. Select one or more paper
                  summaries before collecting.
                </p>
              ) : null}
            </section>
          </div>
        </section>
      ) : null}

      {actionViewModel ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Collect result</p>
              <h3>{actionViewModel.title}</h3>
            </div>
            <span className="pill">{actionViewModel.action}</span>
          </div>
          <p>{actionViewModel.message}</p>
          {actionViewModel.notes.length > 0 ? (
            <ul className="bullet-list">
              {actionViewModel.notes.map((note, index) => (
                <li key={`${index}:${note}`}>{note}</li>
              ))}
            </ul>
          ) : null}
          <div className="list-stack">
            {actionViewModel.itemResults.map((item) => (
              <article className="list-card" key={`${item.paperId}:${item.status}`}>
                <div className="list-card-header">
                  <div>
                    <h4>{item.title}</h4>
                    <p className="meta-copy">paper {item.paperId}</p>
                  </div>
                  <span className="pill">{item.status}</span>
                </div>
                {item.reasonCodes.length > 0 ? (
                  <p className="soft-copy">
                    Reason codes: {item.reasonCodes.map(formatReasonCode).join(", ")}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {selfServiceState ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Workspace result collections</p>
              <h3>Current self-service collection history</h3>
            </div>
          </div>
          <WorkspaceResultCollectionsView collections={selfServiceState.collections} />
        </section>
      ) : null}

      {connectedState.viewModel.shareKind === "digest_issue" ? (
        <DigestShareView viewModel={connectedState.viewModel} />
      ) : null}
      {connectedState.viewModel.shareKind === "paper_snapshot" ? (
        <PaperSnapshotView viewModel={connectedState.viewModel} />
      ) : null}
      {connectedState.viewModel.shareKind === "workspace_board" ? (
        <WorkspaceBoardView viewModel={connectedState.viewModel} />
      ) : null}
    </main>
  );
}

export default App;
