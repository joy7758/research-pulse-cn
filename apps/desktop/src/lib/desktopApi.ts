import { invoke } from "@tauri-apps/api/core";

import type {
  AppBootstrapRead,
  ConnectDeviceInput,
  ConnectDeviceResponse,
  ListPapersInput,
  PaperDetailRead,
  PaperListItemRead,
  PendingMutationRead,
  QueuePaperPatchInput,
  QueueProgressEventCreateInput,
  QueueSubscriptionPolicyPatchInput,
  SubscriptionPolicyRead,
  SyncNowResponse,
  SyncStatusRead,
  TodayOverviewRead,
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
  queuePaperPatch: (input: QueuePaperPatchInput) =>
    invoke<WriteActionResultRead>("queuePaperPatch", { input }),
  queueProgressEventCreate: (input: QueueProgressEventCreateInput) =>
    invoke<WriteActionResultRead>("queueProgressEventCreate", { input }),
  queueSubscriptionPolicyPatch: (input: QueueSubscriptionPolicyPatchInput) =>
    invoke<WriteActionResultRead>("queueSubscriptionPolicyPatch", { input }),
};
