type SummaryCardProps = {
  label: string;
  count: number;
  hint: string;
  tone?: "neutral" | "success" | "warning";
};

export function SummaryCard({ label, count, hint, tone = "neutral" }: SummaryCardProps) {
  return (
    <article className={`summary-card summary-card-${tone}`}>
      <p className="summary-card-label">{label}</p>
      <p className="summary-card-count">{count}</p>
      <p className="summary-card-hint">{hint}</p>
    </article>
  );
}
