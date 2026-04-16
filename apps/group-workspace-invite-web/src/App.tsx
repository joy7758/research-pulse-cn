import { useCallback, useEffect, useRef, useState } from "react";

import "./App.css";
import { InviteSummaryView } from "./components/InviteSummaryView";
import { InviteTokenEntryView } from "./components/InviteTokenEntryView";
import { MembershipListView } from "./components/MembershipListView";
import {
  createGroupWorkspaceInviteApiClient,
  GroupWorkspaceInviteApiError,
  type GroupWorkspaceInviteApiClient,
} from "./lib/apiClient";
import {
  buildClaimPreviewStatusViewModel,
  buildClaimResultStatusViewModel,
  buildInviteErrorViewModel,
  buildInvitePageViewModel,
  formatReasonCode,
} from "./lib/inviteModel";
import {
  clearVisibleInviteTokenHints,
  extractInviteTokensFromLocation,
  type TokenSource,
} from "./lib/token";
import type {
  ApiErrorViewModel,
  GroupWorkspaceInviteBootstrapRead,
  GroupWorkspaceInviteClaimPreviewRead,
  GroupWorkspaceInviteClaimResponse,
  GroupWorkspaceMembershipRead,
  InvitePageViewModel,
  MembershipStatusViewModel,
} from "./lib/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_GROUP_WORKSPACE_INVITE_API_BASE_URL?.trim() ||
  "http://127.0.0.1:8000";

type InviteShellProps = {
  initialApiBaseUrl?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  apiClientFactory?: typeof createGroupWorkspaceInviteApiClient;
};

type ConnectedInviteState = {
  apiBaseUrl: string;
  inviteToken: string;
  client: GroupWorkspaceInviteApiClient;
  bootstrap: GroupWorkspaceInviteBootstrapRead;
  viewModel: InvitePageViewModel;
};

type SelfServiceState = {
  token: string;
  preview: GroupWorkspaceInviteClaimPreviewRead;
  previewViewModel: MembershipStatusViewModel;
  memberships: GroupWorkspaceMembershipRead[];
  claimResponse: GroupWorkspaceInviteClaimResponse | null;
  claimViewModel: MembershipStatusViewModel | null;
};

function App() {
  return <GroupWorkspaceInviteShell />;
}

export function GroupWorkspaceInviteShell({
  initialApiBaseUrl,
  locationLike,
  historyLike,
  apiClientFactory = createGroupWorkspaceInviteApiClient,
}: InviteShellProps) {
  const resolvedLocation =
    locationLike ?? (typeof window === "undefined" ? undefined : window.location);
  const resolvedHistory =
    historyLike ?? (typeof window === "undefined" ? undefined : window.history);
  const [apiBaseUrlInput, setApiBaseUrlInput] = useState(
    initialApiBaseUrl ?? DEFAULT_API_BASE_URL,
  );
  const [inviteTokenInput, setInviteTokenInput] = useState("");
  const [selfServiceTokenInput, setSelfServiceTokenInput] = useState("");
  const [connectedInviteState, setConnectedInviteState] = useState<ConnectedInviteState | null>(
    null,
  );
  const [selfServiceState, setSelfServiceState] = useState<SelfServiceState | null>(null);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);
  const [selfServiceLoading, setSelfServiceLoading] = useState(false);
  const [claimSubmitting, setClaimSubmitting] = useState(false);
  const [bootstrapError, setBootstrapError] = useState<ApiErrorViewModel | null>(null);
  const [selfServiceError, setSelfServiceError] = useState<ApiErrorViewModel | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const locationConsumedRef = useRef(false);

  const loadSelfServiceState = useCallback(
    async ({
      client,
      inviteToken,
      selfServiceToken,
      source,
    }: {
      client: GroupWorkspaceInviteApiClient;
      inviteToken: string;
      selfServiceToken: string;
      source: Exclude<TokenSource, "path" | "none">;
    }) => {
      const trimmedToken = selfServiceToken.trim();
      if (!trimmedToken) {
        setSelfServiceError({
          kind: "unauthorized_self_service",
          title: "Missing self-service token",
          message: "Paste an existing self-service token before previewing or claiming membership.",
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
        const [preview, memberships] = await Promise.all([
          client.getClaimPreview(inviteToken, trimmedToken),
          client.getWorkspaceMemberships(trimmedToken),
        ]);
        setSelfServiceState({
          token: trimmedToken,
          preview,
          previewViewModel: buildClaimPreviewStatusViewModel(preview),
          memberships,
          claimResponse: null,
          claimViewModel: null,
        });
        setSelfServiceTokenInput("");
      } catch (error) {
        const inviteError =
          error instanceof GroupWorkspaceInviteApiError
            ? buildInviteErrorViewModel(error)
            : buildInviteErrorViewModel({
                kind: "request_failed",
                detail: error instanceof Error ? error.message : String(error),
              });
        setSelfServiceState(null);
        setSelfServiceError(inviteError);
      } finally {
        setSelfServiceLoading(false);
      }
    },
    [],
  );

  const loadInviteState = useCallback(
    async ({
      inviteToken,
      apiBaseUrl,
      source,
      selfServiceToken,
      selfServiceSource,
    }: {
      inviteToken: string;
      apiBaseUrl: string;
      source: Exclude<TokenSource, "none">;
      selfServiceToken?: string | null;
      selfServiceSource?: Exclude<TokenSource, "path" | "none"> | null;
    }) => {
      const trimmedToken = inviteToken.trim();
      const trimmedApiBaseUrl = apiBaseUrl.trim();
      if (!trimmedToken) {
        setBootstrapError({
          kind: "invalid_invite",
          title: "Missing invite token",
          message: "Paste an invite token or open an invite URL first.",
        });
        return;
      }
      if (!trimmedApiBaseUrl) {
        setBootstrapError({
          kind: "request_failed",
          title: "Missing API base URL",
          message: "Set an API base URL before opening an invite.",
        });
        return;
      }

      setBootstrapLoading(true);
      setBootstrapError(null);
      setSelfServiceError(null);
      setSelfServiceState(null);
      setNoticeMessage(
        source === "query" || source === "fragment"
          ? "Invite token was moved from the URL into in-memory state."
          : null,
      );

      const client = apiClientFactory({ apiBaseUrl: trimmedApiBaseUrl });

      try {
        const bootstrap = await client.getInviteBootstrap(trimmedToken);
        const nextInviteState = {
          apiBaseUrl: trimmedApiBaseUrl,
          inviteToken: trimmedToken,
          client,
          bootstrap,
          viewModel: buildInvitePageViewModel(bootstrap),
        };
        setConnectedInviteState(nextInviteState);
        setInviteTokenInput("");

        if (selfServiceToken && selfServiceSource) {
          await loadSelfServiceState({
            client,
            inviteToken: trimmedToken,
            selfServiceToken,
            source: selfServiceSource,
          });
        }
      } catch (error) {
        const inviteError =
          error instanceof GroupWorkspaceInviteApiError
            ? buildInviteErrorViewModel(error)
            : buildInviteErrorViewModel({
                kind: "request_failed",
                detail: error instanceof Error ? error.message : String(error),
              });
        setConnectedInviteState(null);
        setBootstrapError(inviteError);
        setInviteTokenInput(source === "manual" ? trimmedToken : "");
      } finally {
        setBootstrapLoading(false);
      }
    },
    [apiClientFactory, loadSelfServiceState],
  );

  useEffect(() => {
    if (locationConsumedRef.current || !resolvedLocation) {
      return;
    }
    locationConsumedRef.current = true;

    const extracted = extractInviteTokensFromLocation(resolvedLocation);
    const shouldClearVisibleHints =
      (extracted.inviteSource === "query" || extracted.inviteSource === "fragment") ||
      (extracted.selfServiceSource === "query" ||
        extracted.selfServiceSource === "fragment");

    if (shouldClearVisibleHints && resolvedHistory) {
      clearVisibleInviteTokenHints(resolvedLocation, resolvedHistory);
    }

    if (!extracted.inviteToken || extracted.inviteSource === "none") {
      if (extracted.selfServiceToken) {
        setSelfServiceTokenInput("");
        setNoticeMessage(
          "A self-service token was found, but no invite token was present to open.",
        );
      }
      return;
    }

    void loadInviteState({
      inviteToken: extracted.inviteToken,
      apiBaseUrl: apiBaseUrlInput,
      source: extracted.inviteSource,
      selfServiceToken: extracted.selfServiceToken,
      selfServiceSource:
        extracted.selfServiceSource === "query" || extracted.selfServiceSource === "fragment"
          ? extracted.selfServiceSource
          : null,
    });
  }, [apiBaseUrlInput, loadInviteState, resolvedHistory, resolvedLocation]);

  const handleOpenInvite = useCallback(() => {
    void loadInviteState({
      inviteToken: inviteTokenInput,
      apiBaseUrl: apiBaseUrlInput,
      source: "manual",
    });
  }, [apiBaseUrlInput, inviteTokenInput, loadInviteState]);

  const handleConnectSelfService = useCallback(() => {
    if (!connectedInviteState) {
      setSelfServiceError({
        kind: "request_failed",
        title: "Open an invite first",
        message: "Load a public invite bootstrap before connecting a self-service token.",
      });
      return;
    }
    void loadSelfServiceState({
      client: connectedInviteState.client,
      inviteToken: connectedInviteState.inviteToken,
      selfServiceToken: selfServiceTokenInput,
      source: "manual",
    });
  }, [connectedInviteState, loadSelfServiceState, selfServiceTokenInput]);

  const handleClaim = useCallback(async () => {
    if (!connectedInviteState || !selfServiceState) {
      return;
    }
    setClaimSubmitting(true);
    setSelfServiceError(null);
    try {
      const response = await connectedInviteState.client.claimInvite(
        connectedInviteState.inviteToken,
        selfServiceState.token,
      );
      const [preview, memberships] = await Promise.all([
        connectedInviteState.client.getClaimPreview(
          connectedInviteState.inviteToken,
          selfServiceState.token,
        ),
        connectedInviteState.client.getWorkspaceMemberships(selfServiceState.token),
      ]);
      setSelfServiceState({
        ...selfServiceState,
        preview,
        previewViewModel: buildClaimPreviewStatusViewModel(preview),
        memberships,
        claimResponse: response,
        claimViewModel: buildClaimResultStatusViewModel(response),
      });
    } catch (error) {
      const inviteError =
        error instanceof GroupWorkspaceInviteApiError
          ? buildInviteErrorViewModel(error)
          : buildInviteErrorViewModel({
              kind: "request_failed",
              detail: error instanceof Error ? error.message : String(error),
            });
      setSelfServiceError(inviteError);
    } finally {
      setClaimSubmitting(false);
    }
  }, [connectedInviteState, selfServiceState]);

  const handleOpenAnother = useCallback(() => {
    setConnectedInviteState(null);
    setSelfServiceState(null);
    setInviteTokenInput("");
    setSelfServiceTokenInput("");
    setBootstrapError(null);
    setSelfServiceError(null);
    setNoticeMessage("Cleared the in-memory invite and self-service tokens.");
  }, []);

  if (!connectedInviteState) {
    return (
      <InviteTokenEntryView
        apiBaseUrl={apiBaseUrlInput}
        errorMessage={bootstrapError?.message ?? null}
        errorTitle={bootstrapError?.title ?? null}
        inviteToken={inviteTokenInput}
        loading={bootstrapLoading}
        noticeMessage={noticeMessage}
        onApiBaseUrlChange={setApiBaseUrlInput}
        onInviteTokenChange={setInviteTokenInput}
        onSubmit={handleOpenInvite}
      />
    );
  }

  const previewViewModel = selfServiceState?.previewViewModel ?? null;
  const claimViewModel = selfServiceState?.claimViewModel ?? null;
  const canSubmitClaim = previewViewModel?.canClaim === true && !claimSubmitting;

  return (
    <main className="invite-root">
      <InviteSummaryView
        apiBaseUrl={connectedInviteState.apiBaseUrl}
        onOpenAnother={handleOpenAnother}
        viewModel={connectedInviteState.viewModel}
      />

      {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}

      <section className="panel-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Self-service claim</p>
            <h2>Connect an existing self-service token</h2>
          </div>
          <span className="pill">
            {selfServiceState ? "Connected in memory" : "Token required"}
          </span>
        </div>
        <p className="soft-copy">
          This shell does not create a new login system. It only uses the existing subscription
          self-service grant boundary.
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
        <div className="action-row">
          <button disabled={selfServiceLoading} onClick={handleConnectSelfService} type="button">
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

      {previewViewModel ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Claim preview</p>
              <h2>{previewViewModel.title}</h2>
            </div>
            <span className="pill">{previewViewModel.kind}</span>
          </div>
          <p className="status-copy">{previewViewModel.message}</p>
          <div className="subtle-grid">
            <article>
              <p className="eyebrow">Reason codes</p>
              {previewViewModel.reasonCodes.length === 0 ? (
                <p className="soft-copy">No blocking reason codes.</p>
              ) : (
                <ul className="bullet-list">
                  {previewViewModel.reasonCodes.map((reasonCode) => (
                    <li key={reasonCode}>{formatReasonCode(reasonCode)}</li>
                  ))}
                </ul>
              )}
            </article>
            {previewViewModel.membership ? (
              <article>
                <p className="eyebrow">Current membership</p>
                <p>
                  {previewViewModel.membership.workspace_summary.name} · {previewViewModel.membership.role}
                </p>
                <p className="soft-copy">
                  Joined at: {previewViewModel.membership.joined_at}
                </p>
              </article>
            ) : null}
          </div>
          <div className="action-row">
            <button disabled={!canSubmitClaim} onClick={handleClaim} type="button">
              {claimSubmitting ? "Claiming..." : "Claim membership"}
            </button>
          </div>
        </section>
      ) : null}

      {claimViewModel ? (
        <section className="panel-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Claim result</p>
              <h2>{claimViewModel.title}</h2>
            </div>
            <span className="pill">{claimViewModel.kind}</span>
          </div>
          <p className="status-copy">{claimViewModel.message}</p>
          {claimViewModel.reasonCodes.length > 0 ? (
            <ul className="bullet-list">
              {claimViewModel.reasonCodes.map((reasonCode) => (
                <li key={reasonCode}>{formatReasonCode(reasonCode)}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {selfServiceState ? (
        <MembershipListView
          loading={selfServiceLoading}
          memberships={selfServiceState.memberships}
        />
      ) : null}
    </main>
  );
}

export default App;
