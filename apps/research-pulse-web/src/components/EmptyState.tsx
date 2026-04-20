type EmptyStateProps = {
  eyebrow?: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryLabel?: string;
  onSecondaryAction?: () => void;
  compact?: boolean;
};

export function EmptyState({
  eyebrow = "当前为空",
  title,
  description,
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondaryAction,
  compact = false,
}: EmptyStateProps) {
  return (
    <section className={`empty-state ${compact ? "empty-state-compact" : ""}`}>
      <div className="empty-state-copy">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        <p className="soft-copy">{description}</p>
      </div>
      {actionLabel || secondaryLabel ? (
        <div className="empty-state-actions">
          {actionLabel && onAction ? (
            <button className="button-primary" onClick={onAction} type="button">
              {actionLabel}
            </button>
          ) : null}
          {secondaryLabel && onSecondaryAction ? (
            <button className="button-secondary" onClick={onSecondaryAction} type="button">
              {secondaryLabel}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
