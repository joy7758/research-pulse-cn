import type { ReactNode } from "react";

type StatusBannerProps = {
  tone: "info" | "warning" | "error";
  title: string;
  children: ReactNode;
};

export function StatusBanner({ tone, title, children }: StatusBannerProps) {
  return (
    <section className={`status-banner status-banner-${tone}`}>
      <div>
        <p className="status-banner-label">{title}</p>
        <div className="status-banner-copy">{children}</div>
      </div>
    </section>
  );
}
