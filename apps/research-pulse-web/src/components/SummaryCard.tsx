type SummaryCardProps = {
  label: string;
  count: number;
  hint: string;
};

export function SummaryCard({ label, count, hint }: SummaryCardProps) {
  return (
    <article className="summary-card">
      <p className="summary-card-label">{label}</p>
      <p className="summary-card-count">{count}</p>
      <p className="summary-card-hint">{hint}</p>
    </article>
  );
}
