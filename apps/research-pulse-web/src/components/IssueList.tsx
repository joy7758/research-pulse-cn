type IssueListProps = {
  issues: string[];
  emptyText: string;
};

export function IssueList({ issues, emptyText }: IssueListProps) {
  if (issues.length === 0) {
    return <p className="empty-inline">{emptyText}</p>;
  }

  return (
    <ul className="issue-list">
      {issues.map((issue) => (
        <li key={issue}>{issue}</li>
      ))}
    </ul>
  );
}
