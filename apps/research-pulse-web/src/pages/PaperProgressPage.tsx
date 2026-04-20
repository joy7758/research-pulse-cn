import { useDeferredValue, useMemo, useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { ProgressFilterBar } from "../components/ProgressFilterBar";
import { ProgressPaperCard } from "../components/ProgressPaperCard";
import { StatusBanner } from "../components/StatusBanner";
import { SummaryCard } from "../components/SummaryCard";
import type { PaperProgressItemRead } from "../lib/types";

type ProgressFilterKey =
  | "all"
  | "unread"
  | "skimming"
  | "reading"
  | "read"
  | "high_priority"
  | "next_action"
  | "metadata_attention";

type PaperProgressPageProps = {
  items: PaperProgressItemRead[];
  scenarioLabel: string;
  onBackHome: () => void;
  onGoImport: () => void;
  onGoPulse: () => void;
};

function matchesFilter(item: PaperProgressItemRead, filter: ProgressFilterKey) {
  switch (filter) {
    case "unread":
    case "skimming":
    case "reading":
    case "read":
      return item.reading_status === filter;
    case "high_priority":
      return item.priority === "high" || item.priority === "urgent";
    case "next_action":
      return Boolean(item.next_action);
    case "metadata_attention":
      return item.warnings.length > 0;
    default:
      return true;
  }
}

function matchesKeyword(item: PaperProgressItemRead, keyword: string) {
  if (!keyword) {
    return true;
  }

  const normalizedKeyword = keyword.trim().toLowerCase();
  const searchable = [
    item.title,
    item.authors.join(" "),
    item.venue ?? "",
    item.tags.join(" "),
    item.keywords.join(" "),
    item.next_action ?? "",
  ]
    .join(" ")
    .toLowerCase();

  return searchable.includes(normalizedKeyword);
}

export function PaperProgressPage({
  items,
  scenarioLabel,
  onBackHome,
  onGoImport,
  onGoPulse,
}: PaperProgressPageProps) {
  const [filter, setFilter] = useState<ProgressFilterKey>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [mockUpdateMessage, setMockUpdateMessage] = useState<string | null>(null);
  const deferredSearchQuery = useDeferredValue(searchQuery);

  const selectedPaper = useMemo(
    () => items.find((item) => item.paper_id === selectedPaperId) ?? null,
    [items, selectedPaperId],
  );

  const filteredItems = useMemo(
    () =>
      items.filter(
        (item) => matchesFilter(item, filter) && matchesKeyword(item, deferredSearchQuery),
      ),
    [items, filter, deferredSearchQuery],
  );

  const filterOptions = useMemo(
    () => [
      { key: "all", label: "全部", count: items.length },
      { key: "unread", label: "待读", count: items.filter((item) => item.reading_status === "unread").length },
      {
        key: "skimming",
        label: "略读中",
        count: items.filter((item) => item.reading_status === "skimming").length,
      },
      {
        key: "reading",
        label: "精读中",
        count: items.filter((item) => item.reading_status === "reading").length,
      },
      { key: "read", label: "已读", count: items.filter((item) => item.reading_status === "read").length },
      {
        key: "high_priority",
        label: "高优先级",
        count: items.filter((item) => item.priority === "high" || item.priority === "urgent").length,
      },
      {
        key: "next_action",
        label: "有下一步动作",
        count: items.filter((item) => Boolean(item.next_action)).length,
      },
      {
        key: "metadata_attention",
        label: "待补全",
        count: items.filter((item) => item.warnings.length > 0).length,
      },
    ],
    [items],
  );

  const summary = useMemo(
    () => ({
      total: items.length,
      unread: items.filter((item) => item.reading_status === "unread").length,
      skimming: items.filter((item) => item.reading_status === "skimming").length,
      reading: items.filter((item) => item.reading_status === "reading").length,
      read: items.filter((item) => item.reading_status === "read").length,
      highPriority: items.filter((item) => item.priority === "high" || item.priority === "urgent").length,
      nextAction: items.filter((item) => Boolean(item.next_action)).length,
      metadataAttention: items.filter((item) => item.warnings.length > 0).length,
    }),
    [items],
  );

  const hasItems = items.length > 0;
  const hasMetadataWarnings = summary.metadataAttention > 0;

  function handleSelect(paperId: string) {
    setSelectedPaperId(paperId);
    setMockUpdateMessage(null);
  }

  function handleMockUpdate() {
    if (!selectedPaper) {
      return;
    }
    setMockUpdateMessage(
      `当前为本地预览，不会真实修改论文库。已模拟准备更新「${selectedPaper.title}」的进度。`,
    );
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">论文进度</p>
          <h1>围绕待读、略读、精读和下一步动作推进科研阅读</h1>
          <p className="hero-summary">
            这一页不是完整文献库，也不是管理后台。它只帮助你快速判断哪些论文该继续看、该补什么、下一步做什么。
          </p>
        </div>
        <div className="hero-actions">
          <button
            className="button-primary"
            onClick={handleMockUpdate}
            type="button"
            disabled={!selectedPaper}
            aria-describedby="progress-primary-action-note"
          >
            {selectedPaper ? "更新选中论文进度" : "请先选中一篇论文"}
          </button>
          <button className="button-secondary" onClick={onBackHome} type="button">
            返回今日 Pulse
          </button>
          <button className="button-tertiary" onClick={onGoImport} type="button">
            导入更多论文
          </button>
          <button className="button-tertiary" onClick={onGoPulse} type="button">
            查看 Pulse 详情
          </button>
        </div>
      </section>

      <StatusBanner tone="info" title={`当前模式：mock mode · ${scenarioLabel}`}>
        <p>当前页面只消费本地 curated progress JSON，用于验证筛选、卡片密度和中文文案。</p>
        <p id="progress-primary-action-note">
          当前为本地预览，不会真实修改论文库；主动作只验证选中与状态反馈，不调用真实 API。
        </p>
      </StatusBanner>

      {hasMetadataWarnings ? (
        <StatusBanner tone="warning" title="当前有论文建议先补全元数据">
          <p>共有 {summary.metadataAttention} 篇论文仍缺年份、来源或 DOI。warning 会被翻成“先补什么”的建议。</p>
          <p>建议优先处理待补全记录，再决定是否继续推进阅读或写入下一步动作。</p>
        </StatusBanner>
      ) : null}

      {mockUpdateMessage ? (
        <StatusBanner tone="info" title="已完成本地预览更新">
          <p>{mockUpdateMessage}</p>
        </StatusBanner>
      ) : null}

      {!hasItems ? (
        <section className="panel">
          <EmptyState
            eyebrow="当前为空"
            title="还没有可展示的论文进度"
            description="先导入论文，再回来判断哪些待读、哪些精读、哪些需要补全元数据。"
            actionLabel="导入论文"
            onAction={onGoImport}
            secondaryLabel="返回今日 Pulse"
            onSecondaryAction={onBackHome}
          />
        </section>
      ) : (
        <>
          <div className="summary-grid">
            <SummaryCard label="总论文数" count={summary.total} hint="已进入工作台的论文总数" />
            <SummaryCard label="待读" count={summary.unread} hint="刚导入或还没进入阅读的论文" />
            <SummaryCard label="略读中" count={summary.skimming} hint="适合先判断相关性的论文" />
            <SummaryCard label="精读中" count={summary.reading} hint="今天适合继续推进的论文" tone="success" />
            <SummaryCard label="已读" count={summary.read} hint="主要内容已读完的论文" />
            <SummaryCard
              label="高优先级"
              count={summary.highPriority}
              hint="需要优先处理的论文数量"
              tone="warning"
            />
            <SummaryCard
              label="下一步动作"
              count={summary.nextAction}
              hint="已经写明 next_action 的论文数量"
              tone="success"
            />
            <SummaryCard
              label="待补全"
              count={summary.metadataAttention}
              hint="建议先补全年份、来源或 DOI 的论文"
              tone="warning"
            />
          </div>

          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">筛选与搜索</p>
                <h3>先缩小到今天最值得处理的论文</h3>
              </div>
            </div>
            <ProgressFilterBar options={filterOptions} activeKey={filter} onChange={(key) => setFilter(key as ProgressFilterKey)} />
            <div className="search-panel">
              <label className="field-label" htmlFor="progress-search-input">
                按题名 / 作者 / 来源 / 关键词搜索
              </label>
              <input
                id="progress-search-input"
                className="field-input"
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="例如：元数据补全 / 周宁 / 科研协同学刊"
              />
              <p className="soft-copy">
                当前筛选：{filterOptions.find((option) => option.key === filter)?.label ?? "全部"}，共 {filteredItems.length} 篇。
              </p>
            </div>
          </section>

          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">论文列表</p>
                <h3>把今天最值得处理的论文放在前面</h3>
              </div>
            </div>
            {filteredItems.length > 0 ? (
              <div className="section-items">
                {filteredItems.map((item) => (
                  <ProgressPaperCard
                    key={item.paper_id}
                    item={item}
                    selected={item.paper_id === selectedPaperId}
                    onSelect={handleSelect}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                compact
                eyebrow="当前为空"
                title="当前筛选条件下没有命中论文"
                description={`当前没有符合“${filterOptions.find((option) => option.key === filter)?.label ?? "全部"}”和搜索词“${deferredSearchQuery || "空"}”的论文。建议先放宽筛选或清空搜索。`}
                actionLabel="查看全部论文"
                onAction={() => {
                  setFilter("all");
                  setSearchQuery("");
                }}
              />
            )}
          </section>
        </>
      )}
    </div>
  );
}
