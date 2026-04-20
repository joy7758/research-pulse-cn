import { EmptyState } from "./EmptyState";
import { Badge } from "./Badge";
import type { ImportPreviewRecord } from "../lib/types";

type ImportPreviewTableProps = {
  records: ImportPreviewRecord[];
  emptyText?: string;
};

function formatCell(record: ImportPreviewRecord, field: "year" | "venue" | "doi") {
  if (field === "year") {
    return record.year ?? "待补全";
  }

  if (field === "venue") {
    return record.venue ?? "待补全";
  }

  return record.doi ?? "待补全";
}

export function ImportPreviewTable({
  records,
  emptyText = "当前没有可展示的预览记录。",
}: ImportPreviewTableProps) {
  if (records.length === 0) {
    return (
      <EmptyState
        compact
        eyebrow="预览为空"
        title="当前没有待预览记录"
        description={emptyText}
      />
    );
  }

  return (
    <div className="table-shell">
      <table className="import-table">
        <caption className="visually-hidden">导入预览字段表</caption>
        <thead>
          <tr>
            <th>题名</th>
            <th>作者</th>
            <th>年份</th>
            <th>来源</th>
            <th>DOI</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.source_index}>
              <td>{record.title || "题名待补全"}</td>
              <td>{record.authors.join(" / ") || "作者待补全"}</td>
              <td>{formatCell(record, "year")}</td>
              <td>{formatCell(record, "venue")}</td>
              <td>{formatCell(record, "doi")}</td>
              <td>
                <div className="badge-row">
                  <Badge tone={record.can_commit ? "success" : "error"}>
                    {record.can_commit ? "可导入" : "不可导入"}
                  </Badge>
                  {record.warnings.length > 0 ? (
                    <Badge tone="warning">warning {record.warnings.length}</Badge>
                  ) : null}
                  {record.errors.length > 0 ? (
                    <Badge tone="error">error {record.errors.length}</Badge>
                  ) : null}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="import-card-list" aria-label="导入预览卡片">
        {records.map((record) => (
          <article key={`card-${record.source_index}`} className="import-card">
            <div className="import-card-header">
              <div>
                <p className="eyebrow">记录 {record.source_index}</p>
                <h4>{record.title || "题名待补全"}</h4>
              </div>
              <Badge tone={record.can_commit ? "success" : "error"}>
                {record.can_commit ? "可导入" : "不可导入"}
              </Badge>
            </div>
            <p className="soft-copy">{record.authors.join(" / ") || "作者待补全"}</p>
            <dl className="import-card-meta">
              <div>
                <dt>年份</dt>
                <dd>{formatCell(record, "year")}</dd>
              </div>
              <div>
                <dt>来源</dt>
                <dd>{formatCell(record, "venue")}</dd>
              </div>
              <div>
                <dt>DOI</dt>
                <dd>{formatCell(record, "doi")}</dd>
              </div>
            </dl>
            <div className="badge-row">
              {record.warnings.length > 0 ? (
                <Badge tone="warning">建议补全 {record.warnings.length} 项</Badge>
              ) : null}
              {record.errors.length > 0 ? (
                <Badge tone="error">需处理 {record.errors.length} 项</Badge>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
