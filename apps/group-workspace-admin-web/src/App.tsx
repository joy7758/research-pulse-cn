import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import { TokenEntryView } from "./components/TokenEntryView";
import { WorkspaceDetailView } from "./components/WorkspaceDetailView";
import { WorkspaceListPanel } from "./components/WorkspaceListPanel";
import {
  buildApiErrorViewModel,
  buildPaperLookupOptions,
  buildShareGrantIssueViewModel,
  buildUserLookupOptions,
  buildWorkspaceBoardViewModel,
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
  GroupWorkspaceRead,
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
  const [boardCache, setBoardCache] = useState<Record<string, GroupWorkspaceBoardRead | undefined>>(
    {},
  );
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [connectError, setConnectError] = useState<ApiErrorViewModel | null>(null);
  const [actionError, setActionError] = useState<ApiErrorViewModel | null>(null);
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
    setBoardCache({});
    setOneTimeGrant(null);
  }, []);

  const handleError = useCallback((error: unknown, setter: (error: ApiErrorViewModel | null) => void) => {
    if (error instanceof GroupWorkspaceAdminApiError) {
      setter(buildApiErrorViewModel(error));
      return;
    }
    setter(
      buildApiErrorViewModel({
        kind: "request_failed",
        detail: error instanceof Error ? error.message : String(error),
      }),
    );
  }, []);

  const loadWorkspaceContext = useCallback(
    async (client: GroupWorkspaceAdminApiClient, workspaceId: string) => {
      setLoadingMessage("Loading workspace detail and board...");
      setActionError(null);
      try {
        const [workspace, board, shareGrants] = await Promise.all([
          client.getWorkspace(workspaceId),
          client.getWorkspaceBoard(workspaceId),
          client.listResultShareGrants({
            workspaceId,
            shareKind: "workspace_board",
          }),
        ]);
        setSelectedWorkspaceId(workspaceId);
        setSelectedWorkspace(workspace);
        setSelectedBoard(board);
        setSelectedShareGrants(shareGrants);
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
        setLoadingMessage(null);
      }
    },
    [handleError],
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
      setConnectError(null);
      setActionError(null);
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
        const [workspaceList, userList, paperList] = await Promise.all([
          client.listWorkspaces(),
          client.listUsers(),
          client.listPapers(),
        ]);
        setSession({
          apiBaseUrl: trimmedApiBaseUrl,
          adminToken: trimmedToken,
          client,
        });
        setWorkspaces(workspaceList);
        setUsers(userList);
        setPapers(paperList);
        setAdminTokenInput("");

        const initialWorkspaceId = workspaceList[0]?.id ?? null;
        if (initialWorkspaceId) {
          await loadWorkspaceContext(client, initialWorkspaceId);
        } else {
          setSelectedWorkspaceId(null);
          setSelectedWorkspace(null);
          setSelectedBoard(null);
          setSelectedShareGrants([]);
        }
      } catch (error) {
        resetConnectedState();
        handleError(error, setConnectError);
        setAdminTokenInput(source === "manual" ? trimmedToken : "");
      } finally {
        setLoadingMessage(null);
      }
    },
    [apiClientFactory, handleError, loadWorkspaceContext, resetConnectedState],
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
