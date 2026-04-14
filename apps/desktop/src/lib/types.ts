export type UserConnectionRead = {
  userId: string;
  name: string;
  email: string | null;
  field: string | null;
  baseUrl: string;
  deviceId: string;
  deviceDisplayName: string;
};

export type SyncStatusRead = {
  connected: boolean;
  baseUrl: string | null;
  deviceId: string | null;
  deviceDisplayName: string | null;
  lastSyncedAt: string | null;
  lastEventSequence: number;
  lastError: string | null;
  currentUserSummary: UserConnectionRead | null;
};

export type PaperListItemRead = {
  id: string;
  userId: string;
  title: string;
  paperType: string;
  stage: string;
  venue: string | null;
  priority: number;
  nextAction: string | null;
  blocker: string | null;
  lastTouchAt: string | null;
  progressPercentage: number;
  updatedAt: string | null;
};

export type DigestHighlightRead = {
  sortOrder: number;
  pulseCardId: string;
  cardType: string;
  sourcePaperId: string | null;
  title: string;
  summary: string;
  whyNow: string | null;
  paper: PaperListItemRead | null;
};

export type TodayOverviewRead = {
  state: string;
  issueId: string | null;
  issueDate: string | null;
  status: string | null;
  title: string | null;
  summary: string | null;
  highlightCount: number;
  selectedCardCount: number;
  deepLinkPath: string | null;
  highlights: DigestHighlightRead[];
  message: string | null;
  updatedAt: string | null;
};

export type ProgressEventRead = {
  id: string;
  paperId: string;
  stage: string;
  happenedAt: string;
  summary: string;
  owner: string | null;
};

export type SignalSnapshotRead = {
  id: string;
  paperId: string;
  source: string;
  citationCount: number | null;
  downloadCount: number | null;
  readCount: number | null;
  inclusionStatus: string | null;
  fetchedAt: string;
};

export type PaperDetailRead = {
  id: string;
  userId: string;
  title: string;
  paperType: string;
  stage: string;
  venue: string | null;
  priority: number;
  nextAction: string | null;
  blocker: string | null;
  lastTouchAt: string | null;
  progressPercentage: number;
  updatedAt: string | null;
  identifiers: Record<string, unknown>;
  sourceLinks: string[];
  progressEvents: ProgressEventRead[];
  signalSnapshots: SignalSnapshotRead[];
};

export type AppBootstrapRead = {
  syncStatus: SyncStatusRead;
  todayOverview: TodayOverviewRead;
};

export type ConnectDeviceInput = {
  baseUrl: string;
  deviceToken: string;
  deviceDisplayName?: string;
};

export type ConnectDeviceResponse = {
  syncStatus: SyncStatusRead;
  connection: UserConnectionRead;
  todayOverview: TodayOverviewRead;
};

export type SyncNowResponse = {
  syncStatus: SyncStatusRead;
  pagesFetched: number;
  eventsApplied: number;
  acknowledgedSequence: number;
  todayOverview: TodayOverviewRead;
};

export type ListPapersInput = {
  limit?: number;
  paperType?: string;
  stage?: string;
};
