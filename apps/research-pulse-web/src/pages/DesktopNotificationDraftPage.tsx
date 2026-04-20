import { useMemo, useState } from "react";

import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { IssueList, type IssueItem } from "../components/IssueList";
import { PayloadPreviewPanel } from "../components/PayloadPreviewPanel";
import { StatusBanner } from "../components/StatusBanner";
import { SummaryCard } from "../components/SummaryCard";
import { copyText } from "../lib/copyText";
import type { DesktopNotificationRead, Priority } from "../lib/types";

type DesktopNotificationDraftPageProps = {
  draft: DesktopNotificationRead;
  scenarioLabel: string;
  onBackPulse: () => void;
  onGoOfficialDraft: () => void;
  onGoMiniPreview: () => void;
};

function getPriorityTone(priority: Priority) {
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

function buildIssues(draft: DesktopNotificationRead): IssueItem[] {
  return draft.warnings.map((warning, index) => ({
    id: `desktop-warning-${index}`,
    tone: "warning" as const,
    title: `通知边界 ${index + 1}`,
    detail: warning,
    suggestion: "当前只保留 payload 预览和 deep link 占位，不要把它理解成真实系统通知。",
  }));
}

export function DesktopNotificationDraftPage({
  draft,
  scenarioLabel,
  onBackPulse,
  onGoOfficialDraft,
  onGoMiniPreview,
}: DesktopNotificationDraftPageProps) {
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const hasItems = draft.items.length > 0;
  const issues = useMemo(() => buildIssues(draft), [draft]);
  const payloadCode = useMemo(() => JSON.stringify(draft.payload_preview, null, 2), [draft]);

  async function handleCopyPayload() {
    try {
      await copyText(payloadCode);
      setCopyFeedback("已复制桌面通知 payload 草稿。当前为 mock-only，不会真实推送。");
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
          <p className="eyebrow">桌面通知草稿</p>
          <h1>{draft.title}</h1>
          <p className="hero-summary">{draft.body}</p>
        </div>
        <div className="hero-action-stack">
          <button
            className="button-primary"
            type="button"
            onClick={() => void handleCopyPayload()}
            disabled={!hasItems}
          >
            {hasItems ? "复制通知 payload（mock）" : "当前没有可复制的通知内容"}
          </button>
          <button className="button-secondary" type="button" onClick={onBackPulse}>
            返回 Pulse 详情
          </button>
          <button className="button-tertiary" type="button" onClick={onGoOfficialDraft}>
            查看公众号草稿
          </button>
          <button className="button-tertiary" type="button" onClick={onGoMiniPreview}>
            查看小程序详情预览
          </button>
          <p className="action-helper-copy">
            当前为本地预览，主动作只复制通知 payload，不会调用系统通知或真实推送服务。
          </p>
        </div>
      </section>

      <StatusBanner tone="warning" title={`当前仍是 draft / not_sent · ${scenarioLabel}`}>
        <p>
          桌面通知页面只展示 <strong>draft / not_sent</strong>，不会触发系统通知，也不会出现“已推送成功”。
        </p>
        <p>deep link、badge count 和 actions 都只是前端占位信息。</p>
      </StatusBanner>

      {copyFeedback ? (
        <StatusBanner tone={copyFeedback.startsWith("复制失败") ? "error" : "info"} title="复制状态">
          <p>{copyFeedback}</p>
        </StatusBanner>
      ) : null}

      <div className="summary-grid">
        <SummaryCard
          label="提醒条目"
          count={draft.total_items}
          hint="当前会进入桌面提醒草稿的条目数量"
          tone="success"
        />
        <SummaryCard
          label="badge 数"
          count={draft.badge_count}
          hint="当前只是通知草稿里的 badge 占位"
        />
        <SummaryCard
          label="动作入口"
          count={draft.actions.length}
          hint="当前只展示 deep link 和动作 payload 占位"
          tone="warning"
        />
      </div>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">通知条目</p>
            <h3>优先提醒什么</h3>
          </div>
          <Badge tone="draft">{draft.delivery_state}</Badge>
        </div>
        {hasItems ? (
          <div className="channel-list">
            {draft.items.map((item) => (
              <article key={item.paper_id} className="channel-item-card">
                <div className="channel-item-header">
                  <strong>{item.title}</strong>
                  <div className="badge-row">
                    <Badge tone={getPriorityTone(item.priority)}>{item.priority}</Badge>
                    <Badge tone="neutral">{item.reading_status}</Badge>
                  </div>
                </div>
                <p>{item.line}</p>
                <p className="channel-item-helper">
                  <strong>原因：</strong>
                  {item.reason}
                </p>
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
            title="当前没有可展示的桌面提醒草稿"
            description="先生成今日 Pulse 或导入更多论文，再回来查看桌面通知预览。"
            actionLabel="返回 Pulse 详情"
            onAction={onBackPulse}
          />
        )}
      </section>

      <section className="channel-double-grid">
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">通知动作</p>
              <h3>deep link 和动作 payload</h3>
            </div>
          </div>
          {draft.actions.length > 0 ? (
            <ul className="channel-link-list">
              {draft.actions.map((action) => (
                <li key={action.action_id}>
                  <strong>{action.label}</strong>
                  <span>{action.deep_link}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-inline">当前没有可展示的通知动作。</p>
          )}
        </section>
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">交付说明</p>
              <h3>delivery notes</h3>
            </div>
          </div>
          <ul className="issue-list">
            {draft.delivery_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      </section>

      {issues.length > 0 ? (
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">提醒</p>
              <h3>warning 要翻成建议</h3>
            </div>
          </div>
          <IssueList issues={issues} emptyText="当前没有额外 warning。" />
        </section>
      ) : null}

      <PayloadPreviewPanel
        title="桌面通知 payload 预览"
        description="这里只展示本地 payload 草稿，不触发系统通知或推送服务。"
        code={payloadCode}
      />
    </div>
  );
}
