import type { ImportPreviewRecord } from "../lib/types";

type ImportPreviewTableProps = {
  records: ImportPreviewRecord[];
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

export function ImportPreviewTable({ records }: ImportPreviewTableProps) {
  return (
    <div className="table-shell">
      <table className="import-table">
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
              <td>{record.can_commit ? "可导入" : "不可导入"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
