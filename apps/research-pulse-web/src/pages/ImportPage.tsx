import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { ImportPreviewTable } from "../components/ImportPreviewTable";
import { IssueList, type IssueItem } from "../components/IssueList";
import { StatusBanner } from "../components/StatusBanner";
import type { ImportCommitRead, ImportPreviewRead } from "../lib/types";

type ImportPageProps = {
  preview: ImportPreviewRead;
  commit: ImportCommitRead;
  showIssuesOnly: boolean;
  committed: boolean;
  scenarioLabel: string;
  onConfirmImport: () => void;
  onToggleIssues: () => void;
  onBackHome: () => void;
};

function buildIssueSuggestion(message: string, isError: boolean) {
  if (message.includes("题名")) {
    return "先补全题名，再重新生成导入预览。";
  }

  if (message.includes("作者")) {
    return "先补全作者信息，再重新确认是否导入。";
  }

  if (message.includes("年份")) {
    return "先补全年份，避免后续筛选和排序受限。";
  }

  if (message.includes("DOI")) {
    return "建议补齐 DOI，后续去重和引用追踪会更稳。";
  }

  if (message.includes("来源") || message.includes("期刊") || message.includes("会议")) {
    return "先补齐来源信息，再决定是否提交这条记录。";
  }

  return isError ? "先修复这条记录，再重新生成预览。" : "当前仍可导入，但建议先补全这条信息。";
}

function collectIssues(preview: ImportPreviewRead): IssueItem[] {
  return preview.records.flatMap((record) => [
    ...record.warnings.map((message, index) => ({
      id: `warning-${record.source_index}-${index}`,
      tone: "warning" as const,
      title: `记录 ${record.source_index}：可导入，但建议补全`,
      detail: message,
      suggestion: buildIssueSuggestion(message, false),
    })),
    ...record.errors.map((message, index) => ({
      id: `error-${record.source_index}-${index}`,
      tone: "error" as const,
      title: `记录 ${record.source_index}：当前不可导入`,
      detail: message,
      suggestion: buildIssueSuggestion(message, true),
    })),
  ]);
}

export function ImportPage({
  preview,
  commit,
  showIssuesOnly,
  committed,
  scenarioLabel,
  onConfirmImport,
  onToggleIssues,
  onBackHome,
}: ImportPageProps) {
  const issues = collectIssues(preview);
  const visibleRecords = showIssuesOnly
    ? preview.records.filter((record) => record.warnings.length > 0 || record.errors.length > 0)
    : preview.records;
  const hasImportableRecords = preview.records.some((record) => record.can_commit && record.selected);
  const isEmpty = preview.total_records === 0;
  const hasWarnings = preview.warning_records_count > 0;
  const hasErrors = preview.error_records_count > 0;

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
          <button
            className="button-primary"
            onClick={onConfirmImport}
            type="button"
            disabled={committed || !hasImportableRecords}
          >
            {committed ? "已确认导入" : hasImportableRecords ? "确认导入可导入记录" : "当前没有可导入记录"}
          </button>
          <button className="button-secondary" onClick={onToggleIssues} type="button">
            {showIssuesOnly ? "查看全部记录" : "只看问题记录"}
          </button>
          <button className="button-tertiary" onClick={onBackHome} type="button">
            返回首页
          </button>
        </div>
      </section>

      <StatusBanner tone="info" title={`导入入口：静态 mock · ${scenarioLabel}`}>
        <p>支持格式提示：CSV / TSV / CSL JSON / BibTeX / RIS / PDF 文件夹占位。</p>
        <p>当前页面不上传真实文件，只用 Demo-1 的导入预览结果说明用户会看到什么。</p>
      </StatusBanner>

      {isEmpty ? (
        <StatusBanner tone="warning" title="当前没有待预览记录">
          <p>这不是系统故障，而是当前 mock 场景专门用来验证空状态文案和下一步引导。</p>
          <p>建议返回首页，或切回默认工作流场景继续演示导入预览。</p>
        </StatusBanner>
      ) : hasErrors ? (
        <StatusBanner tone="error" title="当前存在不可导入记录">
          <p>当前有 {preview.error_records_count} 条记录不可导入，主按钮会保持 disabled，避免误提交。</p>
          <p>建议先查看问题记录，把 error 翻成补全动作，再重新生成预览。</p>
        </StatusBanner>
      ) : hasWarnings ? (
        <StatusBanner tone="warning" title="当前存在 warning，但仍可导入">
          <p>共有 {preview.warning_records_count} 条记录建议补全。warning 会被翻成“先补什么”的中文建议。</p>
          <p>如果只是缺少年份、DOI 或来源，可以先导入，再在后续流程里补全。</p>
        </StatusBanner>
      ) : null}

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
            aria-label="mock 粘贴区域"
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
        <ImportPreviewTable
          records={visibleRecords}
          emptyText={
            showIssuesOnly
              ? "当前没有需要额外处理的问题记录。"
              : "当前 mock 场景没有待预览记录，建议切回默认工作流场景。"
          }
        />
      </section>

      <section className="panel">
        <div className="section-panel-header">
          <div>
            <p className="eyebrow">问题记录</p>
            <h3>把 warning 和 error 翻成下一步建议</h3>
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
          {commit.record_results.length > 0 ? (
            <ul className="issue-list">
              {commit.record_results.map((result) => (
                <li key={`${result.source_index}-${result.status}`}>
                  记录 {result.source_index}：{result.reason}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              compact
              eyebrow="暂未提交"
              title="当前 mock 场景没有提交结果"
              description="只有当存在可导入记录并点击主动作后，这里才会显示导入完成反馈。"
            />
          )}
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
