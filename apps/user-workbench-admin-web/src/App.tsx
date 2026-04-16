import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import { PaperDetailView } from "./components/PaperDetailView";
import { TokenEntryView } from "./components/TokenEntryView";
import { UserDetailView } from "./components/UserDetailView";
import { UserListPanel } from "./components/UserListPanel";
import { WatchProfileExplorer } from "./components/WatchProfileExplorer";
import {
  createUserWorkbenchAdminApiClient,
  UserWorkbenchAdminApiError,
  type UserWorkbenchAdminApiClient,
} from "./lib/apiClient";
import {
  buildApiErrorViewModel,
  buildPaperCardViewModels,
  buildUserCardViewModels,
  buildWatchProfileCardViewModels,
} from "./lib/workbenchModel";
import {
  clearVisibleAdminTokenHints,
  extractAdminTokenFromLocation,
} from "./lib/token";
import type {
  ApiErrorViewModel,
  UserWorkbenchPaperDetailRead,
  UserWorkbenchPapersQuery,
  UserWorkbenchUserDetailRead,
  UserWorkbenchUserSummaryRead,
  UserWorkbenchWatchProfileRead,
  UserWorkbenchWatchProfilesQuery,
} from "./lib/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_USER_WORKBENCH_ADMIN_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

type ActiveView = "users" | "papers" | "watch-profiles";

type UserWorkbenchAdminShellProps = {
  initialApiBaseUrl?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  apiClientFactory?: typeof createUserWorkbenchAdminApiClient;
};

function App() {
  return <UserWorkbenchAdminShell />;
}

export function UserWorkbenchAdminShell({
  initialApiBaseUrl,
  locationLike,
  historyLike,
  apiClientFactory = createUserWorkbenchAdminApiClient,
}: UserWorkbenchAdminShellProps) {
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
    client: UserWorkbenchAdminApiClient;
  } | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>("users");
  const [users, setUsers] = useState<UserWorkbenchUserSummaryRead[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedUserDetail, setSelectedUserDetail] = useState<UserWorkbenchUserDetailRead | null>(
    null,
  );
  const [papers, setPapers] = useState<UserWorkbenchPaperDetailRead["paper"][]>([]);
  const [paperFilters, setPaperFilters] = useState<UserWorkbenchPapersQuery>({
    q: "",
    userId: "",
    stage: "",
    type: "",
    limit: 25,
  });
  const [selectedPaperDetail, setSelectedPaperDetail] =
    useState<UserWorkbenchPaperDetailRead | null>(null);
  const [watchProfiles, setWatchProfiles] = useState<UserWorkbenchWatchProfileRead[]>([]);
  const [watchFilters, setWatchFilters] = useState<UserWorkbenchWatchProfilesQuery>({});
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [connectError, setConnectError] = useState<ApiErrorViewModel | null>(null);
  const [actionError, setActionError] = useState<ApiErrorViewModel | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const locationConsumedRef = useRef(false);

  const userCards = useMemo(() => buildUserCardViewModels(users), [users]);
  const paperCards = useMemo(() => buildPaperCardViewModels(papers), [papers]);
  const watchCards = useMemo(
    () => buildWatchProfileCardViewModels(watchProfiles),
    [watchProfiles],
  );

  const resetConnectedState = useCallback(() => {
    setSession(null);
    setUsers([]);
    setSelectedUserId(null);
    setSelectedUserDetail(null);
    setPapers([]);
    setSelectedPaperDetail(null);
    setWatchProfiles([]);
  }, []);

  const handleError = useCallback(
    (error: unknown, setter: (error: ApiErrorViewModel | null) => void) => {
      if (error instanceof UserWorkbenchAdminApiError) {
        setter(buildApiErrorViewModel(error));
        return;
      }
      setter(
        buildApiErrorViewModel({
          kind: "request_failed",
          detail: error instanceof Error ? error.message : String(error),
        }),
      );
    },
    [],
  );

  const loadUserList = useCallback(
    async (
      client: UserWorkbenchAdminApiClient,
      query: string,
      {
        preserveSelection = true,
      }: {
        preserveSelection?: boolean;
      } = {},
    ) => {
      setLoadingMessage("Loading users...");
      setActionError(null);
      try {
        const nextUsers = await client.listUsers({
          q: query || undefined,
          limit: 25,
        });
        setUsers(nextUsers);
        if (!preserveSelection || !nextUsers.some((item) => item.id === selectedUserId)) {
          const nextSelectedId = nextUsers[0]?.id ?? null;
          setSelectedUserId(nextSelectedId);
          if (nextSelectedId) {
            const detail = await client.getUserDetail(nextSelectedId);
            setSelectedUserDetail(detail);
          } else {
            setSelectedUserDetail(null);
          }
        }
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError, selectedUserId],
  );

  const loadUserDetail = useCallback(
    async (client: UserWorkbenchAdminApiClient, userId: string) => {
      setLoadingMessage("Loading user detail...");
      setActionError(null);
      try {
        const detail = await client.getUserDetail(userId);
        setSelectedUserId(userId);
        setSelectedUserDetail(detail);
        setActiveView("users");
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError],
  );

  const loadPapers = useCallback(
    async (client: UserWorkbenchAdminApiClient, filters: UserWorkbenchPapersQuery) => {
      setLoadingMessage("Loading papers...");
      setActionError(null);
      try {
        const paperList = await client.listPapers({
          q: filters.q || undefined,
          userId: filters.userId || undefined,
          stage: filters.stage || undefined,
          type: filters.type || undefined,
          limit: 25,
        });
        setPapers(paperList);
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError],
  );

  const loadPaperDetail = useCallback(
    async (client: UserWorkbenchAdminApiClient, paperId: string) => {
      setLoadingMessage("Loading paper detail...");
      setActionError(null);
      try {
        const detail = await client.getPaperDetail(paperId);
        setSelectedPaperDetail(detail);
        setActiveView("papers");
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError],
  );

  const loadWatchProfiles = useCallback(
    async (client: UserWorkbenchAdminApiClient, filters: UserWorkbenchWatchProfilesQuery) => {
      setLoadingMessage("Loading watch profiles...");
      setActionError(null);
      try {
        const profiles = await client.listWatchProfiles({
          userId: filters.userId || undefined,
          paperId: filters.paperId || undefined,
          enabled: filters.enabled,
          q: filters.q || undefined,
        });
        setWatchProfiles(profiles);
        setActiveView("watch-profiles");
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
          message: "Paste a valid viewer/operator/super_admin bearer token from POST /auth/login.",
        });
        return;
      }
      if (!trimmedApiBaseUrl) {
        setConnectError({
          kind: "request_failed",
          title: "Missing API base URL",
          message: "Set an API base URL before opening the workbench.",
        });
        return;
      }

      setLoadingMessage("Connecting user workbench...");
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
        const listedUsers = await client.listUsers({ limit: 25 });
        setSession({
          apiBaseUrl: trimmedApiBaseUrl,
          adminToken: trimmedToken,
          client,
        });
        setUsers(listedUsers);
        setAdminTokenInput("");
        setActiveView("users");
        const initialUserId = listedUsers[0]?.id ?? null;
        setSelectedUserId(initialUserId);
        if (initialUserId) {
          const detail = await client.getUserDetail(initialUserId);
          setSelectedUserDetail(detail);
        } else {
          setSelectedUserDetail(null);
        }
      } catch (error) {
        resetConnectedState();
        handleError(error, setConnectError);
        setAdminTokenInput(source === "manual" ? trimmedToken : "");
      } finally {
        setLoadingMessage(null);
      }
    },
    [apiClientFactory, handleError, resetConnectedState],
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
    if (resolvedHistory) {
      clearVisibleAdminTokenHints(
        {
          pathname: resolvedLocation.pathname,
          search: resolvedLocation.search,
          hash: resolvedLocation.hash,
        },
        resolvedHistory,
      );
    }
    void connectWithToken({
      adminToken: extracted.adminToken,
      apiBaseUrl: apiBaseUrlInput,
      source: extracted.source,
    });
  }, [apiBaseUrlInput, connectWithToken, resolvedHistory, resolvedLocation]);

  const handleManualConnect = useCallback(() => {
    void connectWithToken({
      adminToken: adminTokenInput,
      apiBaseUrl: apiBaseUrlInput,
      source: "manual",
    });
  }, [adminTokenInput, apiBaseUrlInput, connectWithToken]);

  const handleOpenPapers = useCallback(() => {
    if (!session) {
      return;
    }
    setActiveView("papers");
    void loadPapers(session.client, paperFilters);
  }, [loadPapers, paperFilters, session]);

  const handleOpenWatchProfiles = useCallback(() => {
    if (!session) {
      return;
    }
    setActiveView("watch-profiles");
    void loadWatchProfiles(session.client, watchFilters);
  }, [loadWatchProfiles, session, watchFilters]);

  const handleOpenWatchProfilesForUser = useCallback(
    (userId: string) => {
      if (!session) {
        return;
      }
      const nextFilters = {
        userId,
        paperId: undefined,
        enabled: undefined,
        q: undefined,
      };
      setWatchFilters(nextFilters);
      void loadWatchProfiles(session.client, nextFilters);
    },
    [loadWatchProfiles, session],
  );

  const handleOpenWatchProfilesForPaper = useCallback(
    (paperId: string) => {
      if (!session) {
        return;
      }
      const nextFilters = {
        userId: undefined,
        paperId,
        enabled: undefined,
        q: undefined,
      };
      setWatchFilters(nextFilters);
      void loadWatchProfiles(session.client, nextFilters);
    },
    [loadWatchProfiles, session],
  );

  if (!session) {
    return (
      <>
        {connectError ? (
          <div className="connect-shell">
            <div className="inline-banner error">
              <strong>{connectError.title}</strong>
              <span>{connectError.message}</span>
            </div>
          </div>
        ) : null}
        <TokenEntryView
          apiBaseUrl={apiBaseUrlInput}
          adminToken={adminTokenInput}
          loading={Boolean(loadingMessage)}
          onApiBaseUrlChange={setApiBaseUrlInput}
          onAdminTokenChange={setAdminTokenInput}
          onConnect={handleManualConnect}
        />
      </>
    );
  }

  return (
    <div className="workbench-shell-root">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Internal user workbench</p>
          <h1>Read-only search across users, papers, and watch profiles</h1>
          <p className="lede">
            This shell stays within admin auth, keeps bearer tokens in memory only, and excludes
            file-level data, note contents, and local attachment paths.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>API base</span>
            <strong>{session.apiBaseUrl}</strong>
          </div>
          <div className="hero-chip">
            <span>Active view</span>
            <strong>{activeView}</strong>
          </div>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              resetConnectedState();
              setNoticeMessage("Disconnected the in-memory admin session.");
            }}
          >
            Disconnect
          </button>
        </div>
      </section>

      {noticeMessage ? (
        <div className="inline-banner info">
          <strong>Notice</strong>
          <span>{noticeMessage}</span>
        </div>
      ) : null}
      {loadingMessage ? (
        <div className="inline-banner info">
          <strong>Loading</strong>
          <span>{loadingMessage}</span>
        </div>
      ) : null}
      {actionError ? (
        <div className="inline-banner error">
          <strong>{actionError.title}</strong>
          <span>{actionError.message}</span>
        </div>
      ) : null}

      <div className="workbench-shell-grid">
        <UserListPanel
          search={userSearch}
          items={userCards}
          selectedUserId={selectedUserId}
          loading={Boolean(loadingMessage)}
          onSearchChange={setUserSearch}
          onSearchSubmit={() => void loadUserList(session.client, userSearch, { preserveSelection: false })}
          onSelect={(userId) => void loadUserDetail(session.client, userId)}
          onOpenPapers={handleOpenPapers}
          onOpenWatchProfiles={handleOpenWatchProfiles}
        />

        <main className="detail-root">
          <div className="tab-row">
            <button
              type="button"
              className={activeView === "users" ? "tab-button active" : "tab-button"}
              onClick={() => setActiveView("users")}
            >
              User detail
            </button>
            <button
              type="button"
              className={activeView === "papers" ? "tab-button active" : "tab-button"}
              onClick={handleOpenPapers}
            >
              Paper explorer
            </button>
            <button
              type="button"
              className={activeView === "watch-profiles" ? "tab-button active" : "tab-button"}
              onClick={handleOpenWatchProfiles}
            >
              Watch profile explorer
            </button>
          </div>

          {activeView === "users" ? (
            <UserDetailView
              detail={selectedUserDetail}
              loading={Boolean(loadingMessage)}
              onOpenPaper={(paperId) => void loadPaperDetail(session.client, paperId)}
              onOpenWatchProfilesForUser={handleOpenWatchProfilesForUser}
            />
          ) : null}

          {activeView === "papers" ? (
            <PaperDetailView
              search={paperFilters.q ?? ""}
              stage={paperFilters.stage ?? ""}
              typeFilter={paperFilters.type ?? ""}
              userIdFilter={paperFilters.userId ?? ""}
              listItems={paperCards}
              detail={selectedPaperDetail}
              loading={Boolean(loadingMessage)}
              onSearchChange={(value) =>
                setPaperFilters((current) => ({
                  ...current,
                  q: value,
                }))
              }
              onStageChange={(value) =>
                setPaperFilters((current) => ({
                  ...current,
                  stage: value,
                }))
              }
              onTypeChange={(value) =>
                setPaperFilters((current) => ({
                  ...current,
                  type: value,
                }))
              }
              onUserIdFilterChange={(value) =>
                setPaperFilters((current) => ({
                  ...current,
                  userId: value,
                }))
              }
              onSearchSubmit={() => void loadPapers(session.client, paperFilters)}
              onSelectPaper={(paperId) => void loadPaperDetail(session.client, paperId)}
              onOpenWatchProfilesForPaper={handleOpenWatchProfilesForPaper}
            />
          ) : null}

          {activeView === "watch-profiles" ? (
            <WatchProfileExplorer
              filters={watchFilters}
              items={watchCards}
              loading={Boolean(loadingMessage)}
              onFiltersChange={(patch) =>
                setWatchFilters((current) => ({
                  ...current,
                  ...patch,
                }))
              }
              onSearch={() => void loadWatchProfiles(session.client, watchFilters)}
              onOpenUser={(userId) => void loadUserDetail(session.client, userId)}
              onOpenPaper={(paperId) => void loadPaperDetail(session.client, paperId)}
            />
          ) : null}
        </main>
      </div>
    </div>
  );
}

export default App;
