import { useCallback, useEffect, useMemo, useState } from "react";
import {
  HashRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";

import "./App.css";
import { desktopApi } from "./lib/desktopApi";
import { buildTodayEmptyState, sortPapers } from "./lib/readModels";
import type {
  ConnectDeviceInput,
  ListPapersInput,
  PaperDetailRead,
  PaperListItemRead,
  SyncStatusRead,
  TodayOverviewRead,
} from "./lib/types";

const defaultConnectionForm: ConnectDeviceInput = {
  baseUrl: "http://127.0.0.1:8000",
  deviceToken: "",
  deviceDisplayName: "Research Pulse Desktop",
};

function App() {
  return (
    <HashRouter>
      <DesktopShell />
    </HashRouter>
  );
}

function DesktopShell() {
  const navigate = useNavigate();
  const [syncStatus, setSyncStatus] = useState<SyncStatusRead | null>(null);
  const [todayOverview, setTodayOverview] = useState<TodayOverviewRead>(buildTodayEmptyState());
  const [desktopError, setDesktopError] = useState<string | null>(null);
  const [loadingBootstrap, setLoadingBootstrap] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [dataVersion, setDataVersion] = useState(0);
  const [connectionForm, setConnectionForm] =
    useState<ConnectDeviceInput>(defaultConnectionForm);

  const connected = Boolean(syncStatus?.connected);

  const reloadBootstrap = useCallback(async () => {
    setLoadingBootstrap(true);
    try {
      const bootstrap = await desktopApi.appBootstrap();
      setSyncStatus(bootstrap.syncStatus);
      setTodayOverview(bootstrap.todayOverview);
      setConnectionForm((current) => ({
        ...current,
        baseUrl: bootstrap.syncStatus.baseUrl ?? current.baseUrl,
        deviceDisplayName:
          bootstrap.syncStatus.deviceDisplayName ?? current.deviceDisplayName,
      }));
      setDesktopError(null);
    } catch (error) {
      setSyncStatus({
        connected: false,
        baseUrl: defaultConnectionForm.baseUrl,
        deviceId: null,
        deviceDisplayName: defaultConnectionForm.deviceDisplayName ?? null,
        lastSyncedAt: null,
        lastEventSequence: 0,
        lastError: null,
        currentUserSummary: null,
      });
      setTodayOverview(
        buildTodayEmptyState(
          "Desktop shell is not connected yet. Start it with `npm run tauri dev` and connect a device token.",
        ),
      );
      setDesktopError(error instanceof Error ? error.message : String(error));
    } finally {
      setLoadingBootstrap(false);
    }
  }, []);

  useEffect(() => {
    void reloadBootstrap();
  }, [reloadBootstrap]);

  async function handleConnect(input: ConnectDeviceInput) {
    setConnecting(true);
    try {
      const response = await desktopApi.connectDevice(input);
      setSyncStatus(response.syncStatus);
      setTodayOverview(response.todayOverview);
      setConnectionForm({
        ...input,
        deviceToken: "",
      });
      setDesktopError(null);
      setDataVersion((value) => value + 1);
      navigate("/today");
    } catch (error) {
      setDesktopError(error instanceof Error ? error.message : String(error));
    } finally {
      setConnecting(false);
    }
  }

  async function handleSyncNow() {
    setSyncing(true);
    try {
      const response = await desktopApi.syncNow();
      setSyncStatus(response.syncStatus);
      setTodayOverview(response.todayOverview);
      setDesktopError(null);
      setDataVersion((value) => value + 1);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setDesktopError(message);
      setSyncStatus((current) =>
        current
          ? {
              ...current,
              lastError: message,
            }
          : current,
      );
    } finally {
      setSyncing(false);
    }
  }

  async function handleDisconnect() {
    try {
      const status = await desktopApi.disconnectDevice();
      setSyncStatus(status);
      setTodayOverview(buildTodayEmptyState("Desktop device disconnected."));
      setDesktopError(null);
      setDataVersion((value) => value + 1);
      navigate("/connect");
    } catch (error) {
      setDesktopError(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleClearLocalCache() {
    try {
      const status = await desktopApi.clearLocalCache();
      setSyncStatus(status);
      setTodayOverview(buildTodayEmptyState("Local cache cleared. Run sync to repopulate it."));
      setDesktopError(null);
      setDataVersion((value) => value + 1);
    } catch (error) {
      setDesktopError(error instanceof Error ? error.message : String(error));
    }
  }

  const shellHeader = useMemo(() => {
    if (!syncStatus?.currentUserSummary) {
      return null;
    }
    return {
      user: syncStatus.currentUserSummary,
      lastSyncedAt: syncStatus.lastSyncedAt,
      lastEventSequence: syncStatus.lastEventSequence,
    };
  }, [syncStatus]);

  if (loadingBootstrap) {
    return <LoadingState label="Bootstrapping desktop shell" />;
  }

  return (
    <div className="desktop-root">
      {desktopError ? (
        <div className="banner banner-error">
          <strong>Desktop Error</strong>
          <span>{desktopError}</span>
        </div>
      ) : null}
      {syncStatus?.lastError ? (
        <div className="banner banner-warning">
          <strong>Last Sync Error</strong>
          <span>{syncStatus.lastError}</span>
        </div>
      ) : null}

      <Routes>
        <Route
          path="/connect"
          element={
            <ConnectionScreen
              connected={connected}
              form={connectionForm}
              onFormChange={setConnectionForm}
              onConnect={handleConnect}
              connecting={connecting}
              syncStatus={syncStatus}
            />
          }
        />
        <Route
          path="/*"
          element={
            connected && syncStatus ? (
              <ShellLayout
                syncStatus={syncStatus}
                shellHeader={shellHeader}
                syncing={syncing}
                onSyncNow={handleSyncNow}
                onDisconnect={handleDisconnect}
                onClearLocalCache={handleClearLocalCache}
                todayOverview={todayOverview}
                dataVersion={dataVersion}
              />
            ) : (
              <Navigate to="/connect" replace />
            )
          }
        />
      </Routes>
    </div>
  );
}

function ShellLayout({
  syncStatus,
  shellHeader,
  syncing,
  onSyncNow,
  onDisconnect,
  onClearLocalCache,
  todayOverview,
  dataVersion,
}: {
  syncStatus: SyncStatusRead;
  shellHeader: {
    user: NonNullable<SyncStatusRead["currentUserSummary"]>;
    lastSyncedAt: string | null;
    lastEventSequence: number;
  } | null;
  syncing: boolean;
  onSyncNow: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onClearLocalCache: () => Promise<void>;
  todayOverview: TodayOverviewRead;
  dataVersion: number;
}) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">RP</div>
          <div>
            <div className="brand-title">Research Pulse</div>
            <div className="brand-subtitle">Tauri desktop shell</div>
          </div>
        </div>

        {shellHeader ? (
          <section className="sidebar-card">
            <div className="sidebar-label">Linked User</div>
            <div className="sidebar-user">{shellHeader.user.name}</div>
            <div className="sidebar-meta">{shellHeader.user.email ?? "No email"}</div>
            <div className="sidebar-meta">{shellHeader.user.field ?? "No field"}</div>
          </section>
        ) : null}

        <nav className="sidebar-nav">
          <NavLink to="/today">Today</NavLink>
          <NavLink to="/papers">Papers</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>

        <section className="sidebar-card">
          <div className="sidebar-label">Connection</div>
          <div className="sidebar-meta">{syncStatus.baseUrl}</div>
          <div className="sidebar-meta">
            Event cursor #{syncStatus.lastEventSequence}
          </div>
          <div className="sidebar-meta">
            {syncStatus.lastSyncedAt
              ? `Last sync ${formatDateTime(syncStatus.lastSyncedAt)}`
              : "Never synced"}
          </div>
          <div className="sidebar-actions">
            <button type="button" onClick={() => void onSyncNow()} disabled={syncing}>
              {syncing ? "Syncing..." : "Sync Now"}
            </button>
            <button type="button" className="button-secondary" onClick={() => void onClearLocalCache()}>
              Clear Cache
            </button>
            <button type="button" className="button-secondary" onClick={() => void onDisconnect()}>
              Disconnect
            </button>
          </div>
        </section>
      </aside>

      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route path="/today" element={<TodayView todayOverview={todayOverview} />} />
          <Route path="/papers" element={<PapersView dataVersion={dataVersion} />} />
          <Route
            path="/papers/:paperId"
            element={<PaperDetailView dataVersion={dataVersion} />}
          />
          <Route
            path="/settings"
            element={
              <SettingsView
                syncStatus={syncStatus}
                syncing={syncing}
                onSyncNow={onSyncNow}
                onDisconnect={onDisconnect}
                onClearLocalCache={onClearLocalCache}
              />
            }
          />
        </Routes>
      </main>
    </div>
  );
}

function ConnectionScreen({
  connected,
  form,
  onFormChange,
  onConnect,
  connecting,
  syncStatus,
}: {
  connected: boolean;
  form: ConnectDeviceInput;
  onFormChange: (form: ConnectDeviceInput) => void;
  onConnect: (input: ConnectDeviceInput) => Promise<void>;
  connecting: boolean;
  syncStatus: SyncStatusRead | null;
}) {
  if (connected) {
    return <Navigate to="/today" replace />;
  }

  return (
    <div className="connection-screen">
      <section className="connection-card">
        <div className="eyebrow">Desktop Connection</div>
        <h1>Connect a read-only desktop device</h1>
        <p className="lede">
          This shell uses the existing device-token sync boundary. Admin auth stays
          separate, and the token never touches localStorage or sessionStorage.
        </p>

        <label>
          Backend base URL
          <input
            value={form.baseUrl}
            onChange={(event) =>
              onFormChange({
                ...form,
                baseUrl: event.target.value,
              })
            }
            placeholder="http://127.0.0.1:8000"
          />
        </label>

        <label>
          Device token
          <textarea
            rows={4}
            value={form.deviceToken}
            onChange={(event) =>
              onFormChange({
                ...form,
                deviceToken: event.target.value,
              })
            }
            placeholder="Paste the admin-issued desktop device token"
          />
        </label>

        <label>
          Local display label
          <input
            value={form.deviceDisplayName ?? ""}
            onChange={(event) =>
              onFormChange({
                ...form,
                deviceDisplayName: event.target.value,
              })
            }
            placeholder="Research Pulse Desktop"
          />
        </label>

        <div className="form-actions">
          <button
            type="button"
            onClick={() => void onConnect(form)}
            disabled={connecting || !form.baseUrl.trim() || !form.deviceToken.trim()}
          >
            {connecting ? "Connecting..." : "Connect Device"}
          </button>
        </div>

        {syncStatus?.baseUrl ? (
          <div className="meta-note">Last configured backend: {syncStatus.baseUrl}</div>
        ) : null}
      </section>
    </div>
  );
}

function TodayView({ todayOverview }: { todayOverview: TodayOverviewRead }) {
  if (todayOverview.state !== "ready") {
    return (
      <section className="panel">
        <div className="eyebrow">Today</div>
        <h1>No digest available yet</h1>
        <p className="panel-message">
          {todayOverview.message ??
            "No digest issue has been cached yet. Run a sync after the backend builds one."}
        </p>
      </section>
    );
  }

  return (
    <section className="page-grid">
      <div className="panel">
        <div className="eyebrow">Today</div>
        <h1>{todayOverview.title}</h1>
        <p className="panel-message">{todayOverview.summary}</p>
        <div className="stat-grid">
          <StatCard label="Issue Date" value={todayOverview.issueDate ?? "-"} />
          <StatCard label="Highlights" value={String(todayOverview.highlightCount)} />
          <StatCard
            label="Selected Cards"
            value={String(todayOverview.selectedCardCount)}
          />
          <StatCard
            label="Landing"
            value={todayOverview.deepLinkPath ?? "Mini path pending"}
          />
        </div>
      </div>
      <div className="panel">
        <div className="eyebrow">Highlights</div>
        <div className="list-stack">
          {todayOverview.highlights.map((highlight) => (
            <article className="list-card" key={highlight.pulseCardId}>
              <div className="list-card-topline">
                <span>#{highlight.sortOrder}</span>
                <span>{highlight.cardType}</span>
              </div>
              <h3>{highlight.title}</h3>
              <p>{highlight.summary}</p>
              {highlight.paper ? (
                <div className="pill-row">
                  <span className="pill">{highlight.paper.title}</span>
                  <span className="pill">
                    {highlight.paper.progressPercentage}% progress
                  </span>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function PapersView({ dataVersion }: { dataVersion: number }) {
  const [papers, setPapers] = useState<PaperListItemRead[]>([]);
  const [paperType, setPaperType] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const filters: ListPapersInput = paperType ? { paperType } : {};
        const response = await desktopApi.listPapers(filters);
        setPapers(sortPapers(response));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : String(loadError));
      } finally {
        setLoading(false);
      }
    })();
  }, [dataVersion, paperType]);

  return (
    <section className="panel">
      <div className="page-header">
        <div>
          <div className="eyebrow">Papers</div>
          <h1>Cached paper library</h1>
        </div>
        <label className="inline-filter">
          Status
          <select value={paperType} onChange={(event) => setPaperType(event.target.value)}>
            <option value="">All</option>
            <option value="published">published</option>
            <option value="revision">revision</option>
            <option value="under_review">under_review</option>
            <option value="in_prep">in_prep</option>
            <option value="paused">paused</option>
          </select>
        </label>
      </div>

      {loading ? <LoadingState label="Loading cached papers" /> : null}
      {error ? <p className="panel-message">{error}</p> : null}
      {!loading && !papers.length ? (
        <p className="panel-message">
          No papers are cached yet. Run sync after the backend emits paper events.
        </p>
      ) : null}

      <div className="list-stack">
        {papers.map((paper) => (
          <NavLink className="list-card list-card-link" key={paper.id} to={`/papers/${paper.id}`}>
            <div className="list-card-topline">
              <span>{paper.paperType}</span>
              <span>{paper.progressPercentage}%</span>
            </div>
            <h3>{paper.title}</h3>
            <p>{paper.nextAction ?? paper.blocker ?? "No next action recorded."}</p>
            <div className="pill-row">
              <span className="pill">Priority {paper.priority}</span>
              {paper.venue ? <span className="pill">{paper.venue}</span> : null}
              <span className="pill">{paper.stage}</span>
            </div>
          </NavLink>
        ))}
      </div>
    </section>
  );
}

function PaperDetailView({ dataVersion }: { dataVersion: number }) {
  const { paperId } = useParams();
  const [paper, setPaper] = useState<PaperDetailRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!paperId) {
      return;
    }
    void (async () => {
      setLoading(true);
      try {
        const detail = await desktopApi.getPaperDetail(paperId);
        setPaper(detail);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : String(loadError));
      } finally {
        setLoading(false);
      }
    })();
  }, [paperId, dataVersion]);

  if (!paperId) {
    return <Navigate to="/papers" replace />;
  }

  if (loading) {
    return <LoadingState label="Loading paper detail" />;
  }

  if (error || !paper) {
    return (
      <section className="panel">
        <div className="eyebrow">Paper Detail</div>
        <h1>Paper not available</h1>
        <p className="panel-message">{error ?? "The paper is not cached yet."}</p>
      </section>
    );
  }

  return (
    <section className="page-grid">
      <div className="panel">
        <div className="eyebrow">Paper Detail</div>
        <h1>{paper.title}</h1>
        <div className="pill-row">
          <span className="pill">{paper.paperType}</span>
          <span className="pill">{paper.stage}</span>
          <span className="pill">{paper.progressPercentage}% progress</span>
        </div>
        <p className="panel-message">
          {paper.nextAction ?? "No next action recorded."}
          {paper.blocker ? ` Blocker: ${paper.blocker}` : ""}
        </p>
        <div className="detail-grid">
          <DetailRow label="Venue" value={paper.venue ?? "Not set"} />
          <DetailRow label="Priority" value={String(paper.priority)} />
          <DetailRow
            label="Last touch"
            value={paper.lastTouchAt ? formatDateTime(paper.lastTouchAt) : "Unknown"}
          />
          <DetailRow label="Identifiers" value={JSON.stringify(paper.identifiers)} />
        </div>
      </div>

      <div className="panel">
        <div className="eyebrow">Recent Progress Events</div>
        <div className="list-stack">
          {paper.progressEvents.length ? (
            paper.progressEvents.map((event) => (
              <article className="list-card" key={event.id}>
                <div className="list-card-topline">
                  <span>{event.stage}</span>
                  <span>{formatDateTime(event.happenedAt)}</span>
                </div>
                <p>{event.summary}</p>
              </article>
            ))
          ) : (
            <p className="panel-message">No progress events cached yet.</p>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="eyebrow">Latest Signal Snapshots</div>
        <div className="list-stack">
          {paper.signalSnapshots.length ? (
            paper.signalSnapshots.map((snapshot) => (
              <article className="list-card" key={snapshot.id}>
                <div className="list-card-topline">
                  <span>{snapshot.source}</span>
                  <span>{formatDateTime(snapshot.fetchedAt)}</span>
                </div>
                <p>
                  Citations {snapshot.citationCount ?? "-"} / Downloads{" "}
                  {snapshot.downloadCount ?? "-"} / Reads {snapshot.readCount ?? "-"}
                </p>
              </article>
            ))
          ) : (
            <p className="panel-message">No signal snapshots cached yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function SettingsView({
  syncStatus,
  syncing,
  onSyncNow,
  onDisconnect,
  onClearLocalCache,
}: {
  syncStatus: SyncStatusRead;
  syncing: boolean;
  onSyncNow: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onClearLocalCache: () => Promise<void>;
}) {
  return (
    <section className="panel">
      <div className="eyebrow">Settings / Sync Status</div>
      <h1>Desktop connection state</h1>
      <div className="detail-grid">
        <DetailRow label="Backend URL" value={syncStatus.baseUrl ?? "Not configured"} />
        <DetailRow
          label="Linked user"
          value={syncStatus.currentUserSummary?.name ?? "Not connected"}
        />
        <DetailRow
          label="Last sync"
          value={
            syncStatus.lastSyncedAt
              ? formatDateTime(syncStatus.lastSyncedAt)
              : "Never synced"
          }
        />
        <DetailRow
          label="Event cursor"
          value={String(syncStatus.lastEventSequence)}
        />
      </div>
      <div className="sidebar-actions">
        <button type="button" onClick={() => void onSyncNow()} disabled={syncing}>
          {syncing ? "Syncing..." : "Manual Sync"}
        </button>
        <button type="button" className="button-secondary" onClick={() => void onClearLocalCache()}>
          Clear Local Cache
        </button>
        <button type="button" className="button-secondary" onClick={() => void onDisconnect()}>
          Disconnect Device
        </button>
      </div>
    </section>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="loading-state">
      <div className="loading-dot" />
      <span>{label}</span>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="stat-card">
      <div className="sidebar-label">{label}</div>
      <div className="stat-value">{value}</div>
    </article>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatDateTime(value: string) {
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export default App;
