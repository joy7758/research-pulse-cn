import type { SubscriptionSettingsValidationIssueRead } from "../lib/types";

type FieldIssueListProps = {
  issues: SubscriptionSettingsValidationIssueRead[];
};

export function FieldIssueList({ issues }: FieldIssueListProps) {
  if (issues.length === 0) {
    return null;
  }

  return (
    <ul className="field-issue-list">
      {issues.map((issue) => (
        <li key={`${issue.field_id}:${issue.code}:${issue.message}`}>{issue.message}</li>
      ))}
    </ul>
  );
}
