import { useCallback, useEffect, useMemo, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
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
import {
  buildQuietHoursPatch,
  buildTodayEmptyState,
  extractQuietHoursDraft,
  sortPapers,
} from "./lib/readModels";
import type {
  AddReviewCommentInput,
  ChooseWorkspaceRootInput,
  ConnectDeviceInput,
  CreateReviewRoundInput,
  CreateBlankPaperNoteInput,
  CreatePaperNoteFromTemplateInput,
  DeleteReviewCommentInput,
  ImportPaperAttachmentsResponse,
  ListPapersInput,
  NoteTemplateRead,
  PaperDetailRead,
  PaperListItemRead,
  PaperNoteDetailRead,
  PendingMutationRead,
  QueuePaperPatchInput,
  QueueProgressEventCreateInput,
  QueueSubscriptionPolicyPatchInput,
  ReviewRoundDetailRead,
  SavePaperNoteInput,
  SubscriptionPolicyRead,
  SyncNowResponse,
  SyncStatusRead,
  TodayOverviewRead,
  UpdateReviewCommentInput,
  UpdateReviewRoundInput,
  WorkspaceStatusRead,
  WriteActionResultRead,
} from "./lib/types";

const defaultConnectionForm: ConnectDeviceInput = {
  baseUrl: "http://127.0.0.1:8000",
  deviceToken: "",
  deviceDisplayName: "Research Pulse Desktop",
};

type PaperPatchDraft = {
  stage: string;
  venue: string;
  nextAction: string;
  blocker: string;
  priority: string;
};

type ProgressEventDraft = {
  stage: string;
  happenedAt: string;
  summary: string;
  owner: string;
};

type SubscriptionPolicyDraft = {
  enabled: boolean;
  frequencyCap: string;
  quietStart: string;
  quietEnd: string;
};

type AttachmentImportDraft = {
  attachmentKind: string;
};

type BlankNoteDraft = {
  title: string;
};

type ReviewRoundDraft = {
  roundLabel: string;
  venue: string;
  decisionLabel: string;
  status: string;
};

type ReviewCommentDraft = {
  reviewerLabel: string;
  commentCode: string;
  commentText: string;
  category: string;
  disposition: string;
  responseSummary: string;
  actionNote: string;
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
  const [lastSyncSummary, setLastSyncSummary] = useState<SyncNowResponse | null>(null);
  const [connectionForm, setConnectionForm] =
    useState<ConnectDeviceInput>(defaultConnectionForm);

  const connected = Boolean(syncStatus?.connected);

  const refreshShellData = useCallback(async () => {
    const [nextStatus, nextToday] = await Promise.all([
      desktopApi.getSyncStatus(),
      desktopApi.getTodayOverview(),
    ]);
    setSyncStatus(nextStatus);
    setTodayOverview(nextToday);
  }, []);

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
        pendingMutationCount: 0,
        failedMutationCount: 0,
        recentOutboxErrors: [],
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
      setLastSyncSummary(null);
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
      setLastSyncSummary(response);
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
      setLastSyncSummary(null);
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
      setLastSyncSummary(null);
      setDataVersion((value) => value + 1);
    } catch (error) {
      setDesktopError(error instanceof Error ? error.message : String(error));
    }
  }

  const handleWriteResult = useCallback(
    async (result: WriteActionResultRead) => {
      setSyncStatus(result.syncStatus);
      if (result.syncError) {
        setDesktopError(result.syncError);
      } else {
        setDesktopError(null);
      }
      await refreshShellData();
      setDataVersion((value) => value + 1);
      return result;
    },
    [refreshShellData],
  );

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
                lastSyncSummary={lastSyncSummary}
                onSyncNow={handleSyncNow}
                onDisconnect={handleDisconnect}
                onClearLocalCache={handleClearLocalCache}
                onWriteResult={handleWriteResult}
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
  lastSyncSummary,
  onSyncNow,
  onDisconnect,
  onClearLocalCache,
  onWriteResult,
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
  lastSyncSummary: SyncNowResponse | null;
  onSyncNow: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onClearLocalCache: () => Promise<void>;
  onWriteResult: (result: WriteActionResultRead) => Promise<WriteActionResultRead>;
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
            <div className="brand-subtitle">Tauri desktop workbench</div>
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
          <div className="sidebar-meta">
            Pending {syncStatus.pendingMutationCount} / Failed{" "}
            {syncStatus.failedMutationCount}
          </div>
          <div className="sidebar-actions">
            <button type="button" onClick={() => void onSyncNow()} disabled={syncing}>
              {syncing ? "Syncing..." : "Sync Now"}
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => void onClearLocalCache()}
            >
              Clear Cache
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => void onDisconnect()}
            >
              Disconnect
            </button>
          </div>
        </section>

        {lastSyncSummary ? (
          <section className="sidebar-card">
            <div className="sidebar-label">Last Sync</div>
            <div className="sidebar-meta">
              Push {lastSyncSummary.pushedCount} / Apply {lastSyncSummary.appliedCount} /
              Dup {lastSyncSummary.duplicateCount} / Fail {lastSyncSummary.failedCount}
            </div>
            <div className="sidebar-meta">
              Feed {lastSyncSummary.eventsApplied} events, ack #{lastSyncSummary.acknowledgedSequence}
            </div>
          </section>
        ) : null}
      </aside>

      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route path="/today" element={<TodayView todayOverview={todayOverview} />} />
          <Route path="/papers" element={<PapersView dataVersion={dataVersion} />} />
          <Route
            path="/papers/:paperId"
            element={
              <PaperDetailView dataVersion={dataVersion} onWriteResult={onWriteResult} />
            }
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
                onWriteResult={onWriteResult}
                dataVersion={dataVersion}
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
        <h1>Connect a write-capable desktop device</h1>
        <p className="lede">
          This shell uses the existing device-token sync boundary. Desktop writes go
          through the local outbox and `/sync/push`, not business CRUD endpoints.
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
                  {highlight.paper.pendingMutationCount ? (
                    <span className="pill pill-accent">
                      {highlight.paper.pendingMutationCount} pending write
                    </span>
                  ) : null}
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
              {paper.pendingMutationCount ? (
                <span className="pill pill-accent">
                  {paper.pendingMutationCount} pending write
                </span>
              ) : null}
              <span className={`pill ${paper.workspaceReady ? "pill-success" : ""}`}>
                Workspace {paper.workspaceReady ? "ready" : "pending"}
              </span>
              {paper.attachmentCount ? (
                <span className="pill">{paper.attachmentCount} attachments</span>
              ) : null}
              {paper.lastMutationError ? (
                <span className="pill pill-danger">Sync failed</span>
              ) : null}
            </div>
          </NavLink>
        ))}
      </div>
    </section>
  );
}

function PaperDetailView({
  dataVersion,
  onWriteResult,
}: {
  dataVersion: number;
  onWriteResult: (result: WriteActionResultRead) => Promise<WriteActionResultRead>;
}) {
  const { paperId } = useParams();
  const [paper, setPaper] = useState<PaperDetailRead | null>(null);
  const [patchDraft, setPatchDraft] = useState<PaperPatchDraft | null>(null);
  const [progressDraft, setProgressDraft] = useState<ProgressEventDraft>({
    stage: "revision",
    happenedAt: toDateTimeLocalValue(new Date().toISOString()),
    summary: "",
    owner: "desktop",
  });
  const [attachmentDraft, setAttachmentDraft] = useState<AttachmentImportDraft>({
    attachmentKind: "manuscript",
  });
  const [blankNoteDraft, setBlankNoteDraft] = useState<BlankNoteDraft>({
    title: "",
  });
  const [noteTemplates, setNoteTemplates] = useState<NoteTemplateRead[]>([]);
  const [selectedTemplateKind, setSelectedTemplateKind] = useState<string>("research_note");
  const [selectedNote, setSelectedNote] = useState<PaperNoteDetailRead | null>(null);
  const [noteContentDraft, setNoteContentDraft] = useState<string>("");
  const [reviewRoundDraft, setReviewRoundDraft] = useState<ReviewRoundDraft>({
    roundLabel: "Round 1",
    venue: "",
    decisionLabel: "",
    status: "open",
  });
  const [selectedReviewRoundId, setSelectedReviewRoundId] = useState<string | null>(null);
  const [selectedReviewRoundDetail, setSelectedReviewRoundDetail] =
    useState<ReviewRoundDetailRead | null>(null);
  const [selectedReviewCommentId, setSelectedReviewCommentId] = useState<string | null>(null);
  const [reviewCommentDraft, setReviewCommentDraft] = useState<ReviewCommentDraft>({
    reviewerLabel: "Reviewer 1",
    commentCode: "",
    commentText: "",
    category: "",
    disposition: "todo",
    responseSummary: "",
    actionNote: "",
  });
  const [savingPatch, setSavingPatch] = useState(false);
  const [savingProgress, setSavingProgress] = useState(false);
  const [workspaceBusy, setWorkspaceBusy] = useState(false);
  const [notesBusy, setNotesBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [workspaceMessage, setWorkspaceMessage] = useState<string | null>(null);
  const [notesMessage, setNotesMessage] = useState<string | null>(null);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

  const loadPaperDetail = useCallback(async () => {
    if (!paperId) {
      return;
    }
    setLoading(true);
    try {
      const [detail, templates] = await Promise.all([
        desktopApi.getPaperDetail(paperId),
        desktopApi.listNoteTemplates(),
      ]);
      setPaper(detail);
      setNoteTemplates(templates);
      setSelectedTemplateKind((current) => current || templates[0]?.kind || "research_note");
      setPatchDraft({
        stage: detail.stage,
        venue: detail.venue ?? "",
        nextAction: detail.nextAction ?? "",
        blocker: detail.blocker ?? "",
        priority: String(detail.priority),
      });
      setProgressDraft((current) => ({
        ...current,
        stage: detail.stage,
      }));
      setSelectedReviewRoundId((current) => {
        if (current && detail.reviewRounds.some((round) => round.id === current)) {
          return current;
        }
        return detail.reviewRounds[0]?.id ?? null;
      });
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
    } finally {
      setLoading(false);
    }
  }, [paperId]);

  useEffect(() => {
    void loadPaperDetail();
  }, [dataVersion, loadPaperDetail]);

  useEffect(() => {
    if (!paper || !selectedNote) {
      return;
    }
    const matchingSummary = paper.notes.find((note) => note.id === selectedNote.note.id);
    if (!matchingSummary) {
      setSelectedNote(null);
      setNoteContentDraft("");
      return;
    }
    if (
      matchingSummary.updatedAt !== selectedNote.note.updatedAt ||
      matchingSummary.status !== selectedNote.note.status ||
      matchingSummary.absolutePath !== selectedNote.note.absolutePath
    ) {
      setSelectedNote((current) =>
        current
          ? {
              ...current,
              note: matchingSummary,
            }
          : current,
      );
    }
  }, [
    paper,
    selectedNote,
    selectedNote?.note.id,
    selectedNote?.note.updatedAt,
    selectedNote?.note.status,
    selectedNote?.note.absolutePath,
  ]);

  useEffect(() => {
    if (!selectedReviewRoundId) {
      setSelectedReviewRoundDetail(null);
      setSelectedReviewCommentId(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const detail = await desktopApi.getReviewRoundDetail(selectedReviewRoundId);
        if (cancelled) {
          return;
        }
        setSelectedReviewRoundDetail(detail);
        setReviewRoundDraft({
          roundLabel: detail.round.roundLabel,
          venue: detail.round.venue ?? "",
          decisionLabel: detail.round.decisionLabel ?? "",
          status: detail.round.status,
        });
        setSelectedReviewCommentId((current) =>
          current && detail.comments.some((comment) => comment.id === current)
            ? current
            : null,
        );
      } catch (reviewError) {
        if (!cancelled) {
          setReviewMessage(
            reviewError instanceof Error ? reviewError.message : String(reviewError),
          );
          setSelectedReviewRoundDetail(null);
          setSelectedReviewCommentId(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedReviewRoundId, dataVersion]);

  useEffect(() => {
    if (!selectedReviewRoundDetail || !selectedReviewCommentId) {
      return;
    }
    const comment = selectedReviewRoundDetail.comments.find(
      (item) => item.id === selectedReviewCommentId,
    );
    if (!comment) {
      setSelectedReviewCommentId(null);
      return;
    }
    setReviewCommentDraft({
      reviewerLabel: comment.reviewerLabel,
      commentCode: comment.commentCode ?? "",
      commentText: comment.commentText,
      category: comment.category ?? "",
      disposition: comment.disposition,
      responseSummary: comment.responseSummary ?? "",
      actionNote: comment.actionNote ?? "",
    });
  }, [selectedReviewRoundDetail, selectedReviewCommentId]);

  if (!paperId) {
    return <Navigate to="/papers" replace />;
  }

  if (loading) {
    return <LoadingState label="Loading paper detail" />;
  }

  if (error || !paper || !patchDraft) {
    return (
      <section className="panel">
        <div className="eyebrow">Paper Detail</div>
        <h1>Paper not available</h1>
        <p className="panel-message">{error ?? "The paper is not cached yet."}</p>
      </section>
    );
  }

  const currentPaper = paper;
  const currentPatchDraft = patchDraft;

  async function handleSavePatch() {
    setSavingPatch(true);
    try {
      const result = await desktopApi.queuePaperPatch({
        paperId: currentPaper.id,
        stage: currentPatchDraft.stage,
        venue: currentPatchDraft.venue,
        nextAction: currentPatchDraft.nextAction,
        blocker: currentPatchDraft.blocker,
        priority: Number(currentPatchDraft.priority),
      } satisfies QueuePaperPatchInput);
      await onWriteResult(result);
      await loadPaperDetail();
      setActionMessage(buildWriteMessage(result, "Paper update queued"));
    } catch (saveError) {
      setActionMessage(
        saveError instanceof Error ? saveError.message : String(saveError),
      );
    } finally {
      setSavingPatch(false);
    }
  }

  async function handleCreateProgressEvent() {
    setSavingProgress(true);
    try {
      const result = await desktopApi.queueProgressEventCreate({
        paperId: currentPaper.id,
        stage: progressDraft.stage,
        happenedAt: toIsoTimestamp(progressDraft.happenedAt),
        summary: progressDraft.summary,
        owner: progressDraft.owner,
      } satisfies QueueProgressEventCreateInput);
      await onWriteResult(result);
      await loadPaperDetail();
      setProgressDraft((current) => ({
        ...current,
        summary: "",
      }));
      setActionMessage(buildWriteMessage(result, "Progress event queued"));
    } catch (saveError) {
      setActionMessage(
        saveError instanceof Error ? saveError.message : String(saveError),
      );
    } finally {
      setSavingProgress(false);
    }
  }

  async function handleEnsureWorkspace() {
    setWorkspaceBusy(true);
    try {
      const workspace = await desktopApi.ensurePaperWorkspace(currentPaper.id);
      await loadPaperDetail();
      setWorkspaceMessage(
        workspace.workspaceReady
          ? "Local workspace ensured."
          : "Workspace metadata was created, but the root still needs attention.",
      );
    } catch (workspaceError) {
      setWorkspaceMessage(
        workspaceError instanceof Error ? workspaceError.message : String(workspaceError),
      );
    } finally {
      setWorkspaceBusy(false);
    }
  }

  async function handleRefreshWorkspace() {
    setWorkspaceBusy(true);
    try {
      await desktopApi.refreshPaperWorkspace(currentPaper.id);
      await loadPaperDetail();
      setWorkspaceMessage("Workspace metadata refreshed.");
    } catch (workspaceError) {
      setWorkspaceMessage(
        workspaceError instanceof Error ? workspaceError.message : String(workspaceError),
      );
    } finally {
      setWorkspaceBusy(false);
    }
  }

  async function handleImportAttachments() {
    const selection = await open({
      title: "Import local paper attachments",
      multiple: true,
      directory: false,
    });
    const sourcePaths = Array.isArray(selection)
      ? selection
      : selection
        ? [selection]
        : [];
    if (!sourcePaths.length) {
      return;
    }

    setWorkspaceBusy(true);
    try {
      const response = await desktopApi.importPaperAttachments({
        paperId: currentPaper.id,
        attachmentKind: attachmentDraft.attachmentKind,
        sourcePaths,
      });
      await loadPaperDetail();
      setWorkspaceMessage(buildAttachmentImportMessage(response));
    } catch (workspaceError) {
      setWorkspaceMessage(
        workspaceError instanceof Error ? workspaceError.message : String(workspaceError),
      );
    } finally {
      setWorkspaceBusy(false);
    }
  }

  async function handleOpenNote(noteId: string) {
    setNotesBusy(true);
    try {
      const note = await desktopApi.getPaperNote(noteId);
      setSelectedNote(note);
      setNoteContentDraft(note.content ?? "");
      setNotesMessage(
        note.note.status === "missing"
          ? "Note file is missing on disk. Save to recreate it once the workspace root is available."
          : `Opened ${note.note.title}.`,
      );
    } catch (noteError) {
      setNotesMessage(noteError instanceof Error ? noteError.message : String(noteError));
    } finally {
      setNotesBusy(false);
    }
  }

  async function handleCreateNoteFromTemplate() {
    setNotesBusy(true);
    try {
      const result = await desktopApi.createPaperNoteFromTemplate({
        paperId: currentPaper.id,
        templateKind: selectedTemplateKind,
      } satisfies CreatePaperNoteFromTemplateInput);
      await loadPaperDetail();
      setSelectedNote(result.note);
      setNoteContentDraft(result.note.content ?? "");
      setNotesMessage(result.message);
    } catch (noteError) {
      setNotesMessage(noteError instanceof Error ? noteError.message : String(noteError));
    } finally {
      setNotesBusy(false);
    }
  }

  async function handleCreateBlankNote() {
    setNotesBusy(true);
    try {
      const result = await desktopApi.createBlankPaperNote({
        paperId: currentPaper.id,
        title: blankNoteDraft.title.trim() || undefined,
      } satisfies CreateBlankPaperNoteInput);
      await loadPaperDetail();
      setSelectedNote(result.note);
      setNoteContentDraft(result.note.content ?? "");
      setBlankNoteDraft({ title: "" });
      setNotesMessage(result.message);
    } catch (noteError) {
      setNotesMessage(noteError instanceof Error ? noteError.message : String(noteError));
    } finally {
      setNotesBusy(false);
    }
  }

  async function handleSaveNote() {
    if (!selectedNote) {
      return;
    }
    setNotesBusy(true);
    try {
      const result = await desktopApi.savePaperNote({
        noteId: selectedNote.note.id,
        content: noteContentDraft,
      } satisfies SavePaperNoteInput);
      await loadPaperDetail();
      setSelectedNote(result.note);
      setNoteContentDraft(result.note.content ?? "");
      setNotesMessage(result.message);
    } catch (noteError) {
      setNotesMessage(noteError instanceof Error ? noteError.message : String(noteError));
    } finally {
      setNotesBusy(false);
    }
  }

  async function handleRefreshNotes() {
    setNotesBusy(true);
    try {
      const refreshed = await desktopApi.refreshPaperNotes(currentPaper.id);
      await loadPaperDetail();
      if (selectedNote) {
        const stillExists = refreshed.find((note) => note.id === selectedNote.note.id);
        if (stillExists) {
          const detail = await desktopApi.getPaperNote(stillExists.id);
          setSelectedNote(detail);
          setNoteContentDraft(detail.content ?? "");
        } else {
          setSelectedNote(null);
          setNoteContentDraft("");
        }
      }
      setNotesMessage("Local note metadata refreshed.");
    } catch (noteError) {
      setNotesMessage(noteError instanceof Error ? noteError.message : String(noteError));
    } finally {
      setNotesBusy(false);
    }
  }

  function resetReviewCommentDraft(defaultReviewerLabel?: string) {
    setSelectedReviewCommentId(null);
    setReviewCommentDraft({
      reviewerLabel: defaultReviewerLabel ?? "Reviewer 1",
      commentCode: "",
      commentText: "",
      category: "",
      disposition: "todo",
      responseSummary: "",
      actionNote: "",
    });
  }

  async function handleCreateReviewRound() {
    setReviewBusy(true);
    try {
      const result = await desktopApi.createReviewRound({
        paperId: currentPaper.id,
        roundLabel: reviewRoundDraft.roundLabel,
        venue: reviewRoundDraft.venue,
        decisionLabel: reviewRoundDraft.decisionLabel,
      } satisfies CreateReviewRoundInput);
      await loadPaperDetail();
      if (result.round) {
        setSelectedReviewRoundId(result.round.id);
      }
      resetReviewCommentDraft();
      setReviewMessage(result.message);
    } catch (reviewError) {
      setReviewMessage(reviewError instanceof Error ? reviewError.message : String(reviewError));
    } finally {
      setReviewBusy(false);
    }
  }

  async function handleUpdateReviewRound() {
    if (!selectedReviewRoundDetail) {
      return;
    }
    setReviewBusy(true);
    try {
      const result = await desktopApi.updateReviewRound({
        reviewRoundId: selectedReviewRoundDetail.round.id,
        roundLabel: reviewRoundDraft.roundLabel,
        venue: reviewRoundDraft.venue,
        decisionLabel: reviewRoundDraft.decisionLabel,
        status: reviewRoundDraft.status,
      } satisfies UpdateReviewRoundInput);
      await loadPaperDetail();
      if (result.round) {
        setSelectedReviewRoundId(result.round.id);
      }
      setReviewMessage(result.message);
    } catch (reviewError) {
      setReviewMessage(reviewError instanceof Error ? reviewError.message : String(reviewError));
    } finally {
      setReviewBusy(false);
    }
  }

  async function handleSaveReviewComment() {
    if (!selectedReviewRoundId) {
      return;
    }
    setReviewBusy(true);
    try {
      const payload = {
        reviewerLabel: reviewCommentDraft.reviewerLabel,
        commentCode: reviewCommentDraft.commentCode || undefined,
        commentText: reviewCommentDraft.commentText,
        category: reviewCommentDraft.category || undefined,
        disposition: reviewCommentDraft.disposition,
        responseSummary: reviewCommentDraft.responseSummary || undefined,
        actionNote: reviewCommentDraft.actionNote || undefined,
      };
      const result = selectedReviewCommentId
        ? await desktopApi.updateReviewComment({
            commentId: selectedReviewCommentId,
            ...payload,
          } satisfies UpdateReviewCommentInput)
        : await desktopApi.addReviewComment({
            reviewRoundId: selectedReviewRoundId,
            ...payload,
          } satisfies AddReviewCommentInput);
      await loadPaperDetail();
      setSelectedReviewRoundDetail(result.detail ?? null);
      setSelectedReviewRoundId(result.detail?.round.id ?? selectedReviewRoundId);
      setSelectedReviewCommentId(result.comment?.id ?? null);
      if (result.comment) {
        setReviewCommentDraft({
          reviewerLabel: result.comment.reviewerLabel,
          commentCode: result.comment.commentCode ?? "",
          commentText: result.comment.commentText,
          category: result.comment.category ?? "",
          disposition: result.comment.disposition,
          responseSummary: result.comment.responseSummary ?? "",
          actionNote: result.comment.actionNote ?? "",
        });
      }
      setReviewMessage(result.message);
    } catch (reviewError) {
      setReviewMessage(reviewError instanceof Error ? reviewError.message : String(reviewError));
    } finally {
      setReviewBusy(false);
    }
  }

  async function handleDeleteReviewComment() {
    if (!selectedReviewCommentId) {
      return;
    }
    setReviewBusy(true);
    try {
      const result = await desktopApi.deleteReviewComment(
        selectedReviewCommentId satisfies DeleteReviewCommentInput["commentId"],
      );
      await loadPaperDetail();
      setSelectedReviewRoundDetail(result.detail ?? null);
      resetReviewCommentDraft();
      setReviewMessage(result.message);
    } catch (reviewError) {
      setReviewMessage(reviewError instanceof Error ? reviewError.message : String(reviewError));
    } finally {
      setReviewBusy(false);
    }
  }

  async function handleGenerateReviewNote(kind: "reviewer_matrix" | "response_letter") {
    if (!selectedReviewRoundId) {
      return;
    }
    setReviewBusy(true);
    try {
      const result =
        kind === "reviewer_matrix"
          ? await desktopApi.generateReviewerMatrixNote(selectedReviewRoundId)
          : await desktopApi.generateResponseLetterNote(selectedReviewRoundId);
      await loadPaperDetail();
      setSelectedReviewRoundDetail(result.detail ?? null);
      setReviewMessage(result.message);
      if (result.generatedNote) {
        await handleOpenNote(result.generatedNote.noteId);
      }
    } catch (reviewError) {
      setReviewMessage(reviewError instanceof Error ? reviewError.message : String(reviewError));
    } finally {
      setReviewBusy(false);
    }
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
          <span className={`pill ${paper.workspace.workspaceReady ? "pill-success" : ""}`}>
            Workspace{" "}
            {paper.workspace.workspaceReady
              ? "ready"
              : paper.workspace.workspaceAbsPath
                ? "pending"
                : "unconfigured"}
          </span>
          {paper.workspace.attachmentCount ? (
            <span className="pill">{paper.workspace.attachmentCount} attachments</span>
          ) : null}
          {paper.pendingMutationCount ? (
            <span className="pill pill-accent">
              {paper.pendingMutationCount} pending write
            </span>
          ) : (
            <span className="pill pill-success">Synced</span>
          )}
          {paper.lastMutationError ? (
            <span className="pill pill-danger">{paper.lastMutationError}</span>
          ) : null}
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
        <div className="eyebrow">Edit Paper</div>
        <div className="form-grid">
          <label>
            Stage
            <select
              value={patchDraft.stage}
              onChange={(event) =>
                setPatchDraft((current) =>
                  current
                    ? {
                        ...current,
                        stage: event.target.value,
                      }
                    : current,
                )
              }
            >
              <option value="published">published</option>
              <option value="revision">revision</option>
              <option value="under_review">under_review</option>
              <option value="in_prep">in_prep</option>
              <option value="paused">paused</option>
            </select>
          </label>
          <label>
            Venue
            <input
              value={patchDraft.venue}
              onChange={(event) =>
                setPatchDraft((current) =>
                  current
                    ? {
                        ...current,
                        venue: event.target.value,
                      }
                    : current,
                )
              }
            />
          </label>
          <label>
            Next Action
            <input
              value={patchDraft.nextAction}
              onChange={(event) =>
                setPatchDraft((current) =>
                  current
                    ? {
                        ...current,
                        nextAction: event.target.value,
                      }
                    : current,
                )
              }
            />
          </label>
          <label>
            Blocker
            <input
              value={patchDraft.blocker}
              onChange={(event) =>
                setPatchDraft((current) =>
                  current
                    ? {
                        ...current,
                        blocker: event.target.value,
                      }
                    : current,
                )
              }
            />
          </label>
          <label>
            Priority
            <input
              type="number"
              min={1}
              value={patchDraft.priority}
              onChange={(event) =>
                setPatchDraft((current) =>
                  current
                    ? {
                        ...current,
                        priority: event.target.value,
                      }
                    : current,
                )
              }
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" onClick={() => void handleSavePatch()} disabled={savingPatch}>
            {savingPatch ? "Saving..." : "Queue Paper Patch"}
          </button>
        </div>
        {actionMessage ? <p className="meta-note">{actionMessage}</p> : null}
      </div>

      <div className="panel">
        <div className="eyebrow">Local Workspace</div>
        <div className="detail-grid">
          <DetailRow
            label="Workspace path"
            value={paper.workspace.workspaceAbsPath ?? "Workspace root not configured"}
          />
          <DetailRow label="Relative path" value={paper.workspace.workspaceRelPath} />
          <DetailRow
            label="Workspace state"
            value={paper.workspace.workspaceReady ? "ready" : "pending"}
          />
          <DetailRow
            label="Managed attachments"
            value={String(paper.workspace.attachmentCount)}
          />
        </div>
        <div className="form-grid">
          <label>
            Attachment kind
            <select
              value={attachmentDraft.attachmentKind}
              onChange={(event) =>
                setAttachmentDraft({
                  attachmentKind: event.target.value,
                })
              }
            >
              <option value="manuscript">manuscript</option>
              <option value="review">review</option>
              <option value="response_letter">response_letter</option>
              <option value="figure">figure</option>
              <option value="dataset">dataset</option>
              <option value="supplement">supplement</option>
              <option value="note">note</option>
              <option value="other">other</option>
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button type="button" onClick={() => void handleEnsureWorkspace()} disabled={workspaceBusy}>
            {workspaceBusy ? "Working..." : "Ensure Workspace"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleImportAttachments()}
            disabled={workspaceBusy}
          >
            Import Attachments
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleRefreshWorkspace()}
            disabled={workspaceBusy}
          >
            Refresh Workspace
          </button>
        </div>
        {workspaceMessage ? <p className="meta-note">{workspaceMessage}</p> : null}
        {!paper.attachments.length ? (
          <p className="panel-message">
            No managed attachments yet. Ensure the workspace and import local files as managed copies.
          </p>
        ) : (
          <div className="list-stack">
            {paper.attachments.map((attachment) => (
              <article className="list-card" key={attachment.id}>
                <div className="list-card-topline">
                  <span>{attachment.attachmentKind}</span>
                  <span>{attachment.status}</span>
                </div>
                <h3>{attachment.originalFileName}</h3>
                <p>
                  Stored as {attachment.storedFileName}
                  {attachment.sizeBytes ? ` • ${formatBytes(attachment.sizeBytes)}` : ""}
                </p>
                <div className="pill-row">
                  <span className="pill">{attachment.storageMode}</span>
                  <span className="pill">{attachment.relativePath}</span>
                  {attachment.mimeType ? <span className="pill">{attachment.mimeType}</span> : null}
                  {attachment.status === "missing" ? (
                    <span className="pill pill-danger">Missing on disk</span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <div className="eyebrow">Local Notes</div>
        <div className="detail-grid">
          <DetailRow label="Notes directory" value={`${paper.workspace.workspaceRelPath}/notes`} />
          <DetailRow label="Indexed notes" value={String(paper.noteCount)} />
          <DetailRow
            label="Workspace root"
            value={paper.workspace.workspaceAbsPath ?? "Workspace root not configured"}
          />
        </div>
        <div className="form-grid">
          <label>
            Template
            <select
              value={selectedTemplateKind}
              onChange={(event) => setSelectedTemplateKind(event.target.value)}
            >
              {noteTemplates.map((template) => (
                <option key={template.kind} value={template.kind}>
                  {template.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Blank note title
            <input
              value={blankNoteDraft.title}
              onChange={(event) =>
                setBlankNoteDraft({
                  title: event.target.value,
                })
              }
              placeholder="Blank Note"
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" onClick={() => void handleCreateNoteFromTemplate()} disabled={notesBusy}>
            {notesBusy ? "Working..." : "Create From Template"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleCreateBlankNote()}
            disabled={notesBusy}
          >
            Create Blank Note
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleRefreshNotes()}
            disabled={notesBusy}
          >
            Refresh Notes
          </button>
        </div>
        {notesMessage ? <p className="meta-note">{notesMessage}</p> : null}
        {!paper.notes.length ? (
          <p className="panel-message">
            No local notes yet. Ensure the workspace root exists, then create a markdown note from a template or a blank note.
          </p>
        ) : (
          <div className="notes-layout">
            <div className="list-stack">
              {paper.notes.map((note) => (
                <article
                  className={`list-card ${selectedNote?.note.id === note.id ? "list-card-selected" : ""}`}
                  key={note.id}
                >
                  <div className="list-card-topline">
                    <span>{note.templateKind}</span>
                    <span>{note.status}</span>
                  </div>
                  <h3>{note.title}</h3>
                  <p>{note.fileName}</p>
                  <div className="pill-row">
                    <span className="pill">{note.sourceMode}</span>
                    <span className="pill">{formatDateTime(note.updatedAt)}</span>
                    {note.status === "missing" ? (
                      <span className="pill pill-danger">Missing on disk</span>
                    ) : null}
                  </div>
                  <div className="form-actions">
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => void handleOpenNote(note.id)}
                      disabled={notesBusy}
                    >
                      Open Note
                    </button>
                  </div>
                </article>
              ))}
            </div>
            <div className="note-editor-panel">
              {selectedNote ? (
                <>
                  <div className="detail-grid">
                    <DetailRow label="Title" value={selectedNote.note.title} />
                    <DetailRow label="File" value={selectedNote.note.relativePath} />
                    <DetailRow label="Status" value={selectedNote.note.status} />
                  </div>
                  <label className="form-full">
                    Markdown
                    <textarea
                      className="note-editor"
                      rows={18}
                      value={noteContentDraft}
                      onChange={(event) => setNoteContentDraft(event.target.value)}
                      disabled={selectedNote.note.status === "missing" && !paper.workspace.workspaceAbsPath}
                    />
                  </label>
                  <div className="form-actions">
                    <button type="button" onClick={() => void handleSaveNote()} disabled={notesBusy}>
                      {notesBusy ? "Saving..." : "Save Note"}
                    </button>
                  </div>
                </>
              ) : (
                <p className="panel-message">
                  Select a note to edit it. The editor is plain markdown in v1.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="eyebrow">Review Matrix</div>
        <div className="detail-grid">
          <DetailRow label="Review rounds" value={String(paper.reviewRoundCount)} />
          <DetailRow
            label="Generated notes"
            value={
              selectedReviewRoundDetail
                ? [
                    selectedReviewRoundDetail.generatedMatrixNote ? "reviewer_matrix" : null,
                    selectedReviewRoundDetail.generatedResponseNote ? "response_letter" : null,
                  ]
                    .filter(Boolean)
                    .join(", ") || "None"
                : "None"
            }
          />
        </div>
        <div className="form-grid">
          <label>
            Round label
            <input
              value={reviewRoundDraft.roundLabel}
              onChange={(event) =>
                setReviewRoundDraft((current) => ({
                  ...current,
                  roundLabel: event.target.value,
                }))
              }
              placeholder="Round 1"
            />
          </label>
          <label>
            Venue
            <input
              value={reviewRoundDraft.venue}
              onChange={(event) =>
                setReviewRoundDraft((current) => ({
                  ...current,
                  venue: event.target.value,
                }))
              }
              placeholder={paper.venue ?? "Venue"}
            />
          </label>
          <label>
            Decision
            <input
              value={reviewRoundDraft.decisionLabel}
              onChange={(event) =>
                setReviewRoundDraft((current) => ({
                  ...current,
                  decisionLabel: event.target.value,
                }))
              }
              placeholder="Major revision"
            />
          </label>
          <label>
            Status
            <select
              value={reviewRoundDraft.status}
              onChange={(event) =>
                setReviewRoundDraft((current) => ({
                  ...current,
                  status: event.target.value,
                }))
              }
            >
              <option value="open">open</option>
              <option value="archived">archived</option>
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button type="button" onClick={() => void handleCreateReviewRound()} disabled={reviewBusy}>
            {reviewBusy ? "Working..." : "Create Review Round"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleUpdateReviewRound()}
            disabled={reviewBusy || !selectedReviewRoundDetail}
          >
            Save Round
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleGenerateReviewNote("reviewer_matrix")}
            disabled={reviewBusy || !selectedReviewRoundDetail}
          >
            Generate Reviewer Matrix Note
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleGenerateReviewNote("response_letter")}
            disabled={reviewBusy || !selectedReviewRoundDetail}
          >
            Generate Response Letter Note
          </button>
        </div>
        {reviewMessage ? <p className="meta-note">{reviewMessage}</p> : null}

        {!paper.reviewRounds.length ? (
          <p className="panel-message">
            No local review rounds yet. Create one to track reviewer comments and generate markdown drafts.
          </p>
        ) : (
          <div className="notes-layout">
            <div className="list-stack">
              {paper.reviewRounds.map((round) => (
                <article
                  className={`list-card ${selectedReviewRoundId === round.id ? "list-card-selected" : ""}`}
                  key={round.id}
                >
                  <div className="list-card-topline">
                    <span>{round.roundLabel}</span>
                    <span>{round.status}</span>
                  </div>
                  <h3>{round.venue ?? paper.venue ?? "Venue pending"}</h3>
                  <p>{round.decisionLabel ?? "Decision pending"}</p>
                  <div className="pill-row">
                    <span className="pill">{round.reviewerCount} reviewers</span>
                    {round.generatedMatrixNoteId ? (
                      <span className="pill pill-success">Matrix note linked</span>
                    ) : null}
                    {round.generatedResponseNoteId ? (
                      <span className="pill pill-success">Response note linked</span>
                    ) : null}
                  </div>
                  <div className="form-actions">
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => {
                        setSelectedReviewRoundId(round.id);
                        resetReviewCommentDraft();
                      }}
                      disabled={reviewBusy}
                    >
                      Open Round
                    </button>
                  </div>
                </article>
              ))}
            </div>
            <div className="note-editor-panel">
              {selectedReviewRoundDetail ? (
                <>
                  <div className="detail-grid">
                    <DetailRow
                      label="Selected round"
                      value={selectedReviewRoundDetail.round.roundLabel}
                    />
                    <DetailRow
                      label="Comments"
                      value={String(selectedReviewRoundDetail.comments.length)}
                    />
                    <DetailRow
                      label="Generated matrix note"
                      value={
                        selectedReviewRoundDetail.generatedMatrixNote?.relativePath ??
                        "Not generated"
                      }
                    />
                    <DetailRow
                      label="Generated response note"
                      value={
                        selectedReviewRoundDetail.generatedResponseNote?.relativePath ??
                        "Not generated"
                      }
                    />
                  </div>
                  <div className="pill-row">
                    {selectedReviewRoundDetail.generatedMatrixNote ? (
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() =>
                          void handleOpenNote(selectedReviewRoundDetail.generatedMatrixNote!.noteId)
                        }
                        disabled={notesBusy}
                      >
                        Open Reviewer Matrix Note
                      </button>
                    ) : null}
                    {selectedReviewRoundDetail.generatedResponseNote ? (
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() =>
                          void handleOpenNote(
                            selectedReviewRoundDetail.generatedResponseNote!.noteId,
                          )
                        }
                        disabled={notesBusy}
                      >
                        Open Response Letter Note
                      </button>
                    ) : null}
                  </div>
                  <div className="list-stack">
                    {selectedReviewRoundDetail.comments.length ? (
                      selectedReviewRoundDetail.comments.map((comment) => (
                        <article
                          className={`list-card ${selectedReviewCommentId === comment.id ? "list-card-selected" : ""}`}
                          key={comment.id}
                        >
                          <div className="list-card-topline">
                            <span>{comment.reviewerLabel}</span>
                            <span>{comment.disposition}</span>
                          </div>
                          <h3>{comment.commentCode ?? `Comment ${comment.sortOrder}`}</h3>
                          <p>{comment.commentText}</p>
                          <div className="pill-row">
                            {comment.category ? <span className="pill">{comment.category}</span> : null}
                            <span className="pill">Order {comment.sortOrder}</span>
                          </div>
                          <div className="form-actions">
                            <button
                              type="button"
                              className="button-secondary"
                              onClick={() => {
                                setSelectedReviewCommentId(comment.id);
                                setReviewCommentDraft({
                                  reviewerLabel: comment.reviewerLabel,
                                  commentCode: comment.commentCode ?? "",
                                  commentText: comment.commentText,
                                  category: comment.category ?? "",
                                  disposition: comment.disposition,
                                  responseSummary: comment.responseSummary ?? "",
                                  actionNote: comment.actionNote ?? "",
                                });
                              }}
                              disabled={reviewBusy}
                            >
                              Edit Comment
                            </button>
                          </div>
                        </article>
                      ))
                    ) : (
                      <p className="panel-message">
                        No comments recorded for this round yet.
                      </p>
                    )}
                  </div>
                  <div className="form-grid">
                    <label>
                      Reviewer
                      <input
                        value={reviewCommentDraft.reviewerLabel}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            reviewerLabel: event.target.value,
                          }))
                        }
                        placeholder="Reviewer 1"
                      />
                    </label>
                    <label>
                      Comment code
                      <input
                        value={reviewCommentDraft.commentCode}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            commentCode: event.target.value,
                          }))
                        }
                        placeholder="R1-1"
                      />
                    </label>
                    <label>
                      Category
                      <input
                        value={reviewCommentDraft.category}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            category: event.target.value,
                          }))
                        }
                        placeholder="method"
                      />
                    </label>
                    <label>
                      Disposition
                      <select
                        value={reviewCommentDraft.disposition}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            disposition: event.target.value,
                          }))
                        }
                      >
                        <option value="todo">todo</option>
                        <option value="accepted">accepted</option>
                        <option value="rebutted">rebutted</option>
                        <option value="not_applicable">not_applicable</option>
                        <option value="done">done</option>
                      </select>
                    </label>
                    <label className="form-full">
                      Comment text
                      <textarea
                        rows={4}
                        value={reviewCommentDraft.commentText}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            commentText: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="form-full">
                      Response summary
                      <textarea
                        rows={3}
                        value={reviewCommentDraft.responseSummary}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            responseSummary: event.target.value,
                          }))
                        }
                      />
                    </label>
                    <label className="form-full">
                      Action note
                      <textarea
                        rows={3}
                        value={reviewCommentDraft.actionNote}
                        onChange={(event) =>
                          setReviewCommentDraft((current) => ({
                            ...current,
                            actionNote: event.target.value,
                          }))
                        }
                      />
                    </label>
                  </div>
                  <div className="form-actions">
                    <button
                      type="button"
                      onClick={() => void handleSaveReviewComment()}
                      disabled={reviewBusy}
                    >
                      {reviewBusy
                        ? "Working..."
                        : selectedReviewCommentId
                          ? "Save Comment"
                          : "Add Comment"}
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => resetReviewCommentDraft()}
                      disabled={reviewBusy}
                    >
                      Clear Draft
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      onClick={() => void handleDeleteReviewComment()}
                      disabled={reviewBusy || !selectedReviewCommentId}
                    >
                      Delete Comment
                    </button>
                  </div>
                </>
              ) : (
                <p className="panel-message">
                  Select a review round to manage structured reviewer comments.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="eyebrow">Add Progress Event</div>
        <div className="form-grid">
          <label>
            Stage
            <select
              value={progressDraft.stage}
              onChange={(event) =>
                setProgressDraft((current) => ({
                  ...current,
                  stage: event.target.value,
                }))
              }
            >
              <option value="published">published</option>
              <option value="revision">revision</option>
              <option value="under_review">under_review</option>
              <option value="in_prep">in_prep</option>
              <option value="paused">paused</option>
            </select>
          </label>
          <label>
            Happened At
            <input
              type="datetime-local"
              value={progressDraft.happenedAt}
              onChange={(event) =>
                setProgressDraft((current) => ({
                  ...current,
                  happenedAt: event.target.value,
                }))
              }
            />
          </label>
          <label className="form-full">
            Summary
            <textarea
              rows={3}
              value={progressDraft.summary}
              onChange={(event) =>
                setProgressDraft((current) => ({
                  ...current,
                  summary: event.target.value,
                }))
              }
            />
          </label>
          <label>
            Owner
            <input
              value={progressDraft.owner}
              onChange={(event) =>
                setProgressDraft((current) => ({
                  ...current,
                  owner: event.target.value,
                }))
              }
            />
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            onClick={() => void handleCreateProgressEvent()}
            disabled={savingProgress}
          >
            {savingProgress ? "Saving..." : "Queue Progress Event"}
          </button>
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
  onWriteResult,
  dataVersion,
}: {
  syncStatus: SyncStatusRead;
  syncing: boolean;
  onSyncNow: () => Promise<void>;
  onDisconnect: () => Promise<void>;
  onClearLocalCache: () => Promise<void>;
  onWriteResult: (result: WriteActionResultRead) => Promise<WriteActionResultRead>;
  dataVersion: number;
}) {
  const [policies, setPolicies] = useState<SubscriptionPolicyRead[]>([]);
  const [pendingMutations, setPendingMutations] = useState<PendingMutationRead[]>([]);
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatusRead | null>(null);
  const [drafts, setDrafts] = useState<Record<string, SubscriptionPolicyDraft>>({});
  const [loading, setLoading] = useState(true);
  const [savingPolicyId, setSavingPolicyId] = useState<string | null>(null);
  const [workspaceBusy, setWorkspaceBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        const [nextPolicies, nextPending, nextWorkspaceStatus] = await Promise.all([
          desktopApi.listSubscriptionPolicies(),
          desktopApi.listPendingMutations(),
          desktopApi.getWorkspaceStatus(),
        ]);
        setPolicies(nextPolicies);
        setPendingMutations(nextPending);
        setWorkspaceStatus(nextWorkspaceStatus);
        setDrafts(
          Object.fromEntries(
            nextPolicies.map((policy) => [
              policy.id,
              {
                enabled: policy.enabled,
                frequencyCap: String(policy.frequencyCap),
                quietStart: extractQuietHoursDraft(policy.quietHours).start,
                quietEnd: extractQuietHoursDraft(policy.quietHours).end,
              },
            ]),
          ),
        );
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : String(loadError));
      } finally {
        setLoading(false);
      }
    })();
  }, [dataVersion]);

  async function handleSavePolicy(policy: SubscriptionPolicyRead) {
    const draft = drafts[policy.id];
    if (!draft) {
      return;
    }
    setSavingPolicyId(policy.id);
    try {
      const result = await desktopApi.queueSubscriptionPolicyPatch({
        subscriptionPolicyId: policy.id,
        enabled: draft.enabled,
        frequencyCap: Number(draft.frequencyCap),
        quietHours: buildQuietHoursPatch(policy.quietHours, draft.quietStart, draft.quietEnd),
      } satisfies QueueSubscriptionPolicyPatchInput);
      await onWriteResult(result);
      setActionMessage(buildWriteMessage(result, "Subscription policy queued"));
    } catch (saveError) {
      setActionMessage(
        saveError instanceof Error ? saveError.message : String(saveError),
      );
    } finally {
      setSavingPolicyId(null);
    }
  }

  async function handleChooseWorkspaceRoot() {
    const selectedPath = await open({
      directory: true,
      multiple: false,
      title: "Choose desktop workspace root",
    });
    if (!selectedPath || Array.isArray(selectedPath)) {
      return;
    }

    setWorkspaceBusy(true);
    try {
      const result = await desktopApi.chooseWorkspaceRoot({
        selectedPath,
      } satisfies ChooseWorkspaceRootInput);
      setWorkspaceStatus(result);
      setActionMessage("Workspace root saved.");
    } catch (workspaceError) {
      setActionMessage(
        workspaceError instanceof Error ? workspaceError.message : String(workspaceError),
      );
    } finally {
      setWorkspaceBusy(false);
    }
  }

  async function handleClearWorkspaceRoot() {
    setWorkspaceBusy(true);
    try {
      const result = await desktopApi.clearWorkspaceRoot();
      setWorkspaceStatus(result);
      setActionMessage("Workspace root cleared. Managed files were left untouched.");
    } catch (workspaceError) {
      setActionMessage(
        workspaceError instanceof Error ? workspaceError.message : String(workspaceError),
      );
    } finally {
      setWorkspaceBusy(false);
    }
  }

  return (
    <section className="page-grid">
      <div className="panel">
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
          <DetailRow label="Event cursor" value={String(syncStatus.lastEventSequence)} />
          <DetailRow
            label="Pending writes"
            value={String(syncStatus.pendingMutationCount)}
          />
          <DetailRow
            label="Failed writes"
            value={String(syncStatus.failedMutationCount)}
          />
        </div>
        <div className="sidebar-actions">
          <button type="button" onClick={() => void onSyncNow()} disabled={syncing}>
            {syncing ? "Syncing..." : "Manual Sync"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void onClearLocalCache()}
          >
            Clear Local Cache
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void onDisconnect()}
          >
            Disconnect Device
          </button>
        </div>
        {syncStatus.recentOutboxErrors.length ? (
          <div className="meta-list">
            {syncStatus.recentOutboxErrors.map((entry) => (
              <div key={entry} className="meta-note">
                {entry}
              </div>
            ))}
          </div>
        ) : null}
      </div>

      <div className="panel">
        <div className="eyebrow">Subscription Policies</div>
        {loading ? <LoadingState label="Loading cached subscription policies" /> : null}
        {error ? <p className="panel-message">{error}</p> : null}
        {!loading && !policies.length ? (
          <p className="panel-message">
            No subscription policies are cached yet. Run sync to edit desktop-side pulse settings.
          </p>
        ) : null}
        <div className="list-stack">
          {policies.map((policy) => {
            const draft = drafts[policy.id];
            if (!draft) {
              return null;
            }
            return (
              <article className="list-card" key={policy.id}>
                <div className="list-card-topline">
                  <span>{policy.channel}</span>
                  <span>{policy.frequency}</span>
                </div>
                <div className="form-grid">
                  <label className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={draft.enabled}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [policy.id]: {
                            ...draft,
                            enabled: event.target.checked,
                          },
                        }))
                      }
                    />
                    Enabled
                  </label>
                  <label>
                    Frequency cap
                    <input
                      type="number"
                      min={1}
                      value={draft.frequencyCap}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [policy.id]: {
                            ...draft,
                            frequencyCap: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                  <label>
                    Quiet start
                    <input
                      type="time"
                      value={draft.quietStart}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [policy.id]: {
                            ...draft,
                            quietStart: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                  <label>
                    Quiet end
                    <input
                      type="time"
                      value={draft.quietEnd}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [policy.id]: {
                            ...draft,
                            quietEnd: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                </div>
                <div className="pill-row">
                  {policy.pendingMutationCount ? (
                    <span className="pill pill-accent">
                      {policy.pendingMutationCount} pending write
                    </span>
                  ) : (
                    <span className="pill pill-success">Synced</span>
                  )}
                  {policy.lastMutationError ? (
                    <span className="pill pill-danger">{policy.lastMutationError}</span>
                  ) : null}
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    onClick={() => void handleSavePolicy(policy)}
                    disabled={savingPolicyId === policy.id}
                  >
                    {savingPolicyId === policy.id ? "Saving..." : "Queue Policy Patch"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
        {actionMessage ? <p className="meta-note">{actionMessage}</p> : null}
      </div>

      <div className="panel">
        <div className="eyebrow">Workspace</div>
        <h1>Local paper workspace</h1>
        <div className="detail-grid">
          <DetailRow
            label="Root path"
            value={workspaceStatus?.rootPath ?? "Not configured"}
          />
          <DetailRow
            label="Status"
            value={workspaceStatus?.status ?? "unknown"}
          />
          <DetailRow
            label="Layout version"
            value={String(workspaceStatus?.layoutVersion ?? 1)}
          />
          <DetailRow
            label="Managed attachments"
            value={String(workspaceStatus?.managedAttachmentCount ?? 0)}
          />
        </div>
        {workspaceStatus?.lastError ? (
          <p className="meta-note">{workspaceStatus.lastError}</p>
        ) : (
          <p className="panel-message">
            Managed attachments stay local in v1. Changing the root does not move old files.
          </p>
        )}
        <div className="sidebar-actions">
          <button
            type="button"
            onClick={() => void handleChooseWorkspaceRoot()}
            disabled={workspaceBusy}
          >
            {workspaceBusy ? "Working..." : "Choose Workspace Root"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => void handleClearWorkspaceRoot()}
            disabled={workspaceBusy}
          >
            Clear Workspace Root
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="eyebrow">Pending Outbox</div>
        {!pendingMutations.length ? (
          <p className="panel-message">No queued or failed mutations.</p>
        ) : (
          <div className="list-stack">
            {pendingMutations.map((mutation) => (
              <article className="list-card" key={mutation.id}>
                <div className="list-card-topline">
                  <span>{mutation.mutationType}</span>
                  <span>{mutation.status}</span>
                </div>
                <p>
                  Resource {mutation.resourceType}
                  {mutation.resourceId ? ` / ${mutation.resourceId}` : ""}
                </p>
                <div className="pill-row">
                  <span className="pill">Attempts {mutation.attemptCount}</span>
                  {mutation.lastError ? (
                    <span className="pill pill-danger">{mutation.lastError}</span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
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

function buildWriteMessage(result: WriteActionResultRead, prefix: string) {
  if (result.syncSucceeded) {
    return `${prefix}. Sync applied or queued successfully.`;
  }
  if (result.syncError) {
    return `${prefix}. Kept in local outbox: ${result.syncError}`;
  }
  if (!result.syncAttempted) {
    return `${prefix}. Stored in local outbox until the next sync.`;
  }
  return prefix;
}

function buildAttachmentImportMessage(response: ImportPaperAttachmentsResponse) {
  const imported = response.results.filter((result) => result.status === "imported").length;
  const duplicates = response.results.filter((result) => result.status === "duplicate").length;
  const failed = response.results.filter((result) => result.status === "failed").length;
  return `Workspace updated. Imported ${imported}, duplicate ${duplicates}, failed ${failed}.`;
}

function toDateTimeLocalValue(isoTimestamp: string) {
  const date = new Date(isoTimestamp);
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  const hours = `${date.getHours()}`.padStart(2, "0");
  const minutes = `${date.getMinutes()}`.padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function toIsoTimestamp(value: string) {
  if (!value) {
    return new Date().toISOString();
  }
  return new Date(value).toISOString();
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

function formatBytes(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default App;
