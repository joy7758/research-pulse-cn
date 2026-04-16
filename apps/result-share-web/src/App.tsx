import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import { DigestShareView } from "./components/DigestShareView";
import { PaperSnapshotView } from "./components/PaperSnapshotView";
import { TokenEntryView } from "./components/TokenEntryView";
import { WorkspaceBoardView } from "./components/WorkspaceBoardView";
import {
  createResultShareApiClient,
  ResultShareApiError,
  type ResultShareApiClient,
} from "./lib/apiClient";
import {
  buildResultShareViewModel,
  buildShareErrorViewModel,
} from "./lib/shareModel";
import {
  clearVisibleShareTokenHints,
  extractShareTokenFromLocation,
} from "./lib/token";
import type {
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
  shareToken: string;
  client: ResultShareApiClient;
  bootstrap: ShareGrantBootstrapRead;
  content: SharedResultContentRead;
  viewModel: ResultShareViewModel;
};

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
  const [shareTokenInput, setShareTokenInput] = useState("");
  const [connectedState, setConnectedState] = useState<ConnectedState | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ShareErrorViewModel | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const locationConsumedRef = useRef(false);

  const connectWithToken = useCallback(
    async ({
      shareToken,
      apiBaseUrl,
      source,
    }: {
      shareToken: string;
      apiBaseUrl: string;
      source: "manual" | "path" | "query" | "fragment";
    }) => {
      const trimmedToken = shareToken.trim();
      const trimmedApiBaseUrl = apiBaseUrl.trim();
      if (!trimmedToken) {
        setErrorState({
          kind: "invalid_token",
          title: "Missing share token",
          message: "Paste a share token or open a share URL first.",
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
      setErrorState(null);
      setNoticeMessage(
        source === "query" || source === "fragment"
          ? "Share token was moved from the URL into in-memory state."
          : null,
      );

      const client = apiClientFactory({ apiBaseUrl: trimmedApiBaseUrl });

      try {
        const bootstrap = await client.getShareBootstrap(trimmedToken);
        const content = await client.getShareContent(trimmedToken);
        const viewModel = buildResultShareViewModel(bootstrap, content);
        setConnectedState({
          apiBaseUrl: trimmedApiBaseUrl,
          shareToken: trimmedToken,
          client,
          bootstrap,
          content,
          viewModel,
        });
        setShareTokenInput("");
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
        setShareTokenInput(source === "manual" ? trimmedToken : "");
      } finally {
        setLoading(false);
      }
    },
    [apiClientFactory],
  );

  useEffect(() => {
    if (locationConsumedRef.current || !resolvedLocation) {
      return;
    }
    locationConsumedRef.current = true;

    const extracted = extractShareTokenFromLocation(resolvedLocation);
    if (!extracted.shareToken || extracted.source === "none") {
      return;
    }

    if (
      resolvedHistory &&
      (extracted.source === "query" || extracted.source === "fragment")
    ) {
      clearVisibleShareTokenHints(resolvedLocation, resolvedHistory);
    }

    void connectWithToken({
      shareToken: extracted.shareToken,
      apiBaseUrl: apiBaseUrlInput,
      source: extracted.source,
    });
  }, [apiBaseUrlInput, connectWithToken, resolvedHistory, resolvedLocation]);

  const handleOpenShare = useCallback(() => {
    void connectWithToken({
      shareToken: shareTokenInput,
      apiBaseUrl: apiBaseUrlInput,
      source: "manual",
    });
  }, [apiBaseUrlInput, connectWithToken, shareTokenInput]);

  const handleOpenAnother = useCallback(() => {
    setConnectedState(null);
    setShareTokenInput("");
    setErrorState(null);
    setNoticeMessage("Cleared the in-memory share token.");
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
    };
  }, [connectedState]);

  if (!connectedState) {
    if (loading) {
      return (
        <main className="connect-shell">
          <section className="connect-card">
            <p className="eyebrow">Loading Share</p>
            <h1>Resolving public share content</h1>
            <p className="lede">
              Fetching share bootstrap and structured read-only content from the public token
              endpoints.
            </p>
            {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
          </section>
        </main>
      );
    }

    return (
      <TokenEntryView
        apiBaseUrl={apiBaseUrlInput}
        shareToken={shareTokenInput}
        loading={loading}
        errorTitle={errorState?.title ?? null}
        errorMessage={errorState?.message ?? null}
        noticeMessage={noticeMessage}
        onApiBaseUrlChange={setApiBaseUrlInput}
        onShareTokenChange={setShareTokenInput}
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
            This shell is read-only and only renders safe structured results from the share token.
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
            <li>Read-only token flow only</li>
            <li>No source-file or attachment sharing</li>
            <li>No local note contents or edit actions</li>
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
            {readyHeader.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
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
