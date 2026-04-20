import { useEffect, useMemo, useState, type KeyboardEvent } from "react";

import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { IssueList, type IssueItem } from "../components/IssueList";
import { PayloadPreviewPanel } from "../components/PayloadPreviewPanel";
import { StatusBanner } from "../components/StatusBanner";
import { SummaryCard } from "../components/SummaryCard";
import { copyText } from "../lib/copyText";
import type { MiniProgramDetailRead, MiniProgramPreviewCollection, Priority } from "../lib/types";

type MiniProgramTabKey = keyof MiniProgramPreviewCollection;

type MiniProgramDetailPreviewPageProps = {
  previews: MiniProgramPreviewCollection;
  scenarioLabel: string;
  onBackPulse: () => void;
  onGoOfficialDraft: () => void;
  onGoDesktopDraft: () => void;
};

const miniTabs: Array<{ key: MiniProgramTabKey; label: string }> = [
  { key: "daily_pulse", label: "今日 Pulse" },
  { key: "paper", label: "单篇论文" },
  { key: "next_actions", label: "下一步动作" },
  { key: "metadata_attention", label: "待补全" },
  { key: "triage", label: "待筛选" },
];

function focusMiniTab(tabKey: MiniProgramTabKey) {
  window.requestAnimationFrame(() => {
    const tab = document.getElementById(`mini-tab-${tabKey}`);
    if (tab instanceof HTMLButtonElement) {
      tab.focus();
    }
  });
}

function getPriorityTone(priority: Priority | null) {
  switch (priority) {
    case "urgent":
      return "urgent";
    case "high":
      return "high";
    case "low":
      return "low";
    default:
      return "normal";
  }
}

function buildIssues(detail: MiniProgramDetailRead): IssueItem[] {
  return detail.warnings.map((warning, index) => ({
    id: `mini-warning-${detail.detail_type}-${index}`,
    tone: "warning" as const,
    title: `预览提醒 ${index + 1}`,
    detail: warning,
    suggestion: "当前只做 preview / share-safe 审阅，不要把 path、share card 或 payload 视为真实小程序能力。",
  }));
}

export function MiniProgramDetailPreviewPage({
  previews,
  scenarioLabel,
  onBackPulse,
  onGoOfficialDraft,
  onGoDesktopDraft,
}: MiniProgramDetailPreviewPageProps) {
  const [activeTab, setActiveTab] = useState<MiniProgramTabKey>("daily_pulse");
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const currentDetail = previews[activeTab];
  const issues = useMemo(() => buildIssues(currentDetail), [currentDetail]);
  const hasItems = currentDetail.total_items > 0;
  const hasCopyableContent = hasItems || currentDetail.cards.some((card) => card.items.length > 0);
  const hasActions = currentDetail.actions.length > 0;
  const detailPayload = useMemo(() => JSON.stringify(currentDetail, null, 2), [currentDetail]);
  const shareCardPayload = useMemo(
    () => JSON.stringify(currentDetail.share_card, null, 2),
    [currentDetail.share_card],
  );
  const activeTabId = `mini-tab-${activeTab}`;
  const activePanelId = `mini-panel-${activeTab}`;
  const primaryHelperText = hasCopyableContent
    ? "当前为本地预览，主动作只复制 detail payload，不会真实创建小程序页面、登录、订阅消息或支付。"
    : "当前没有可复制的 detail payload，请先回到 Pulse 详情确认今天的重点论文和预览内容。";

  useEffect(() => {
    setCopyFeedback(null);
  }, [activeTab, currentDetail.detail_id, scenarioLabel]);

  function handleTabKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    let nextIndex = index;

    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      nextIndex = (index + 1) % miniTabs.length;
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      nextIndex = (index - 1 + miniTabs.length) % miniTabs.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = miniTabs.length - 1;
    } else {
      return;
    }

    event.preventDefault();
    const nextKey = miniTabs[nextIndex].key;
    setActiveTab(nextKey);
    focusMiniTab(nextKey);
  }

  async function handleCopyDetailPayload() {
    try {
      await copyText(detailPayload);
      setCopyFeedback("已复制当前小程序 detail payload。当前为 preview / share-safe，不会触发真实微信能力。");
    } catch (error) {
      setCopyFeedback(
        error instanceof Error ? `复制失败：${error.message}` : "复制失败，请稍后重试。",
      );
    }
  }

  async function handleCopyPath() {
    try {
      await copyText(currentDetail.navigation.current_path);
      setCopyFeedback("已复制当前 path 占位。当前只是前端预览路径，不会触发真实微信 API。");
    } catch (error) {
      setCopyFeedback(
        error instanceof Error ? `复制失败：${error.message}` : "复制失败，请稍后重试。",
      );
    }
  }

  async function handleCopyShareCard() {
    try {
      await copyText(shareCardPayload);
      setCopyFeedback("已复制 share card 预览。当前保持 share_safe，不会生成真实小程序卡片。");
    } catch (error) {
      setCopyFeedback(
        error instanceof Error ? `复制失败：${error.message}` : "复制失败，请稍后重试。",
      );
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">小程序详情预览</p>
          <h1>{currentDetail.title}</h1>
          <p className="hero-summary">{currentDetail.summary}</p>
        </div>
        <div className="hero-action-stack">
          <button
            className="button-primary"
            type="button"
            onClick={() => void handleCopyDetailPayload()}
            disabled={!hasCopyableContent}
            aria-label={hasCopyableContent ? "复制当前小程序 detail payload" : "当前没有可复制的小程序详情内容"}
            aria-describedby="mini-preview-primary-helper"
          >
            {hasCopyableContent ? "复制当前 detail payload（mock）" : "当前没有可复制的详情内容"}
          </button>
          <button className="button-secondary" type="button" onClick={onBackPulse}>
            返回 Pulse 详情
          </button>
          <button
            className="button-tertiary"
            type="button"
            onClick={() => void handleCopyPath()}
            aria-label="复制当前小程序 path 占位"
          >
            复制当前 path
          </button>
          <button
            className="button-tertiary"
            type="button"
            onClick={() => void handleCopyShareCard()}
            aria-label="复制当前分享卡片预览"
          >
            复制 share card
          </button>
          <button className="button-tertiary" type="button" onClick={onGoOfficialDraft}>
            查看公众号草稿
          </button>
          <button className="button-tertiary" type="button" onClick={onGoDesktopDraft}>
            查看桌面通知草稿
          </button>
          <p className="action-helper-copy" id="mini-preview-primary-helper">
            {primaryHelperText}
          </p>
        </div>
      </section>

      <StatusBanner tone="warning" title={`当前仍是 preview / share-safe · ${scenarioLabel}`}>
        <p>
          小程序详情页只展示 <strong>preview</strong> 和 <strong>share_safe</strong> 语义，不触发真实微信小程序能力。
        </p>
        <p>当前 path、share card 和 visibility notes 都只是预览边界。</p>
      </StatusBanner>

      {copyFeedback ? (
        <StatusBanner tone={copyFeedback.startsWith("复制失败") ? "error" : "info"} title="复制状态">
          <p>{copyFeedback}</p>
        </StatusBanner>
      ) : null}

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">detail type</p>
            <h3>切换预览内容</h3>
          </div>
          <Badge tone="preview">{currentDetail.delivery_state}</Badge>
        </div>
        <div className="filter-bar" role="tablist" aria-label="小程序详情类型">
          {miniTabs.map((tab) => (
            <button
              key={tab.key}
              className={`filter-chip ${activeTab === tab.key ? "filter-chip-active" : ""}`}
              type="button"
              role="tab"
              id={`mini-tab-${tab.key}`}
              aria-selected={activeTab === tab.key}
              aria-controls={`mini-panel-${tab.key}`}
              tabIndex={activeTab === tab.key ? 0 : -1}
              aria-label={`${tab.label}，${previews[tab.key].total_items} 项`}
              onClick={() => setActiveTab(tab.key)}
              onKeyDown={(event) => handleTabKeyDown(event, miniTabs.findIndex((item) => item.key === tab.key))}
            >
              <span>{tab.label}</span>
              <strong>{previews[tab.key].total_items} 项</strong>
            </button>
          ))}
        </div>
      </section>

      <section
        className="channel-tab-panel"
        id={activePanelId}
        role="tabpanel"
        aria-labelledby={activeTabId}
      >
        <div className="summary-grid">
          <SummaryCard
            label="内容项"
            count={currentDetail.total_items}
            hint="当前 detail_type 下可展示的结构化条目数量"
            tone="success"
          />
          <SummaryCard
            label="卡片数"
            count={currentDetail.cards.length}
            hint="当前小程序详情预览会展示的卡片数量"
          />
          <SummaryCard
            label="动作入口"
            count={currentDetail.actions.length}
            hint="当前只展示 path 与 payload 占位"
            tone="warning"
          />
        </div>

        <section className="channel-double-grid">
          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">分享卡片</p>
                <h3>{currentDetail.share_card.title}</h3>
              </div>
              <Badge tone="preview">
                {currentDetail.share_card.share_safe ? "share_safe" : "preview"}
              </Badge>
            </div>
            <p className="section-description">{currentDetail.share_card.summary}</p>
            <div className="channel-definition-list">
              <div>
                <dt>path</dt>
                <dd>{currentDetail.share_card.path}</dd>
              </div>
              <div>
                <dt>裁剪字段</dt>
                <dd>{currentDetail.share_card.redacted_fields.join(" / ") || "当前没有裁剪说明"}</dd>
              </div>
            </div>
          </section>
          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">导航占位</p>
                <h3>path / back / related</h3>
              </div>
            </div>
            <div className="channel-definition-list">
              <div>
                <dt>current path</dt>
                <dd>{currentDetail.navigation.current_path}</dd>
              </div>
              <div>
                <dt>back path</dt>
                <dd>{currentDetail.navigation.back_path}</dd>
              </div>
              <div>
                <dt>related paths</dt>
                <dd>{currentDetail.navigation.related_paths.join(" / ") || "当前没有 related path"}</dd>
              </div>
            </div>
          </section>
        </section>

        <section className="channel-double-grid">
          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">页面动作</p>
                <h3>当前 detail_type 的 path 占位</h3>
              </div>
            </div>
            {hasActions ? (
              <ul className="channel-link-list">
                {currentDetail.actions.map((action) => (
                  <li key={action.action_id}>
                    <strong>{action.label}</strong>
                    <span>{action.path}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                compact
                title="当前没有额外的页面动作"
                description="这不影响 preview 审阅，当前 detail_type 只保留基础展示和 share-safe path。"
              />
            )}
          </section>
          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">可见性边界</p>
                <h3>share_safe / preview 说明</h3>
              </div>
              <Badge tone="preview">{currentDetail.delivery_state}</Badge>
            </div>
            {currentDetail.visibility_notes.length > 0 ? (
              <ul className="issue-list channel-note-list">
                {currentDetail.visibility_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : (
              <p className="empty-inline">当前没有额外的可见性说明。</p>
            )}
          </section>
        </section>

        {hasItems || currentDetail.cards.length > 0 ? (
          <div className="channel-list">
            {currentDetail.cards.map((card) => (
              <section key={card.card_id} className="panel channel-section-card">
                <div className="section-panel-header">
                  <div>
                    <p className="eyebrow">{card.card_type}</p>
                    <h3>{card.title}</h3>
                  </div>
                  <Badge tone="preview">{card.items.length} 项</Badge>
                </div>
                <p className="section-description">{card.subtitle ?? card.body}</p>
                {card.items.length > 0 ? (
                  <div className="channel-list">
                    {card.items.map((item) => (
                      <article key={item.item_id} className="channel-item-card">
                        <div className="channel-item-header">
                          <strong>{item.title}</strong>
                          <div className="badge-row">
                            <Badge tone={getPriorityTone(item.priority)}>{item.priority ?? "normal"}</Badge>
                            <Badge tone="neutral">{item.reading_status ?? "待判断"}</Badge>
                          </div>
                        </div>
                        <p className="channel-item-helper">
                          {item.authors.join(" / ") || "作者待补全"}
                          {item.year ? ` · ${item.year}` : " · 年份待补全"}
                          {item.venue ? ` · ${item.venue}` : " · 来源待补全"}
                        </p>
                        <p>{item.reason}</p>
                        <p className="channel-item-helper">
                          <strong>建议动作：</strong>
                          {item.suggested_action}
                        </p>
                        {item.metadata_warnings.length > 0 ? (
                          <div className="warning-list">
                            {item.metadata_warnings.map((warning) => (
                              <Badge key={warning} tone="warning">
                                建议补全：{warning}
                              </Badge>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    compact
                    title={`当前“${card.title}”没有可展示内容`}
                    description={card.empty_reason ?? "当前没有可展示的结构化条目。"}
                  />
                )}
              </section>
            ))}
          </div>
        ) : (
          <section className="panel">
            <EmptyState
              title="当前没有可展示的小程序详情预览"
              description="先回到 Pulse 详情生成草稿，再回来切换不同 detail_type。"
              actionLabel="返回 Pulse 详情"
              onAction={onBackPulse}
            />
          </section>
        )}

        {issues.length > 0 ? (
          <section className="panel">
            <div className="section-panel-header">
              <div>
                <p className="eyebrow">可见性说明</p>
                <h3>warning 要翻成边界说明</h3>
              </div>
            </div>
            <IssueList issues={issues} emptyText="当前没有额外 warning。" />
          </section>
        ) : null}

        <PayloadPreviewPanel
          title="当前 detail payload 预览"
          description="这里只展示小程序详情页 payload 预览，不会接入真实微信小程序。"
          code={detailPayload}
        />
      </section>
    </div>
  );
}
