import { Badge } from "./Badge";
import type { ResearchPulseItem } from "../lib/types";

type PaperCardProps = {
  item: ResearchPulseItem;
};

function getPriorityTone(priority: ResearchPulseItem["priority"]) {
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

export function PaperCard({ item }: PaperCardProps) {
  return (
    <article className="paper-card">
      <div className="paper-card-header">
        <div>
          <h4>{item.title}</h4>
          <p className="paper-meta">
            {item.authors.join(" / ") || "作者待补全"}
            {item.year ? ` · ${item.year}` : " · 年份待补全"}
            {item.venue ? ` · ${item.venue}` : " · 来源待补全"}
          </p>
        </div>
        <div className="badge-row">
          <Badge tone={getPriorityTone(item.priority)} ariaLabel={`优先级：${item.priority}`}>
            {item.priority}
          </Badge>
          <Badge tone="neutral" ariaLabel={`阅读状态：${item.reading_status}`}>
            {item.reading_status}
          </Badge>
          <Badge tone="neutral" ariaLabel={`研究阶段：${item.research_stage}`}>
            {item.research_stage}
          </Badge>
        </div>
      </div>
      <p className="paper-reason">{item.reason}</p>
      <p className="paper-action">
        <strong>建议下一步：</strong>
        {item.suggested_action}
      </p>
      <div className="paper-card-footer">
        {item.metadata_warnings.length > 0 ? (
          <div className="warning-list" aria-label="元数据提醒">
            {item.metadata_warnings.map((warning) => (
              <Badge key={warning} tone="warning" ariaLabel={`建议补全：${warning}`}>
                建议补全：{warning}
              </Badge>
            ))}
          </div>
        ) : (
          <div className="badge-row">
            {item.tags.length > 0 ? (
              item.tags.map((tag) => (
                <Badge key={tag} tone="primary" ariaLabel={`标签：${tag}`}>
                  {tag}
                </Badge>
              ))
            ) : (
              <Badge tone="neutral">暂无附加标签</Badge>
            )}
          </div>
        )}
        {item.next_action ? (
          <span className="paper-next-action">动作：{item.next_action}</span>
        ) : (
          <span className="paper-next-action">动作：先判断是否需要写入 next_action</span>
        )}
      </div>
    </article>
  );
}
