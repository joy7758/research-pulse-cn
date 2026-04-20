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
  ariaLabel?: string;
};

const toneLabelMap: Record<BadgeTone, string> = {
  neutral: "信息",
  primary: "标签",
  success: "通过",
  warning: "建议补全",
  error: "需处理",
  draft: "草稿",
  preview: "预览",
  "not-sent": "未发送",
  low: "低优先级",
  normal: "普通优先级",
  high: "高优先级",
  urgent: "紧急优先级",
};

export function Badge({ tone, children, ariaLabel }: BadgeProps) {
  return (
    <span
      className={`badge badge-${tone}`}
      aria-label={ariaLabel ?? `${toneLabelMap[tone]}：${String(children)}`}
      title={`${toneLabelMap[tone]}：${String(children)}`}
    >
      {children}
    </span>
  );
}
