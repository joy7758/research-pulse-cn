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
  pendingMutationCount: number;
  failedMutationCount: number;
  recentOutboxErrors: string[];
  currentUserSummary: UserConnectionRead | null;
};

export type PendingMutationRead = {
  id: string;
  clientMutationId: string;
  mutationType: string;
  resourceType: string;
  resourceId: string | null;
  payload: Record<string, unknown>;
  status: string;
  attemptCount: number;
  lastError: string | null;
  resultingEventSequence: number | null;
  createdAt: string;
  updatedAt: string;
  lastAttemptedAt: string | null;
};

export type SubscriptionPolicyRead = {
  id: string;
  userId: string;
  channel: string;
  enabled: boolean;
  frequency: string;
  quietHours: Record<string, unknown> | null;
  frequencyCap: number;
  policy: Record<string, unknown>;
  updatedAt: string | null;
  pendingMutationCount: number;
  lastMutationError: string | null;
};

export type QuietHoursWindowRead = {
  start: string;
  end: string;
  timezone: string;
};

export type DeliveryControlSettingsRead = {
  id: string;
  userId: string;
  channel: string;
  enabled: boolean;
  frequency: string;
  quietHours: QuietHoursWindowRead[];
  rawQuietHours: Record<string, unknown> | null;
  timezone: string;
  allowedWeekdays: number[];
  mutedUntil: string | null;
  minimumSelectedCards: number | null;
  skipIfNoTodayFocus: boolean;
  frequencyCap: number;
  updatedAt: string | null;
  pendingMutationCount: number;
  lastMutationError: string | null;
  rawPolicy: Record<string, unknown>;
  localSettingsError: string | null;
};

export type DeliveryControlLocalHintRead = {
  subscriptionPolicyId: string;
  channel: string;
  effectiveTimezone: string;
  currentLocalTime: string;
  localWeekday: number;
  quietHoursActive: boolean;
  mutedUntilActive: boolean;
  weekdayBlocked: boolean;
  nextAllowedAtApprox: string | null;
  notes: string[];
  localSettingsError: string | null;
};

export type WorkspaceStatusRead = {
  rootPath: string | null;
  status: "unconfigured" | "ready" | "missing" | "invalid" | string;
  layoutVersion: number;
  lastValidatedAt: string | null;
  lastError: string | null;
  managedAttachmentCount: number;
};

export type PaperWorkspaceRead = {
  paperId: string;
  paperTitle: string;
  workspaceRelPath: string;
  workspaceAbsPath: string | null;
  workspaceReady: boolean;
  attachmentCount: number;
  lastImportedAt: string | null;
};

export type PaperAttachmentRead = {
  id: string;
  paperId: string;
  attachmentKind: string;
  storageMode: string;
  originalFileName: string;
  storedFileName: string;
  fileExtension: string | null;
  relativePath: string;
  absolutePath: string | null;
  sourcePath: string;
  sizeBytes: number | null;
  mimeType: string | null;
  sha256: string | null;
  status: "ready" | "missing" | string;
  importedAt: string;
  updatedAt: string;
  lastOpenedAt: string | null;
};

export type NoteTemplateRead = {
  kind: string;
  title: string;
  description: string;
  defaultFileNamePattern: string;
};

export type PaperNoteSummaryRead = {
  id: string;
  paperId: string;
  templateKind: string;
  title: string;
  fileName: string;
  relativePath: string;
  absolutePath: string | null;
  contentFormat: "markdown" | string;
  sourceMode: "template" | "blank" | string;
  status: "ready" | "missing" | string;
  sizeBytes: number | null;
  sha256: string | null;
  createdAt: string;
  updatedAt: string;
  lastOpenedAt: string | null;
};

export type PaperNoteDetailRead = {
  note: PaperNoteSummaryRead;
  content: string | null;
};

export type NoteActionResultRead = {
  note: PaperNoteDetailRead;
  message: string;
};

export type ReviewRoundSummaryRead = {
  id: string;
  paperId: string;
  roundLabel: string;
  venue: string | null;
  decisionLabel: string | null;
  status: "open" | "archived" | string;
  sourceMode: "manual" | string;
  reviewerCount: number;
  generatedResponseNoteId: string | null;
  generatedMatrixNoteId: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ReviewCommentItemRead = {
  id: string;
  reviewRoundId: string;
  paperId: string;
  reviewerLabel: string;
  commentCode: string | null;
  sortOrder: number;
  commentText: string;
  category: string | null;
  disposition: "todo" | "accepted" | "rebutted" | "not_applicable" | "done" | string;
  responseSummary: string | null;
  actionNote: string | null;
  createdAt: string;
  updatedAt: string;
};

export type GeneratedReviewNoteRead = {
  kind: "reviewer_matrix" | "response_letter" | string;
  noteId: string;
  title: string;
  relativePath: string;
  status: string;
  updatedAt: string;
};

export type ReviewRoundDetailRead = {
  round: ReviewRoundSummaryRead;
  comments: ReviewCommentItemRead[];
  generatedResponseNote: GeneratedReviewNoteRead | null;
  generatedMatrixNote: GeneratedReviewNoteRead | null;
};

export type ReviewActionResultRead = {
  message: string;
  round: ReviewRoundSummaryRead | null;
  comment: ReviewCommentItemRead | null;
  detail: ReviewRoundDetailRead | null;
  generatedNote: GeneratedReviewNoteRead | null;
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
  pendingMutationCount: number;
  lastMutationError: string | null;
  attachmentCount: number;
  workspaceReady: boolean;
};

export type PulseCardTypeRead =
  | "signal_change"
  | "stalled_progress"
  | "deadline_risk"
  | "today_suggestion"
  | "next_action"
  | "yesterday_summary"
  | "related_paper"
  | string;

export type DigestHighlightRead = {
  sortOrder: number;
  pulseCardId: string;
  cardType: PulseCardTypeRead;
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
  pendingMutationCount: number;
  lastMutationError: string | null;
  workspace: PaperWorkspaceRead;
  attachments: PaperAttachmentRead[];
  notes: PaperNoteSummaryRead[];
  noteCount: number;
  reviewRounds: ReviewRoundSummaryRead[];
  reviewRoundCount: number;
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
  pushedCount: number;
  appliedCount: number;
  duplicateCount: number;
  failedCount: number;
  pagesFetched: number;
  eventsApplied: number;
  acknowledgedSequence: number;
  pendingMutationCount: number;
  failedMutationCount: number;
  todayOverview: TodayOverviewRead;
};

export type ListPapersInput = {
  limit?: number;
  paperType?: string;
  stage?: string;
};

export type ChooseWorkspaceRootInput = {
  selectedPath: string;
};

export type ImportPaperAttachmentsInput = {
  paperId: string;
  attachmentKind: string;
  sourcePaths: string[];
};

export type PaperAttachmentImportResultRead = {
  sourcePath: string;
  status: "imported" | "duplicate" | "failed" | string;
  message: string | null;
  attachment: PaperAttachmentRead | null;
};

export type ImportPaperAttachmentsResponse = {
  workspace: PaperWorkspaceRead;
  results: PaperAttachmentImportResultRead[];
};

export type ListPaperNotesInput = {
  paperId: string;
};

export type CreatePaperNoteFromTemplateInput = {
  paperId: string;
  templateKind: string;
};

export type CreateBlankPaperNoteInput = {
  paperId: string;
  title?: string | null;
};

export type SavePaperNoteInput = {
  noteId: string;
  content: string;
};

export type RefreshPaperNotesInput = {
  paperId: string;
};

export type ListReviewRoundsInput = {
  paperId: string;
};

export type CreateReviewRoundInput = {
  paperId: string;
  roundLabel: string;
  venue?: string | null;
  decisionLabel?: string | null;
};

export type UpdateReviewRoundInput = {
  reviewRoundId: string;
  roundLabel?: string | null;
  venue?: string | null;
  decisionLabel?: string | null;
  status?: string | null;
};

export type ListReviewCommentsInput = {
  reviewRoundId: string;
};

export type AddReviewCommentInput = {
  reviewRoundId: string;
  reviewerLabel: string;
  commentCode?: string | null;
  commentText: string;
  category?: string | null;
  disposition?: string | null;
  responseSummary?: string | null;
  actionNote?: string | null;
};

export type UpdateReviewCommentInput = {
  commentId: string;
  reviewerLabel?: string | null;
  commentCode?: string | null;
  commentText?: string | null;
  category?: string | null;
  disposition?: string | null;
  responseSummary?: string | null;
  actionNote?: string | null;
};

export type DeleteReviewCommentInput = {
  commentId: string;
};

export type QueuePaperPatchInput = {
  paperId: string;
  stage?: string | null;
  venue?: string | null;
  nextAction?: string | null;
  blocker?: string | null;
  priority?: number | null;
  lastTouchAt?: string | null;
};

export type QueueProgressEventCreateInput = {
  paperId: string;
  stage: string;
  happenedAt: string;
  summary: string;
  owner?: string | null;
};

export type QueueSubscriptionPolicyPatchInput = {
  subscriptionPolicyId: string;
  enabled?: boolean | null;
  quietHours?: Record<string, unknown> | null;
  frequencyCap?: number | null;
  policy?: Record<string, unknown> | null;
};

export type WriteActionResultRead = {
  mutation: PendingMutationRead;
  syncAttempted: boolean;
  syncSucceeded: boolean;
  syncError: string | null;
  syncStatus: SyncStatusRead;
  pendingMutationCount: number;
  failedMutationCount: number;
};
