import { PaperCard } from "./PaperCard";
import type { ResearchPulseSection } from "../lib/types";

type PulseSectionProps = {
  section: ResearchPulseSection;
  compact?: boolean;
};

export function PulseSection({ section, compact = false }: PulseSectionProps) {
  const visibleItems = compact ? section.items.slice(0, 2) : section.items;

  return (
    <section className="panel section-panel">
      <div className="section-panel-header">
        <div>
          <p className="eyebrow">{section.section_id}</p>
          <h3>{section.title}</h3>
        </div>
        <span className="section-count">{section.items.length} 项</span>
      </div>
      <p className="section-description">{section.description}</p>
      {visibleItems.length > 0 ? (
        <div className="section-items">
          {visibleItems.map((item) => (
            <PaperCard key={`${section.section_id}-${item.paper_id}`} item={item} />
          ))}
        </div>
      ) : (
        <p className="empty-inline">{section.empty_reason ?? "当前没有需要展示的内容。"}</p>
      )}
      {compact && section.items.length > visibleItems.length ? (
        <p className="section-truncation">
          这里先展示前 {visibleItems.length} 项，完整列表请进入 Pulse 详情页。
        </p>
      ) : null}
    </section>
  );
}
