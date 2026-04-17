import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import { ConversionDrilldownPanel } from "./components/ConversionDrilldownPanel";
import { ConversionOverviewPanel } from "./components/ConversionOverviewPanel";
import { TokenEntryView } from "./components/TokenEntryView";
import { WorkspaceDetailView } from "./components/WorkspaceDetailView";
import { WorkspaceListPanel } from "./components/WorkspaceListPanel";
import {
  buildApiErrorViewModel,
  buildGlobalConversionDrilldownViewModel,
  buildGlobalConversionOverviewViewModel,
  buildPaperLookupOptions,
  buildShareGrantIssueViewModel,
  buildUserLookupOptions,
  buildWorkspaceBoardViewModel,
  buildWorkspaceConversionDrilldownViewModel,
  buildWorkspaceConversionOverviewViewModel,
  buildWorkspaceListItems,
} from "./lib/adminModel";
import {
  createGroupWorkspaceAdminApiClient,
  GroupWorkspaceAdminApiError,
  type GroupWorkspaceAdminApiClient,
} from "./lib/apiClient";
import {
  clearVisibleAdminTokenHints,
  extractAdminTokenFromLocation,
} from "./lib/token";
import type {
  ApiErrorViewModel,
  GroupWorkspaceBoardRead,
  GroupWorkspaceConversionDrilldownRead,
  GroupWorkspaceConversionOverviewRead,
  GroupWorkspaceRead,
  GroupWorkspaceWorkspaceConversionDrilldownRead,
  GroupWorkspaceWorkspaceConversionOverviewRead,
  PaperProfileRead,
  ResultShareGrantRead,
  ShareGrantOneTimeDisplayModel,
  UserProfileRead,
  WorkspaceBoardShareCreateInput,
  WorkspaceCreateInput,
  WorkspaceMemberAddInput,
  WorkspacePaperAddInput,
  WorkspaceUpdateInput,
} from "./lib/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_GROUP_WORKSPACE_ADMIN_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

type GroupWorkspaceAdminShellProps = {
  initialApiBaseUrl?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  apiClientFactory?: typeof createGroupWorkspaceAdminApiClient;
};

function App() {
  return <GroupWorkspaceAdminShell />;
}

export function GroupWorkspaceAdminShell({
  initialApiBaseUrl,
  locationLike,
  historyLike,
  apiClientFactory = createGroupWorkspaceAdminApiClient,
}: GroupWorkspaceAdminShellProps) {
  const resolvedLocation =
    locationLike ?? (typeof window === "undefined" ? undefined : window.location);
  const resolvedHistory =
    historyLike ?? (typeof window === "undefined" ? undefined : window.history);

  const [apiBaseUrlInput, setApiBaseUrlInput] = useState(
    initialApiBaseUrl ?? DEFAULT_API_BASE_URL,
  );
  const [adminTokenInput, setAdminTokenInput] = useState("");
  const [session, setSession] = useState<{
    apiBaseUrl: string;
    adminToken: string;
    client: GroupWorkspaceAdminApiClient;
  } | null>(null);
  const [workspaces, setWorkspaces] = useState<GroupWorkspaceRead[]>([]);
  const [users, setUsers] = useState<UserProfileRead[]>([]);
  const [papers, setPapers] = useState<PaperProfileRead[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<GroupWorkspaceRead | null>(null);
  const [selectedBoard, setSelectedBoard] = useState<GroupWorkspaceBoardRead | null>(null);
  const [selectedShareGrants, setSelectedShareGrants] = useState<ResultShareGrantRead[]>([]);
  const [globalConversionOverview, setGlobalConversionOverview] =
    useState<GroupWorkspaceConversionOverviewRead | null>(null);
  const [globalConversionDrilldown, setGlobalConversionDrilldown] =
    useState<GroupWorkspaceConversionDrilldownRead | null>(null);
  const [workspaceConversionOverview, setWorkspaceConversionOverview] =
    useState<GroupWorkspaceWorkspaceConversionOverviewRead | null>(null);
  const [workspaceConversionDrilldown, setWorkspaceConversionDrilldown] =
    useState<GroupWorkspaceWorkspaceConversionDrilldownRead | null>(null);
  const [boardCache, setBoardCache] = useState<Record<string, GroupWorkspaceBoardRead | undefined>>(
    {},
  );
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [globalConversionLoading, setGlobalConversionLoading] = useState(false);
  const [globalConversionDrilldownLoading, setGlobalConversionDrilldownLoading] = useState(false);
  const [workspaceConversionLoading, setWorkspaceConversionLoading] = useState(false);
  const [workspaceConversionDrilldownLoading, setWorkspaceConversionDrilldownLoading] =
    useState(false);
  const [connectError, setConnectError] = useState<ApiErrorViewModel | null>(null);
  const [actionError, setActionError] = useState<ApiErrorViewModel | null>(null);
  const [globalConversionError, setGlobalConversionError] = useState<ApiErrorViewModel | null>(null);
  const [globalConversionDrilldownError, setGlobalConversionDrilldownError] =
    useState<ApiErrorViewModel | null>(null);
  const [workspaceConversionError, setWorkspaceConversionError] =
    useState<ApiErrorViewModel | null>(null);
  const [workspaceConversionDrilldownError, setWorkspaceConversionDrilldownError] =
    useState<ApiErrorViewModel | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const [oneTimeGrant, setOneTimeGrant] = useState<ShareGrantOneTimeDisplayModel | null>(null);
  const [createInput, setCreateInput] = useState<WorkspaceCreateInput>({
    slug: "",
    name: "",
    description: "",
  });
  const [updateInput, setUpdateInput] = useState<WorkspaceUpdateInput>({
    name: "",
    description: "",
    status: "active",
  });
  const [memberInput, setMemberInput] = useState<WorkspaceMemberAddInput>({
    user_id: "",
    role: "viewer",
  });
  const [paperInput, setPaperInput] = useState<WorkspacePaperAddInput>({
    paper_id: "",
  });
  const [shareInput, setShareInput] = useState<WorkspaceBoardShareCreateInput>({
    display_label: "",
    expires_at: null,
  });
  const locationConsumedRef = useRef(false);

  const resetConnectedState = useCallback(() => {
    setSession(null);
    setWorkspaces([]);
    setUsers([]);
    setPapers([]);
    setSelectedWorkspaceId(null);
    setSelectedWorkspace(null);
    setSelectedBoard(null);
    setSelectedShareGrants([]);
    setGlobalConversionOverview(null);
    setGlobalConversionDrilldown(null);
    setWorkspaceConversionOverview(null);
    setWorkspaceConversionDrilldown(null);
    setBoardCache({});
    setGlobalConversionError(null);
    setGlobalConversionDrilldownError(null);
    setWorkspaceConversionError(null);
    setWorkspaceConversionDrilldownError(null);
    setOneTimeGrant(null);
  }, []);

  const toApiErrorViewModel = useCallback((error: unknown): ApiErrorViewModel => {
    if (error instanceof GroupWorkspaceAdminApiError) {
      return buildApiErrorViewModel(error);
    }
    return buildApiErrorViewModel({
      kind: "request_failed",
      detail: error instanceof Error ? error.message : String(error),
    });
  }, []);

  const handleError = useCallback(
    (error: unknown, setter: (error: ApiErrorViewModel | null) => void) => {
      setter(toApiErrorViewModel(error));
    },
    [toApiErrorViewModel],
  );

  const loadWorkspaceContext = useCallback(
    async (client: GroupWorkspaceAdminApiClient, workspaceId: string) => {
      setLoadingMessage("Loading workspace detail and board...");
      setActionError(null);
      setWorkspaceConversionLoading(true);
      setWorkspaceConversionDrilldownLoading(true);
      setWorkspaceConversionError(null);
      setWorkspaceConversionDrilldownError(null);
      try {
        const [workspace, board, shareGrants, conversionResult, drilldownResult] = await Promise.all([
          client.getWorkspace(workspaceId),
          client.getWorkspaceBoard(workspaceId),
          client.listResultShareGrants({
            workspaceId,
            shareKind: "workspace_board",
          }),
          client
            .getWorkspaceConversionOverview(workspaceId)
            .then((conversion) => ({ conversion, error: null }))
            .catch((error: unknown) => ({
              conversion: null,
              error: toApiErrorViewModel(error),
            })),
          client
            .getWorkspaceConversionDrilldown(workspaceId)
            .then((drilldown) => ({ drilldown, error: null }))
            .catch((error: unknown) => ({
              drilldown: null,
              error: toApiErrorViewModel(error),
            })),
        ]);
        setSelectedWorkspaceId(workspaceId);
        setSelectedWorkspace(workspace);
        setSelectedBoard(board);
        setSelectedShareGrants(shareGrants);
        setWorkspaceConversionOverview(conversionResult.conversion);
        setWorkspaceConversionError(conversionResult.error);
        setWorkspaceConversionDrilldown(drilldownResult.drilldown);
        setWorkspaceConversionDrilldownError(drilldownResult.error);
        setUpdateInput({
          name: workspace.name,
          description: workspace.description ?? "",
          status: workspace.status,
        });
        setBoardCache((current) => ({
          ...current,
          [workspaceId]: board,
        }));
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setWorkspaceConversionLoading(false);
        setWorkspaceConversionDrilldownLoading(false);
        setLoadingMessage(null);
      }
    },
    [handleError, toApiErrorViewModel],
  );

  const connectWithToken = useCallback(
    async ({
      adminToken,
      apiBaseUrl,
      source,
    }: {
      adminToken: string;
      apiBaseUrl: string;
      source: "manual" | "query" | "fragment";
    }) => {
      const trimmedToken = adminToken.trim();
      const trimmedApiBaseUrl = apiBaseUrl.trim();
      if (!trimmedToken) {
        setConnectError({
          kind: "unauthorized",
          title: "Missing admin bearer token",
          message: "Paste an admin/operator bearer token from POST /auth/login.",
        });
        return;
      }
      if (!trimmedApiBaseUrl) {
        setConnectError({
          kind: "request_failed",
          title: "Missing API base URL",
          message: "Set an API base URL before opening the workspace shell.",
        });
        return;
      }

      setLoadingMessage("Connecting admin shell...");
      setGlobalConversionLoading(true);
      setGlobalConversionDrilldownLoading(true);
      setConnectError(null);
      setActionError(null);
      setGlobalConversionError(null);
      setGlobalConversionDrilldownError(null);
      setNoticeMessage(
        source === "query" || source === "fragment"
          ? "Admin bearer token was moved from the URL into in-memory state."
          : null,
      );

      const client = apiClientFactory({
        apiBaseUrl: trimmedApiBaseUrl,
        accessToken: trimmedToken,
      });

      try {
        const [workspaceList, userList, paperList, globalConversion, globalDrilldown] =
          await Promise.all([
          client.listWorkspaces(),
          client.listUsers(),
          client.listPapers(),
          client
            .getConversionOverview()
            .then((overview) => ({ overview, error: null }))
            .catch((error: unknown) => ({
              overview: null,
              error: toApiErrorViewModel(error),
            })),
            client
              .getConversionDrilldown()
              .then((drilldown) => ({ drilldown, error: null }))
              .catch((error: unknown) => ({
                drilldown: null,
                error: toApiErrorViewModel(error),
              })),
          ]);
        setSession({
          apiBaseUrl: trimmedApiBaseUrl,
          adminToken: trimmedToken,
          client,
        });
        setWorkspaces(workspaceList);
        setUsers(userList);
        setPapers(paperList);
        setGlobalConversionOverview(globalConversion.overview);
        setGlobalConversionError(globalConversion.error);
        setGlobalConversionDrilldown(globalDrilldown.drilldown);
        setGlobalConversionDrilldownError(globalDrilldown.error);
        setAdminTokenInput("");

        const initialWorkspaceId = workspaceList[0]?.id ?? null;
        if (initialWorkspaceId) {
          await loadWorkspaceContext(client, initialWorkspaceId);
        } else {
          setSelectedWorkspaceId(null);
          setSelectedWorkspace(null);
          setSelectedBoard(null);
          setSelectedShareGrants([]);
          setWorkspaceConversionOverview(null);
          setWorkspaceConversionDrilldown(null);
        }
      } catch (error) {
        resetConnectedState();
        handleError(error, setConnectError);
        setAdminTokenInput(source === "manual" ? trimmedToken : "");
      } finally {
        setGlobalConversionLoading(false);
        setGlobalConversionDrilldownLoading(false);
        setLoadingMessage(null);
      }
    },
    [apiClientFactory, handleError, loadWorkspaceContext, resetConnectedState, toApiErrorViewModel],
  );

  useEffect(() => {
    if (locationConsumedRef.current || !resolvedLocation) {
      return;
    }
    locationConsumedRef.current = true;
    const extracted = extractAdminTokenFromLocation(resolvedLocation);
    if (!extracted.adminToken || extracted.source === "none") {
      return;
    }

    if (
      resolvedHistory &&
      (extracted.source === "query" || extracted.source === "fragment")
    ) {
      clearVisibleAdminTokenHints(resolvedLocation, resolvedHistory);
    }

    void connectWithToken({
      adminToken: extracted.adminToken,
      apiBaseUrl: apiBaseUrlInput,
      source: extracted.source,
    });
  }, [apiBaseUrlInput, connectWithToken, resolvedHistory, resolvedLocation]);

  const refreshWorkspaces = useCallback(async () => {
    if (!session) {
      return;
    }
    const latest = await session.client.listWorkspaces();
    setWorkspaces(latest);
    return latest;
  }, [session]);

  const refreshWorkspaceContext = useCallback(async () => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    await loadWorkspaceContext(session.client, selectedWorkspaceId);
  }, [loadWorkspaceContext, selectedWorkspaceId, session]);

  const availableUserOptions = useMemo(() => {
    const currentMemberIds = new Set((selectedBoard?.members ?? []).map((member) => member.user_id));
    return buildUserLookupOptions(users.filter((user) => !currentMemberIds.has(user.id)));
  }, [selectedBoard, users]);

  const availablePaperOptions = useMemo(() => {
    const currentPaperIds = new Set((selectedBoard?.papers ?? []).map((paper) => paper.paper_id));
    return buildPaperLookupOptions(papers.filter((paper) => !currentPaperIds.has(paper.id)));
  }, [papers, selectedBoard]);

  const workspaceListItems = useMemo(
    () => buildWorkspaceListItems(workspaces, boardCache),
    [boardCache, workspaces],
  );

  const boardViewModel = useMemo(
    () => (selectedBoard ? buildWorkspaceBoardViewModel(selectedBoard) : null),
    [selectedBoard],
  );
  const globalConversionViewModel = useMemo(
    () =>
      globalConversionOverview
        ? buildGlobalConversionOverviewViewModel(globalConversionOverview)
        : null,
    [globalConversionOverview],
  );
  const globalConversionDrilldownViewModel = useMemo(
    () =>
      globalConversionDrilldown
        ? buildGlobalConversionDrilldownViewModel(globalConversionDrilldown)
        : null,
    [globalConversionDrilldown],
  );
  const workspaceConversionViewModel = useMemo(
    () =>
      workspaceConversionOverview
        ? buildWorkspaceConversionOverviewViewModel(workspaceConversionOverview)
        : null,
    [workspaceConversionOverview],
  );
  const workspaceConversionDrilldownViewModel = useMemo(
    () =>
      workspaceConversionDrilldown
        ? buildWorkspaceConversionDrilldownViewModel(workspaceConversionDrilldown)
        : null,
    [workspaceConversionDrilldown],
  );

  const handleOpenShell = useCallback(() => {
    void connectWithToken({
      adminToken: adminTokenInput,
      apiBaseUrl: apiBaseUrlInput,
      source: "manual",
    });
  }, [adminTokenInput, apiBaseUrlInput, connectWithToken]);

  const handleDisconnect = useCallback(() => {
    resetConnectedState();
    setAdminTokenInput("");
    setConnectError(null);
    setActionError(null);
    setNoticeMessage("Cleared the in-memory admin bearer token.");
  }, [resetConnectedState]);

  const runAction = useCallback(
    async (message: string, action: () => Promise<void>) => {
      setLoadingMessage(message);
      setActionError(null);
      try {
        await action();
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError],
  );

  const handleCreateWorkspace = useCallback(() => {
    if (!session) {
      return;
    }
    void runAction("Creating workspace...", async () => {
      const created = await session.client.createWorkspace(createInput);
      const latest = (await refreshWorkspaces()) ?? [];
      setCreateInput({ slug: "", name: "", description: "" });
      setNoticeMessage(`Created workspace ${created.name}.`);
      const selected = latest.find((workspace) => workspace.id === created.id)?.id ?? created.id;
      await loadWorkspaceContext(session.client, selected);
    });
  }, [createInput, loadWorkspaceContext, refreshWorkspaces, runAction, session]);

  const handleSaveWorkspace = useCallback(() => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    void runAction("Saving workspace...", async () => {
      await session.client.updateWorkspace(selectedWorkspaceId, {
        name: updateInput.name,
        description: updateInput.description,
        status: updateInput.status,
      });
      await refreshWorkspaces();
      await refreshWorkspaceContext();
      setNoticeMessage("Saved workspace summary.");
    });
  }, [refreshWorkspaceContext, refreshWorkspaces, runAction, selectedWorkspaceId, session, updateInput]);

  const handleAddMember = useCallback(() => {
    if (!session || !selectedWorkspaceId || !memberInput.user_id) {
      return;
    }
    void runAction("Adding workspace member...", async () => {
      await session.client.addWorkspaceMember(selectedWorkspaceId, memberInput);
      setMemberInput({ user_id: "", role: "viewer" });
      await refreshWorkspaceContext();
      setNoticeMessage("Added workspace member.");
    });
  }, [memberInput, refreshWorkspaceContext, runAction, selectedWorkspaceId, session]);

  const handleRemoveMember = useCallback(
    (memberId: string) => {
      if (!session || !selectedWorkspaceId) {
        return;
      }
      void runAction("Removing workspace member...", async () => {
        await session.client.removeWorkspaceMember(selectedWorkspaceId, memberId);
        await refreshWorkspaceContext();
        setNoticeMessage("Removed workspace member.");
      });
    },
    [refreshWorkspaceContext, runAction, selectedWorkspaceId, session],
  );

  const handleAddPaper = useCallback(() => {
    if (!session || !selectedWorkspaceId || !paperInput.paper_id) {
      return;
    }
    void runAction("Adding workspace paper...", async () => {
      await session.client.addWorkspacePaper(selectedWorkspaceId, paperInput);
      setPaperInput({ paper_id: "" });
      await refreshWorkspaceContext();
      setNoticeMessage("Added paper to workspace.");
    });
  }, [paperInput, refreshWorkspaceContext, runAction, selectedWorkspaceId, session]);

  const handleRemovePaper = useCallback(
    (paperId: string) => {
      if (!session || !selectedWorkspaceId) {
        return;
      }
      void runAction("Removing workspace paper...", async () => {
        await session.client.removeWorkspacePaper(selectedWorkspaceId, paperId);
        await refreshWorkspaceContext();
        setNoticeMessage("Removed paper from workspace.");
      });
    },
    [refreshWorkspaceContext, runAction, selectedWorkspaceId, session],
  );

  const handleCreateShareGrant = useCallback(() => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    void runAction("Issuing workspace_board share grant...", async () => {
      const issued = await session.client.createWorkspaceBoardShareGrant(selectedWorkspaceId, {
        display_label: shareInput.display_label.trim(),
        expires_at: shareInput.expires_at ? new Date(shareInput.expires_at).toISOString() : null,
      });
      setOneTimeGrant(buildShareGrantIssueViewModel(issued));
      setShareInput({ display_label: "", expires_at: null });
      await refreshWorkspaceContext();
      setNoticeMessage("Issued workspace_board share grant.");
    });
  }, [refreshWorkspaceContext, runAction, selectedWorkspaceId, session, shareInput]);

  const handleRevokeShareGrant = useCallback(
    (grantId: string) => {
      if (!session) {
        return;
      }
      void runAction("Revoking share grant...", async () => {
        await session.client.revokeResultShareGrant(grantId);
        await refreshWorkspaceContext();
        setNoticeMessage("Revoked workspace_board share grant.");
      });
    },
    [refreshWorkspaceContext, runAction, session],
  );

  if (!session) {
    return (
      <TokenEntryView
        apiBaseUrl={apiBaseUrlInput}
        adminToken={adminTokenInput}
        loading={loadingMessage !== null}
        errorTitle={connectError?.title ?? null}
        errorMessage={connectError?.message ?? null}
        noticeMessage={noticeMessage}
        onApiBaseUrlChange={setApiBaseUrlInput}
        onAdminTokenChange={setAdminTokenInput}
        onSubmit={handleOpenShell}
      />
    );
  }

  return (
    <main className="admin-shell-root">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Internal Workspace Admin</p>
          <h1>Group workspaces and workspace-board shares</h1>
          <p className="lede">
            This internal shell manages structured group workspaces only. It does not expose
            source files, local attachments, or local note contents.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>API base</span>
            <strong>{session.apiBaseUrl}</strong>
          </div>
          <div className="hero-chip">
            <span>Workspaces</span>
            <strong>{workspaces.length}</strong>
          </div>
          <button type="button" className="button-secondary" onClick={handleDisconnect}>
            Disconnect
          </button>
        </div>
      </section>

      {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
      {actionError ? (
        <div className="inline-banner error" role="alert">
          <strong>{actionError.title}</strong>
          <span>{actionError.message}</span>
        </div>
      ) : null}
      {loadingMessage ? <div className="inline-banner info">{loadingMessage}</div> : null}

      <ConversionOverviewPanel
        eyebrow="Conversion dashboard"
        title="Global conversion overview"
        description="Read-only aggregate signals across public share views, handoff redirects, invite claims, and result collect records."
        summaryMetrics={globalConversionViewModel?.summaryMetrics ?? []}
        sections={globalConversionViewModel?.sections ?? []}
        attributionScope={globalConversionViewModel?.attributionScope ?? null}
        windowStart={globalConversionViewModel?.windowStart ?? null}
        windowEnd={globalConversionViewModel?.windowEnd ?? null}
        lastActivityAt={globalConversionViewModel?.lastActivityAt ?? null}
        loading={globalConversionLoading}
        error={globalConversionError}
        empty={globalConversionViewModel?.empty ?? !globalConversionLoading}
        emptyMessage="No share, invite, or collect activity has been recorded in this analytics window."
      />

      <ConversionDrilldownPanel
        eyebrow="Conversion drilldown"
        title="Global conversion drilldown"
        description="Read-only daily buckets, recent activity, top workspaces, and top result-share grants across the existing admin-safe drilldown reserve."
        summaryMetrics={globalConversionDrilldownViewModel?.summaryMetrics ?? []}
        windowStart={globalConversionDrilldownViewModel?.windowStart ?? null}
        windowEnd={globalConversionDrilldownViewModel?.windowEnd ?? null}
        lastActivityAt={globalConversionDrilldownViewModel?.lastActivityAt ?? null}
        dailyBuckets={globalConversionDrilldownViewModel?.dailyBuckets ?? []}
        topWorkspaces={globalConversionDrilldownViewModel?.topWorkspaces ?? []}
        topResultShareGrants={globalConversionDrilldownViewModel?.topResultShareGrants ?? []}
        recentShareEvents={globalConversionDrilldownViewModel?.recentShareEvents ?? []}
        recentInviteClaims={globalConversionDrilldownViewModel?.recentInviteClaims ?? []}
        recentCollectRecords={globalConversionDrilldownViewModel?.recentCollectRecords ?? []}
        attributionScope={globalConversionDrilldownViewModel?.attributionScope ?? null}
        notes={globalConversionDrilldownViewModel?.notes ?? []}
        loading={globalConversionDrilldownLoading}
        error={globalConversionDrilldownError}
        empty={globalConversionDrilldownViewModel?.empty ?? !globalConversionDrilldownLoading}
        emptyMessage="No global drilldown activity has been recorded in this analytics window."
      />

      <section className="admin-shell-grid">
        <WorkspaceListPanel
          items={workspaceListItems}
          selectedWorkspaceId={selectedWorkspaceId}
          createInput={createInput}
          loading={loadingMessage !== null}
          onSelect={(workspaceId) => {
            if (!session) {
              return;
            }
            void loadWorkspaceContext(session.client, workspaceId);
          }}
          onCreateInputChange={(patch) =>
            setCreateInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onCreate={handleCreateWorkspace}
        />

        <WorkspaceDetailView
          workspace={selectedWorkspace}
          board={boardViewModel}
          updateInput={updateInput}
          memberInput={memberInput}
          paperInput={paperInput}
          shareInput={shareInput}
          userOptions={availableUserOptions}
          paperOptions={availablePaperOptions}
          shareGrants={selectedShareGrants}
          conversionOverview={workspaceConversionViewModel}
          conversionError={workspaceConversionError}
          conversionLoading={workspaceConversionLoading}
          conversionDrilldown={workspaceConversionDrilldownViewModel}
          conversionDrilldownError={workspaceConversionDrilldownError}
          conversionDrilldownLoading={workspaceConversionDrilldownLoading}
          actionLoading={loadingMessage !== null}
          oneTimeGrant={oneTimeGrant}
          onUpdateInputChange={(patch) =>
            setUpdateInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onMemberInputChange={(patch) =>
            setMemberInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onPaperInputChange={(patch) =>
            setPaperInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onShareInputChange={(patch) =>
            setShareInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onSaveWorkspace={handleSaveWorkspace}
          onAddMember={handleAddMember}
          onRemoveMember={handleRemoveMember}
          onAddPaper={handleAddPaper}
          onRemovePaper={handleRemovePaper}
          onCreateShareGrant={handleCreateShareGrant}
          onRevokeShareGrant={handleRevokeShareGrant}
          onDismissOneTimeGrant={() => setOneTimeGrant(null)}
        />
      </section>
    </main>
  );
}

export default App;
