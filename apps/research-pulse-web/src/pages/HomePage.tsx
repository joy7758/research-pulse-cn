import { Badge } from "../components/Badge";
import { PulseSection } from "../components/PulseSection";
import { StatusBanner } from "../components/StatusBanner";
import { SummaryCard } from "../components/SummaryCard";
import type { ChannelStateHint, PaperProgressSummaryRead, ResearchPulseRead } from "../lib/types";

type HomePageProps = {
  pulse: ResearchPulseRead;
  summary: PaperProgressSummaryRead;
  channelStates: ChannelStateHint[];
  lastRefreshedAt: string;
  onRefresh: () => void;
  onGoImport: () => void;
  onGoPulse: () => void;
};

export function HomePage({
  pulse,
  summary,
  channelStates,
  lastRefreshedAt,
  onRefresh,
  onGoImport,
  onGoPulse,
}: HomePageProps) {
  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">今日 Research Pulse</p>
          <h1>{pulse.title}</h1>
          <p className="hero-summary">{pulse.summary}</p>
        </div>
        <div className="hero-actions">
          <button className="button-primary" onClick={onRefresh}>
            刷新今日 Pulse
          </button>
          <button className="button-secondary" onClick={onGoImport}>
            导入论文
          </button>
          <button className="button-tertiary" onClick={onGoPulse}>
            查看 Pulse 详情
          </button>
        </div>
      </section>

      <StatusBanner tone="info" title="当前模式：mock mode">
        <p>当前首页只消费本地 curated demo JSON，方便先验证首屏信息架构与中文文案。</p>
        <p>最近刷新：{lastRefreshedAt}。Research Pulse 保持 <strong>draft</strong> 语义。</p>
      </StatusBanner>

      <div className="summary-grid">
        <SummaryCard label="总论文数" count={summary.total_papers} hint="已导入且进入工作台的论文总数" />
        <SummaryCard label="阅读中" count={summary.reading_count} hint="今天适合继续推进的论文数量" />
        <SummaryCard
          label="高优先级"
          count={summary.high_priority_count + summary.urgent_count}
          hint="需要优先处理的论文数量"
        />
        <SummaryCard label="下一步动作" count={summary.with_next_action_count} hint="已写明 next_action 的论文数量" />
      </div>

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

      {pulse.sections.map((section) => (
        <PulseSection key={section.section_id} section={section} compact />
      ))}
    </div>
  );
}
