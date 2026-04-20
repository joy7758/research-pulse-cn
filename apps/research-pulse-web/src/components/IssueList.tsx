import { Badge } from "./Badge";

export type IssueItem = {
  id: string;
  tone: "warning" | "error";
  title: string;
  detail: string;
  suggestion: string;
};

type IssueListProps = {
  issues: IssueItem[];
  emptyText: string;
};

export function IssueList({ issues, emptyText }: IssueListProps) {
  if (issues.length === 0) {
    return <p className="empty-inline">{emptyText}</p>;
  }

  return (
    <ul className="issue-list issue-list-detailed">
      {issues.map((issue) => (
        <li key={issue.id} className={`issue-card issue-card-${issue.tone}`}>
          <div className="issue-card-header">
            <Badge tone={issue.tone}>{issue.tone === "warning" ? "建议补全" : "当前不可导入"}</Badge>
            <strong>{issue.title}</strong>
          </div>
          <p>{issue.detail}</p>
          <p className="issue-suggestion">
            <strong>下一步：</strong>
            {issue.suggestion}
          </p>
        </li>
      ))}
    </ul>
  );
}
