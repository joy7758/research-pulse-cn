import { useEffect, useMemo, useState } from "react";

import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { IssueList, type IssueItem } from "../components/IssueList";
import { PayloadPreviewPanel } from "../components/PayloadPreviewPanel";
import { StatusBanner } from "../components/StatusBanner";
import { SummaryCard } from "../components/SummaryCard";
import { copyText } from "../lib/copyText";
import type { OfficialAccountDailySummaryRead } from "../lib/types";

type OfficialAccountDraftPageProps = {
  draft: OfficialAccountDailySummaryRead;
  scenarioLabel: string;
  onBackPulse: () => void;
  onGoDesktopDraft: () => void;
  onGoMiniPreview: () => void;
};

function buildMarkdown(draft: OfficialAccountDailySummaryRead) {
  const header = [
    `# ${draft.title}`,
    "",
    `> ${draft.headline}`,
    "",
    draft.summary,
    "",
  ];

  const sections = draft.sections.flatMap((section) => {
    if (section.items.length === 0) {
      return [`## ${section.title}`, "", section.empty_reason ?? "当前没有可展示内容。", ""];
    }

    return [
      `## ${section.title}`,
      "",
      ...section.items.map(
        (item) => `- **${item.title}**：${item.summary_line}${item.next_action ? `\n  - 下一步动作：${item.next_action}` : ""}`,
      ),
      "",
    ];
  });

  return header.concat(sections).join("\n").trim();
}

function buildIssues(draft: OfficialAccountDailySummaryRead): IssueItem[] {
  return [
    ...draft.warnings.map((warning, index) => ({
      id: `official-warning-${index}`,
      tone: "warning" as const,
      title: `草稿提醒 ${index + 1}`,
      detail: warning,
      suggestion: "先确认这条提醒是否只需要文案调整，还是需要继续推迟到真实平台接入阶段。",
    })),
    ...draft.binding_preview.notes.map((note, index) => ({
      id: `official-binding-${index}`,
      tone: "warning" as const,
      title: `绑定说明 ${index + 1}`,
      detail: note,
      suggestion: "当前只保留绑定预览，不要把它理解成已接入真实发送能力。",
    })),
  ];
}

export function OfficialAccountDraftPage({
  draft,
  scenarioLabel,
  onBackPulse,
  onGoDesktopDraft,
  onGoMiniPreview,
}: OfficialAccountDraftPageProps) {
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const hasItems = draft.sections.some((section) => section.items.length > 0);
  const hasHighlights = draft.publication_preview.digest_highlights.length > 0;
  const selectedBinding = draft.binding_preview.selected_binding;
  const templateFieldEntries = Object.entries(draft.template_payload_preview.logical_fields);
  const markdown = useMemo(() => buildMarkdown(draft), [draft]);
  const issues = useMemo(() => buildIssues(draft), [draft]);
  const primaryActionDisabled = !hasItems;
  const primaryHelperText = primaryActionDisabled
    ? "当前没有可复制的摘要内容，请先回到 Pulse 详情确认今天的重点论文。"
    : "当前为本地预览，主动作只复制 Markdown 草稿，不会真实发送公众号摘要。";

  useEffect(() => {
    setCopyFeedback(null);
  }, [draft.draft_id, scenarioLabel]);

  useEffect(() => {
    if (!copyFeedback) {
      return;
    }

    const timer = window.setTimeout(() => {
      setCopyFeedback(null);
    }, 2800);

    return () => {
      window.clearTimeout(timer);
    };
  }, [copyFeedback]);

  async function handleCopyMarkdown() {
    try {
      await copyText(markdown);
      setCopyFeedback("已复制公众号 Markdown 草稿。当前为 mock-only，不会真实发送。");
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
          <p className="eyebrow">公众号摘要草稿</p>
          <h1>{draft.title}</h1>
          <p className="hero-summary">{draft.summary}</p>
        </div>
        <div className="hero-action-stack">
          <button
            className="button-primary"
            type="button"
            onClick={() => void handleCopyMarkdown()}
            disabled={primaryActionDisabled}
            aria-label={primaryActionDisabled ? "当前没有可复制的公众号草稿内容" : "复制公众号 Markdown 草稿"}
            aria-describedby="official-draft-primary-helper"
          >
            {hasItems ? "复制 Markdown 草稿（mock）" : "当前没有可复制的摘要内容"}
          </button>
          <button className="button-secondary" type="button" onClick={onBackPulse}>
            返回 Pulse 详情
          </button>
          <button className="button-tertiary" type="button" onClick={onGoDesktopDraft}>
            查看桌面通知草稿
          </button>
          <button className="button-tertiary" type="button" onClick={onGoMiniPreview}>
            查看小程序详情预览
          </button>
          <p className="action-helper-copy" id="official-draft-primary-helper">
            {primaryHelperText}
          </p>
        </div>
      </section>

      <StatusBanner tone="warning" title={`当前仍是 draft / not_sent · ${scenarioLabel}`}>
        <p>
          这个页面只展示公众号摘要草稿。状态保持 <strong>draft / not_sent</strong>，不会出现“已发送成功”。
        </p>
        <p>当前不会触发 access_token、群发、素材上传或模板消息发送。</p>
      </StatusBanner>

      {copyFeedback ? (
        <StatusBanner tone={copyFeedback.startsWith("复制失败") ? "error" : "info"} title="复制状态">
          <p>{copyFeedback}</p>
        </StatusBanner>
      ) : null}

      <div className="summary-grid">
        <SummaryCard
          label="摘要重点"
          count={draft.highlight_count}
          hint="当前会进入公众号摘要的重点条目数量"
          tone="success"
        />
        <SummaryCard
          label="来源论文"
          count={draft.total_source_papers}
          hint="构成这份草稿的原始论文数量"
        />
        <SummaryCard
          label="绑定预览"
          count={draft.binding_preview.active_binding_count}
          hint="当前只展示绑定占位，不代表真实可发送"
          tone="warning"
        />
      </div>

      <section className="channel-double-grid">
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">绑定预览</p>
              <h3>公众号绑定仍是占位说明</h3>
            </div>
            <Badge tone="not-sent">{draft.binding_preview.active_binding_count} 个绑定</Badge>
          </div>
          {selectedBinding ? (
            <div className="channel-definition-list">
              <div>
                <dt>显示名称</dt>
                <dd>{selectedBinding.display_label ?? "绑定名称待补全"}</dd>
              </div>
              <div>
                <dt>绑定状态</dt>
                <dd>{selectedBinding.bind_state}</dd>
              </div>
              <div>
                <dt>openid 占位</dt>
                <dd>{selectedBinding.masked_openid}</dd>
              </div>
            </div>
          ) : (
            <EmptyState
              compact
              title="当前没有可展示的绑定预览"
              description="这不影响草稿审阅，本页仍然只保留 not_sent 边界。"
            />
          )}
          {draft.binding_preview.notes.length > 0 ? (
            <ul className="issue-list channel-note-list">
              {draft.binding_preview.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-inline">当前没有额外的绑定说明。</p>
          )}
        </section>

        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">上下文说明</p>
              <h3>这份草稿来自哪些上下文</h3>
            </div>
          </div>
          {draft.source_context_notes.length > 0 ? (
            <ul className="issue-list channel-note-list">
              {draft.source_context_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : (
            <p className="empty-inline">当前没有额外的上下文说明。</p>
          )}
        </section>
      </section>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">发布预览</p>
            <h3>{draft.publication_preview.digest_title}</h3>
          </div>
          <Badge tone="not-sent">not_sent</Badge>
        </div>
        <p className="section-description">{draft.publication_preview.digest_subtitle}</p>
        {hasHighlights ? (
          <div className="channel-list">
            {draft.publication_preview.digest_highlights.map((highlight) => (
              <article key={highlight.paper_id} className="channel-item-card">
                <div className="channel-item-header">
                  <strong>{highlight.title}</strong>
                  <Badge tone="primary">{highlight.section_title}</Badge>
                </div>
                <p>{highlight.summary}</p>
                <p className="channel-item-helper">
                  <strong>为什么是现在：</strong>
                  {highlight.why_now}
                </p>
                <p className="channel-item-helper">
                  <strong>建议动作：</strong>
                  {highlight.suggested_action}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            compact
            title="当前没有可展示的公众号摘要重点"
            description="先回到 Pulse 详情确认今天的重点论文，再回来复制公众号摘要草稿。"
            actionLabel="返回 Pulse 详情"
            onAction={onBackPulse}
          />
        )}
      </section>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">草稿结构</p>
            <h3>分 section 组织摘要内容</h3>
          </div>
        </div>
        <div className="channel-list">
          {draft.sections.map((section) => (
            <article key={section.section_id} className="channel-section-card">
              <div className="channel-item-header">
                <strong>{section.title}</strong>
                <Badge tone="draft">{section.items.length} 项</Badge>
              </div>
              <p className="section-description">{section.description}</p>
              {section.items.length > 0 ? (
                <ul className="channel-bullet-list">
                  {section.items.map((item) => (
                    <li key={`${section.section_id}-${item.paper_id}`}>
                      <strong>{item.title}</strong>
                      <span>{item.summary_line}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-inline">{section.empty_reason ?? "当前没有可展示内容。"}</p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="channel-double-grid">
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">模板字段</p>
              <h3>模板 payload 占位</h3>
            </div>
          </div>
          {templateFieldEntries.length > 0 ? (
            <div className="channel-definition-list">
              {templateFieldEntries.map(([label, key]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{key}</dd>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              compact
              title="当前没有可展示的模板字段"
              description="这说明模板映射仍停留在 mock-only 预览阶段，不会影响本页的 not_sent 边界。"
            />
          )}
        </section>
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">provider 边界</p>
              <h3>dry_run / preview only</h3>
            </div>
          </div>
          <div className="channel-note-stack">
            <p>provider mode：{draft.provider_preview.provider_mode}</p>
            <p>transport kind：{draft.provider_preview.transport_kind}</p>
            {draft.provider_preview.notes.length > 0 ? (
              <ul className="issue-list channel-note-list">
                {draft.provider_preview.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : (
              <p className="empty-inline">当前没有额外的 provider 边界说明。</p>
            )}
          </div>
        </section>
      </section>

      {issues.length > 0 ? (
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">提示与约束</p>
              <h3>先把 warning 翻成可理解建议</h3>
            </div>
          </div>
          <IssueList issues={issues} emptyText="当前没有额外 warning。" />
        </section>
      ) : null}

      <PayloadPreviewPanel
        eyebrow="Markdown 草稿"
        title="当前复制的就是这份 Markdown"
        description="保持 draft / not_sent 语义，不做真实公众号发送。"
        code={markdown}
      />

      <PayloadPreviewPanel
        eyebrow="payload 占位"
        title="模板 payload 预览"
        description="这里只展示 share-safe 的模板字段占位，不包含真实 access_token 或发送请求。"
        code={JSON.stringify(draft.template_payload_preview.payload_preview, null, 2)}
      />
    </div>
  );
}
