import type { ReactNode } from "react";

type BadgeTone =
  | "neutral"
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "draft"
  | "preview"
  | "not-sent"
  | "low"
  | "normal"
  | "high"
  | "urgent";

type BadgeProps = {
  tone: BadgeTone;
  children: ReactNode;
};

export function Badge({ tone, children }: BadgeProps) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
