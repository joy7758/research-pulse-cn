import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { IssueList, type IssueItem } from "../components/IssueList";
import { PulseSection } from "../components/PulseSection";
import { StatusBanner } from "../components/StatusBanner";
import type { ChannelStateHint, ResearchPulseRead } from "../lib/types";

type PulseDetailPageProps = {
  pulse: ResearchPulseRead;
  channelStates: ChannelStateHint[];
  scenarioLabel: string;
  onGoOfficialDraft: () => void;
  onGoDesktopDraft: () => void;
  onGoMiniPreview: () => void;
  onBackHome: () => void;
};

function buildWarningIssues(pulse: ResearchPulseRead): IssueItem[] {
  return pulse.warnings.map((warning, index) => ({
    id: `pulse-warning-${index}`,
    tone: "warning" as const,
    title: `提醒 ${index + 1}`,
    detail: warning,
    suggestion: "先确认这条提醒是否需要补元数据或调整今日动作，再决定是否继续生成渠道草稿。",
  }));
}

export function PulseDetailPage({
  pulse,
  channelStates,
  scenarioLabel,
  onGoOfficialDraft,
  onGoDesktopDraft,
  onGoMiniPreview,
  onBackHome,
}: PulseDetailPageProps) {
  const hasVisibleSections = pulse.sections.some((section) => section.items.length > 0);
  const warningIssues = buildWarningIssues(pulse);

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Research Pulse 详情</p>
          <h1>{pulse.title}</h1>
          <p className="hero-summary">{pulse.summary}</p>
        </div>
        <div className="hero-actions">
          <button
            className="button-primary"
            onClick={onGoOfficialDraft}
            type="button"
            disabled={!hasVisibleSections}
          >
            {hasVisibleSections ? "查看公众号摘要草稿（mock）" : "当前没有可生成的草稿内容"}
          </button>
          <button className="button-secondary" onClick={onGoDesktopDraft} type="button" disabled={!hasVisibleSections}>
            查看桌面通知草稿
          </button>
          <button className="button-tertiary" onClick={onGoMiniPreview} type="button" disabled={!hasVisibleSections}>
            查看小程序详情预览
          </button>
          <button className="button-tertiary" onClick={onBackHome} type="button">
            返回首页
          </button>
        </div>
      </section>

      <StatusBanner tone="warning" title={`当前仍是草稿边界 · ${scenarioLabel}`}>
        <p>Research Pulse 当前保持 <strong>draft</strong> 语义，不触发真实公众号、桌面或小程序投递。</p>
        <p>当前前端新增的渠道页只做草稿、预览和 payload 展示，不做真实发送、推送或小程序交互。</p>
      </StatusBanner>

      <StatusBanner tone="info" title="当前渠道状态：draft / preview / not_sent">
        <p>本页会明确显示草稿、预览和未发送，不会出现“已发送成功”或“已推送成功”。</p>
        <p>如果你现在点击渠道入口，只会进入 mock-only 草稿页，不会产生真实外部调用。</p>
      </StatusBanner>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">状态标识</p>
            <h3>draft / preview / not_sent</h3>
          </div>
        </div>
        <div className="channel-state-grid">
          {channelStates.map((state) => (
            <article key={state.id} className="channel-state-card">
              <div className="channel-state-header">
                <strong>{state.label}</strong>
                <Badge
                  tone={
                    state.state === "draft"
                      ? "draft"
                      : state.state === "preview"
                        ? "preview"
                        : "not-sent"
                  }
                >
                  {state.state}
                </Badge>
              </div>
              <p>{state.message}</p>
            </article>
          ))}
        </div>
      </section>

      {pulse.source_context_notes.length > 0 ? (
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">来源说明</p>
              <h3>当前 Pulse 依赖哪些上下文</h3>
            </div>
          </div>
          <ul className="issue-list">
            {pulse.source_context_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {warningIssues.length > 0 ? (
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">提醒</p>
              <h3>先把 warning 翻成建议</h3>
            </div>
          </div>
          <IssueList issues={warningIssues} emptyText="当前没有需要额外解释的 warning。" />
        </section>
      ) : null}

      {!hasVisibleSections ? (
        <section className="panel">
          <EmptyState
            eyebrow="当前为空"
            title="当前还没有可展开的 Pulse 内容"
            description="这通常说明当前 mock 场景专门用于验证空 section、disabled 主动作和返回首页的恢复路径。"
            actionLabel="返回首页"
            onAction={onBackHome}
          />
        </section>
      ) : null}

      {pulse.sections.map((section) => (
        <PulseSection key={section.section_id} section={section} />
      ))}
    </div>
  );
}
