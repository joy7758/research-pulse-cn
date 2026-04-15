import { invoke } from "@tauri-apps/api/core";

import type {
  AppBootstrapRead,
  ChooseWorkspaceRootInput,
  ConnectDeviceInput,
  ConnectDeviceResponse,
  CreateBlankPaperNoteInput,
  CreatePaperNoteFromTemplateInput,
  ImportPaperAttachmentsInput,
  ImportPaperAttachmentsResponse,
  ListPapersInput,
  NoteActionResultRead,
  NoteTemplateRead,
  PaperAttachmentRead,
  PaperDetailRead,
  PaperListItemRead,
  PaperNoteDetailRead,
  PaperNoteSummaryRead,
  PaperWorkspaceRead,
  PendingMutationRead,
  QueuePaperPatchInput,
  QueueProgressEventCreateInput,
  QueueSubscriptionPolicyPatchInput,
  SavePaperNoteInput,
  SubscriptionPolicyRead,
  SyncNowResponse,
  SyncStatusRead,
  TodayOverviewRead,
  WorkspaceStatusRead,
  WriteActionResultRead,
} from "./types";

export const desktopApi = {
  appBootstrap: () => invoke<AppBootstrapRead>("appBootstrap"),
  connectDevice: (input: ConnectDeviceInput) =>
    invoke<ConnectDeviceResponse>("connectDevice", { input }),
  disconnectDevice: () => invoke<SyncStatusRead>("disconnectDevice"),
  clearLocalCache: () => invoke<SyncStatusRead>("clearLocalCache"),
  syncNow: () => invoke<SyncNowResponse>("syncNow"),
  getSyncStatus: () => invoke<SyncStatusRead>("getSyncStatus"),
  getTodayOverview: () => invoke<TodayOverviewRead>("getTodayOverview"),
  listPapers: (filters?: ListPapersInput) =>
    invoke<PaperListItemRead[]>("listPapers", { filters }),
  getPaperDetail: (paperId: string) =>
    invoke<PaperDetailRead>("getPaperDetail", { paperId }),
  listSubscriptionPolicies: () =>
    invoke<SubscriptionPolicyRead[]>("listSubscriptionPolicies"),
  listPendingMutations: () =>
    invoke<PendingMutationRead[]>("listPendingMutations"),
  getWorkspaceStatus: () => invoke<WorkspaceStatusRead>("getWorkspaceStatus"),
  chooseWorkspaceRoot: (input: ChooseWorkspaceRootInput) =>
    invoke<WorkspaceStatusRead>("chooseWorkspaceRoot", { input }),
  clearWorkspaceRoot: () => invoke<WorkspaceStatusRead>("clearWorkspaceRoot"),
  ensurePaperWorkspace: (paperId: string) =>
    invoke<PaperWorkspaceRead>("ensurePaperWorkspace", {
      input: { paperId },
    }),
  getPaperWorkspace: (paperId: string) =>
    invoke<PaperWorkspaceRead>("getPaperWorkspace", { paperId }),
  listPaperAttachments: (paperId: string) =>
    invoke<PaperAttachmentRead[]>("listPaperAttachments", { paperId }),
  listNoteTemplates: () => invoke<NoteTemplateRead[]>("listNoteTemplates"),
  listPaperNotes: (paperId: string) =>
    invoke<PaperNoteSummaryRead[]>("listPaperNotes", {
      input: { paperId },
    }),
  createPaperNoteFromTemplate: (input: CreatePaperNoteFromTemplateInput) =>
    invoke<NoteActionResultRead>("createPaperNoteFromTemplate", { input }),
  createBlankPaperNote: (input: CreateBlankPaperNoteInput) =>
    invoke<NoteActionResultRead>("createBlankPaperNote", { input }),
  getPaperNote: (noteId: string) =>
    invoke<PaperNoteDetailRead>("getPaperNote", { noteId }),
  savePaperNote: (input: SavePaperNoteInput) =>
    invoke<NoteActionResultRead>("savePaperNote", { input }),
  refreshPaperNotes: (paperId: string) =>
    invoke<PaperNoteSummaryRead[]>("refreshPaperNotes", {
      input: { paperId },
    }),
  importPaperAttachments: (input: ImportPaperAttachmentsInput) =>
    invoke<ImportPaperAttachmentsResponse>("importPaperAttachments", { input }),
  refreshPaperWorkspace: (paperId: string) =>
    invoke<PaperWorkspaceRead>("refreshPaperWorkspace", {
      input: { paperId },
    }),
  queuePaperPatch: (input: QueuePaperPatchInput) =>
    invoke<WriteActionResultRead>("queuePaperPatch", { input }),
  queueProgressEventCreate: (input: QueueProgressEventCreateInput) =>
    invoke<WriteActionResultRead>("queueProgressEventCreate", { input }),
  queueSubscriptionPolicyPatch: (input: QueueSubscriptionPolicyPatchInput) =>
    invoke<WriteActionResultRead>("queueSubscriptionPolicyPatch", { input }),
};
