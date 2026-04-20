import { Badge } from "./Badge";
import type { PaperProgressItemRead } from "../lib/types";
import {
  getPriorityLabel,
  getReadingStatusLabel,
  getResearchStageLabel,
} from "../lib/progressLabels";

type ProgressPaperCardProps = {
  item: PaperProgressItemRead;
  selected: boolean;
  onSelect: (paperId: string) => void;
};

function getPriorityTone(priority: PaperProgressItemRead["priority"]) {
  switch (priority) {
    case "urgent":
      return "urgent";
    case "high":
      return "high";
    case "normal":
      return "normal";
    default:
      return "low";
  }
}

export function ProgressPaperCard({
  item,
  selected,
  onSelect,
}: ProgressPaperCardProps) {
  return (
    <article className={`paper-card progress-paper-card ${selected ? "paper-card-selected" : ""}`}>
      <div className="paper-card-header">
        <div>
          <h4>{item.title}</h4>
          <p className="paper-meta">
            {item.authors.join(" / ") || "作者待补全"}
            {item.year ? ` · ${item.year}` : " · 年份待补全"}
            {item.venue ? ` · ${item.venue}` : " · 来源待补全"}
          </p>
        </div>
        <div className="progress-card-actions">
          <div className="badge-row">
            <Badge tone={getPriorityTone(item.priority)} ariaLabel={`优先级：${getPriorityLabel(item.priority)}`}>
              {getPriorityLabel(item.priority)}
            </Badge>
            <Badge tone="neutral" ariaLabel={`阅读状态：${getReadingStatusLabel(item.reading_status)}`}>
              {getReadingStatusLabel(item.reading_status)}
            </Badge>
            <Badge tone="neutral" ariaLabel={`研究阶段：${getResearchStageLabel(item.research_stage)}`}>
              {getResearchStageLabel(item.research_stage)}
            </Badge>
          </div>
          <button
            className={selected ? "button-secondary" : "button-tertiary"}
            onClick={() => onSelect(item.paper_id)}
            type="button"
            aria-pressed={selected}
          >
            {selected ? "已选中" : "选中这篇"}
          </button>
        </div>
      </div>

      <p className="paper-reason">
        <strong>当前判断：</strong>
        {item.user_note ?? item.research_note ?? "当前还没有补充额外说明。"}
      </p>

      <p className="paper-action">
        <strong>下一步动作：</strong>
        {item.next_action ?? "先判断是否需要写入 next_action，再决定是否继续推进。"}
      </p>

      <div className="progress-meta-grid">
        <div>
          <p className="eyebrow">来源格式</p>
          <p className="soft-copy">{item.source_format}</p>
        </div>
        <div>
          <p className="eyebrow">最近触达</p>
          <p className="soft-copy">{item.last_touch_at.slice(0, 10)}</p>
        </div>
      </div>

      {item.warnings.length > 0 ? (
        <div className="warning-list" aria-label="元数据待补全">
          {item.warnings.map((warning) => (
            <Badge key={warning} tone="warning" ariaLabel={`建议补全：${warning}`}>
              建议补全：{warning}
            </Badge>
          ))}
        </div>
      ) : null}

      <div className="paper-card-footer">
        <div className="badge-row">
          {item.tags.map((tag) => (
            <Badge key={tag} tone="primary" ariaLabel={`标签：${tag}`}>
              {tag}
            </Badge>
          ))}
          {item.keywords.map((keyword) => (
            <Badge key={keyword} tone="neutral" ariaLabel={`关键词：${keyword}`}>
              {keyword}
            </Badge>
          ))}
        </div>
        <span className="paper-next-action">{selected ? "已加入本地更新预览" : "可加入本地更新预览"}</span>
      </div>
    </article>
  );
}
