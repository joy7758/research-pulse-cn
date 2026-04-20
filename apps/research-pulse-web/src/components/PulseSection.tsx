import { EmptyState } from "./EmptyState";
import { PaperCard } from "./PaperCard";
import type { ResearchPulseSection } from "../lib/types";

type PulseSectionProps = {
  section: ResearchPulseSection;
  compact?: boolean;
};

export function PulseSection({ section, compact = false }: PulseSectionProps) {
  const visibleItems = compact ? section.items.slice(0, 2) : section.items;
  const sectionLabelId = `section-title-${section.section_id}`;

  return (
    <section className="panel section-panel" aria-labelledby={sectionLabelId}>
      <div className="section-panel-header">
        <div>
          <p className="eyebrow">{section.section_id}</p>
          <h3 id={sectionLabelId}>{section.title}</h3>
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
        <EmptyState
          compact
          eyebrow="当前为空"
          title={`暂时没有“${section.title}”内容`}
          description={section.empty_reason ?? "当前没有需要展示的内容。"}
        />
      )}
      {compact && section.items.length > visibleItems.length ? (
        <p className="section-truncation">
          这里先展示前 {visibleItems.length} 项，完整列表请进入 Pulse 详情页。
        </p>
      ) : null}
    </section>
  );
}
