import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { PulseSection } from "../components/PulseSection";
import { StatusBanner } from "../components/StatusBanner";
import { SummaryCard } from "../components/SummaryCard";
import type { ChannelStateHint, PaperProgressSummaryRead, ResearchPulseRead } from "../lib/types";

type HomePageProps = {
  pulse: ResearchPulseRead;
  summary: PaperProgressSummaryRead;
  channelStates: ChannelStateHint[];
  lastRefreshedAt: string;
  isRefreshing: boolean;
  scenarioLabel: string;
  onRefresh: () => void;
  onGoImport: () => void;
  onGoPulse: () => void;
};

export function HomePage({
  pulse,
  summary,
  channelStates,
  lastRefreshedAt,
  isRefreshing,
  scenarioLabel,
  onRefresh,
  onGoImport,
  onGoPulse,
}: HomePageProps) {
  const hasVisibleSections = pulse.sections.some((section) => section.items.length > 0);
  const isEmpty = summary.total_papers === 0 || !hasVisibleSections;
  const metadataAttentionCount = pulse.sections
    .filter((section) => section.section_id === "metadata_attention")
    .reduce((total, section) => total + section.items.length, 0);
  const shouldShowWarning = pulse.warnings.length > 0 || metadataAttentionCount > 0;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">今日 Research Pulse</p>
          <h1>{pulse.title}</h1>
          <p className="hero-summary">{pulse.summary}</p>
        </div>
        <div className="hero-actions">
          <button className="button-primary" onClick={isEmpty ? onGoImport : onRefresh} type="button">
            {isRefreshing ? "正在刷新今日 Pulse..." : isEmpty ? "导入论文" : "刷新今日 Pulse"}
          </button>
          <button className="button-secondary" onClick={isEmpty ? onRefresh : onGoImport} type="button">
            {isEmpty ? "重试读取 mock 数据" : "导入论文"}
          </button>
          <button className="button-tertiary" onClick={onGoPulse} type="button" disabled={isEmpty}>
            查看 Pulse 详情
          </button>
        </div>
      </section>

      <StatusBanner tone="info" title={`当前模式：mock mode · ${scenarioLabel}`}>
        <p>当前首页只消费本地 curated demo JSON，方便先验证首屏信息架构、窄屏布局和中文文案。</p>
        <p>
          最近刷新：{lastRefreshedAt}。Research Pulse 保持 <strong>draft</strong>，渠道仍然是
          <strong>preview / not_sent</strong>。
        </p>
      </StatusBanner>

      {shouldShowWarning && !isEmpty ? (
        <StatusBanner tone="warning" title="今天有记录建议先补全">
          <p>当前共有 {metadataAttentionCount} 条元数据待补全记录，warning 会先被翻译成用户可执行建议。</p>
          <p>建议优先补全年份、来源和 DOI，再决定是否纳入今天的重点推进列表。</p>
        </StatusBanner>
      ) : null}

      {isEmpty ? (
        <section className="panel">
          <EmptyState
            eyebrow="当前为空"
            title="今天还没有可进入 Pulse 的论文"
            description="先导入 3 到 5 篇论文，再回来查看今天该看什么、该补什么、下一步该做什么。"
            actionLabel="导入论文"
            onAction={onGoImport}
            secondaryLabel="重试读取 mock 数据"
            onSecondaryAction={onRefresh}
          />
        </section>
      ) : (
        <div className="summary-grid">
          <SummaryCard
            label="总论文数"
            count={summary.total_papers}
            hint="已导入且进入工作台的论文总数"
          />
          <SummaryCard
            label="阅读中"
            count={summary.reading_count}
            hint="今天适合继续推进的论文数量"
            tone="success"
          />
          <SummaryCard
            label="高优先级"
            count={summary.high_priority_count + summary.urgent_count}
            hint="需要优先处理的论文数量"
            tone="warning"
          />
          <SummaryCard
            label="下一步动作"
            count={summary.with_next_action_count}
            hint="已写明 next_action 的论文数量"
            tone="success"
          />
        </div>
      )}

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">状态边界</p>
            <h3>草稿 / 预览 / 未发送</h3>
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

      {!isEmpty ? pulse.sections.map((section) => <PulseSection key={section.section_id} section={section} compact />) : null}
    </div>
  );
}
