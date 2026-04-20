import type { ReactNode } from "react";

type StatusBannerProps = {
  tone: "info" | "warning" | "error";
  title: string;
  children: ReactNode;
  eyebrow?: string;
};

export function StatusBanner({
  tone,
  title,
  children,
  eyebrow = tone === "error" ? "当前需处理" : tone === "warning" ? "当前建议" : "状态说明",
}: StatusBannerProps) {
  return (
    <section
      className={`status-banner status-banner-${tone}`}
      role={tone === "error" ? "alert" : "status"}
      aria-live={tone === "error" ? "assertive" : "polite"}
    >
      <div>
        <p className="status-banner-label">{eyebrow}</p>
        <h3 className="status-banner-title">{title}</h3>
        <div className="status-banner-copy">{children}</div>
      </div>
    </section>
  );
}
