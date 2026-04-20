import { Badge } from "../components/Badge";
import { ImportPreviewTable } from "../components/ImportPreviewTable";
import { IssueList } from "../components/IssueList";
import { StatusBanner } from "../components/StatusBanner";
import type { ImportCommitRead, ImportPreviewRead } from "../lib/types";

type ImportPageProps = {
  preview: ImportPreviewRead;
  commit: ImportCommitRead;
  showIssuesOnly: boolean;
  committed: boolean;
  onConfirmImport: () => void;
  onToggleIssues: () => void;
  onBackHome: () => void;
};

function collectIssues(preview: ImportPreviewRead) {
  return preview.records.flatMap((record) =>
    [...record.warnings, ...record.errors].map((message) => `记录 ${record.source_index}：${message}`),
  );
}

export function ImportPage({
  preview,
  commit,
  showIssuesOnly,
  committed,
  onConfirmImport,
  onToggleIssues,
  onBackHome,
}: ImportPageProps) {
  const issues = collectIssues(preview);
  const visibleRecords = showIssuesOnly
    ? preview.records.filter((record) => record.warnings.length > 0 || record.errors.length > 0)
    : preview.records;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">导入 / 导入预览</p>
          <h1>先看清结果，再确认导入</h1>
          <p className="hero-summary">
            Frontend-1 暂不做真实文件上传复杂工程，这一页先用 mock 数据演示拖入、粘贴、预览和确认的最短路径。
          </p>
        </div>
        <div className="hero-actions">
          <button className="button-primary" onClick={onConfirmImport} disabled={committed}>
            {committed ? "已确认导入" : "确认导入可导入记录"}
          </button>
          <button className="button-secondary" onClick={onToggleIssues}>
            {showIssuesOnly ? "查看全部记录" : "只看问题记录"}
          </button>
          <button className="button-tertiary" onClick={onBackHome}>
            返回首页
          </button>
        </div>
      </section>

      <StatusBanner tone="info" title="导入入口：静态 mock">
        <p>支持格式提示：CSV / TSV / CSL JSON / BibTeX / RIS / PDF 文件夹占位。</p>
        <p>当前页面不上传真实文件，只用 Demo-1 的导入预览结果说明用户会看到什么。</p>
      </StatusBanner>

      <div className="import-entry-grid">
        <section className="panel input-panel">
          <p className="eyebrow">拖入区域</p>
          <h3>把文件拖到这里</h3>
          <p className="soft-copy">
            先支持 mock 演示：前端只展示拖入区域，不在 Frontend-1 实现复杂文件上传工程。
          </p>
        </section>
        <section className="panel input-panel">
          <p className="eyebrow">粘贴区域</p>
          <h3>或直接粘贴题录内容</h3>
          <textarea
            className="paste-box"
            readOnly
            value={"题名,作者,年份,来源\na,b,c,d\n... 当前只展示 mock 粘贴入口。"}
          />
        </section>
      </div>

      <div className="summary-grid">
        <SummaryPreviewCard label="可导入" count={preview.valid_records_count} tone="success" />
        <SummaryPreviewCard label="warning" count={preview.warning_records_count} tone="warning" />
        <SummaryPreviewCard label="error" count={preview.error_records_count} tone="error" />
        <SummaryPreviewCard label="总记录" count={preview.total_records} tone="neutral" />
      </div>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">字段预览</p>
            <h3>导入结果一眼看懂</h3>
          </div>
          <Badge tone="primary">{preview.source_format}</Badge>
        </div>
        <ImportPreviewTable records={visibleRecords} />
      </section>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">问题记录</p>
            <h3>把错误翻成下一步建议</h3>
          </div>
        </div>
        <IssueList issues={issues} emptyText="当前没有需要额外处理的问题记录。" />
      </section>

      {committed ? (
        <section className="panel">
          <div className="section-panel-header">
            <div>
              <p className="eyebrow">导入完成</p>
              <h3>已给出下一步建议</h3>
            </div>
          </div>
          <div className="summary-grid">
            <SummaryPreviewCard label="已导入" count={commit.committed_count} tone="success" />
            <SummaryPreviewCard label="跳过" count={commit.skipped_count} tone="warning" />
            <SummaryPreviewCard label="失败" count={commit.failed_count} tone="error" />
          </div>
          <ul className="issue-list">
            {commit.record_results.map((result) => (
              <li key={`${result.source_index}-${result.status}`}>
                记录 {result.source_index}：{result.reason}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function SummaryPreviewCard({
  label,
  count,
  tone,
}: {
  label: string;
  count: number;
  tone: "success" | "warning" | "error" | "neutral";
}) {
  return (
    <article className={`summary-card summary-card-${tone}`}>
      <p className="summary-card-label">{label}</p>
      <p className="summary-card-count">{count}</p>
    </article>
  );
}
