import { Badge } from "../components/Badge";
import { PulseSection } from "../components/PulseSection";
import { StatusBanner } from "../components/StatusBanner";
import type { ChannelStateHint, ResearchPulseRead } from "../lib/types";

type PulseDetailPageProps = {
  pulse: ResearchPulseRead;
  channelStates: ChannelStateHint[];
  draftActionTriggered: boolean;
  onGenerateOfficialDraft: () => void;
  onBackHome: () => void;
};

export function PulseDetailPage({
  pulse,
  channelStates,
  draftActionTriggered,
  onGenerateOfficialDraft,
  onBackHome,
}: PulseDetailPageProps) {
  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Research Pulse 详情</p>
          <h1>{pulse.title}</h1>
          <p className="hero-summary">{pulse.summary}</p>
        </div>
        <div className="hero-actions">
          <button className="button-primary" onClick={onGenerateOfficialDraft}>
            生成公众号摘要草稿
          </button>
          <button className="button-tertiary" onClick={onBackHome}>
            返回首页
          </button>
        </div>
      </section>

      <StatusBanner tone="warning" title="当前仍是草稿边界">
        <p>Research Pulse 当前保持 <strong>draft</strong> 语义，不触发真实公众号、桌面或小程序投递。</p>
        <p>Front-end 只展示入口和状态，不在 Frontend-1 增加草稿详情页。</p>
      </StatusBanner>

      {draftActionTriggered ? (
        <StatusBanner tone="info" title="公众号摘要草稿入口已触发">
          <p>当前只在 mock mode 下确认入口可达，状态保持 <strong>draft / not_sent</strong>。</p>
          <p>真实公众号草稿页被明确延期到 Frontend-1 之后的阶段。</p>
        </StatusBanner>
      ) : null}

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

      {pulse.warnings.length > 0 ? (
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">提醒</p>
              <h3>先把 warning 翻成建议</h3>
            </div>
          </div>
          <ul className="issue-list">
            {pulse.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {pulse.sections.map((section) => (
        <PulseSection key={section.section_id} section={section} />
      ))}
    </div>
  );
}
