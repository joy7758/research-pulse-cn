import importCommitJson from "../data/mock/import_commit.json";
import importPreviewJson from "../data/mock/import_preview.json";
import progressSummaryJson from "../data/mock/paper_progress_summary.json";
import researchPulseJson from "../data/mock/research_pulse.json";
import type { ChannelStateHint, DataMode, FrontendShellData } from "./types";

const channelStates: ChannelStateHint[] = [
  {
    id: "pulse",
    label: "Research Pulse",
    state: "draft",
    message: "当前页面展示的是本地 mock 草稿，不触发真实生成任务。",
  },
  {
    id: "official-account",
    label: "公众号摘要",
    state: "not_sent",
    message: "只保留草稿入口，不触发真实微信发送。",
  },
  {
    id: "desktop",
    label: "桌面通知",
    state: "not_sent",
    message: "只保留通知草稿，不调用系统通知。",
  },
  {
    id: "mini-program",
    label: "小程序详情",
    state: "preview",
    message: "只展示 share-safe 预览，不做真实小程序交互。",
  },
];

const mockShellData: FrontendShellData = {
  progressSummary: progressSummaryJson as FrontendShellData["progressSummary"],
  importPreview: importPreviewJson as FrontendShellData["importPreview"],
  importCommit: importCommitJson as FrontendShellData["importCommit"],
  researchPulse: researchPulseJson as FrontendShellData["researchPulse"],
  channelStates,
};

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export async function loadShellData(mode: DataMode): Promise<FrontendShellData> {
  if (mode === "api") {
    throw new Error(
      "Frontend-1 当前只启用 mock mode。real API mode 仅预留后续内部联调，不在本轮启用。",
    );
  }

  return clone(mockShellData);
}

export const apiModePlan = {
  importPreview: "POST /papers/import-preview",
  importCommit: "POST /papers/import-commit",
  progressSummary: "GET /papers/progress/summary",
  pulseContext: "GET /papers/progress/pulse-context",
  dailyPulse: "POST /pulse/papers/daily",
} as const;
