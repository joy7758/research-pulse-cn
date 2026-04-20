type PayloadPreviewPanelProps = {
  eyebrow?: string;
  title: string;
  description: string;
  code: string;
};

export function PayloadPreviewPanel({
  eyebrow = "payload 预览",
  title,
  description,
  code,
}: PayloadPreviewPanelProps) {
  return (
    <section className="panel payload-panel">
      <div className="section-panel-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
        </div>
      </div>
      <p className="section-description">{description}</p>
      <pre className="payload-preview" aria-label={title}>
        <code>{code}</code>
      </pre>
    </section>
  );
}
