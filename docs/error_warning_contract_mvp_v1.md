# Error And Warning Contract MVP v1

## 目标

当前 MVP 还没有统一的全局错误码体系，但已经存在稳定的最小错误与 warning 语义。

本文件的目标不是引入新实现，而是冻结当前最小约定，避免后续前端、小程序、桌面端接入时误解错误含义。

## 当前错误语义分层

### 1. HTTP transport errors

当前后端至少保持这些 transport 语义：

- `404`
  - 资源不存在
  - 当前常见返回：
    - `{"detail": "..."}`
- `422`
  - 请求体或字段校验失败
  - 可能来自：
    - FastAPI / Pydantic 请求校验
    - 业务层 `ValidationFailedError`

当前 MVP 不要求所有错误都统一成一个 envelope。
调用方至少应兼容：

- `detail`
- 可选 `errors`

### 2. Payload-level warnings / errors

当前 import / progress / pulse / multi-surface draft 体系大量使用 payload 内部字段来表达 warning，而不是全部通过 HTTP error 抛出。

典型字段：

- `warnings`
- `errors`
- `metadata_warnings`
- `visibility_notes`
- `delivery_notes`

这些字段本身就是 contract 的一部分。

## 最小分类约定

以下分类是当前 MVP 应持续表达的“逻辑类别”，不等于所有地方都有统一 `code` 字段。

### `validation_error`
- 含义：
  - 请求字段不合法
  - 枚举值不合法
  - 必填字段缺失
- 当前常见落点：
  - HTTP `422`
  - `detail`

### `import_parse_error`
- 含义：
  - 导入内容无法解析，或格式明显错误
- 当前常见落点：
  - `PaperImportPreviewResult.errors`
  - `PaperImportPreviewRecord.errors`

### `import_commit_error`
- 含义：
  - commit 阶段单条记录失败或不可提交
- 当前常见落点：
  - `PaperImportCommitResult.errors`
  - `PaperImportCommitRecordResult.status`
  - `PaperImportCommitRecordResult.reason`

### `paper_not_found`
- 含义：
  - 论文不存在
- 当前常见落点：
  - HTTP `404`
  - `detail`

### `progress_update_error`
- 含义：
  - 论文进度更新请求非法或目标不存在
- 当前常见落点：
  - HTTP `422`
  - HTTP `404`

### `pulse_generation_warning`
- 含义：
  - Pulse 能生成，但上下文不足、内容为空、元数据不完整
- 当前常见落点：
  - `ResearchPulseResult.warnings`
  - section `empty_reason`

### `delivery_draft_only`
- 含义：
  - 当前输出只是 draft / preview，不是真实发送
- 当前常见落点：
  - `dry_run`
  - `delivery_state`
  - `delivery_notes`
  - `visibility_notes`
  - `warnings`

### `share_safety_warning`
- 含义：
  - 分享安全边界触发裁剪或隐藏字段
- 当前常见落点：
  - `MiniProgramDetailResult.visibility_notes`
  - `MiniProgramShareCard.redacted_fields`
  - `warnings`

### `metadata_incomplete`
- 含义：
  - 论文缺少作者、年份、来源、DOI 等关键元数据
- 当前常见落点：
  - `PaperProgressItemRead.warnings`
  - `ResearchPulseItem.metadata_warnings`
  - mini/detail card warnings

### `unsupported_format`
- 含义：
  - 当前 MVP 暂不支持某类导入格式或真实平台集成
- 当前常见落点：
  - import preview `errors / warnings`
  - 文档层明确暂缓

## 当前 warning / error 结构约定

### Import 层

#### `PaperImportProblem`
字段：
- `code`
- `message`
- `field`

用途：
- 结构化表达 import warning / error
- 适合前端或脚本做字段级提示

#### `PaperImportPreviewRecord`
字段：
- `warnings`
- `errors`
- `can_commit`

约定：
- 有 `errors` 时通常不可提交
- 只有 `warnings` 时可以继续 commit

#### `PaperImportCommitRecordResult`
字段：
- `status`
- `reason`
- `warnings`
- `errors`

约定：
- `status` 用于区分 `committed / skipped / failed / dry_run`
- `reason` 是当前最稳定的 per-record 解释字段

### Progress / Pulse / Multi-surface 层

当前更多采用：
- `warnings`
- `metadata_warnings`
- `empty_reason`
- `delivery_notes`
- `visibility_notes`

这些字段多数是面向产品层的解释文本，不一定都有统一 code。

因此当前调用方应优先按下面方式消费：

1. 先看 HTTP status
2. 再看 `detail`
3. 再看 payload 中的：
   - `warnings`
   - `errors`
   - `metadata_warnings`
   - `empty_reason`
   - `delivery_notes`
   - `visibility_notes`

## 中国市场场景说明

### 中文表格列名不匹配
- 可能表现为：
  - `validation_error`
  - `import_parse_error`
- 当前建议：
  - 先修正表头
  - 再执行 import preview

### PDF 文件夹占位导入缺元数据
- 可能表现为：
  - `metadata_incomplete`
  - `share_safety_warning`
- 当前建议：
  - 允许导入
  - 在 progress / pulse / mini detail 中继续提示补全

### `CNKI / Wanfang / VIP` 正式导入暂缓
- 当前属于：
  - `unsupported_format`
  - 文档层 non-goal
- 不应伪装成已支持能力

### 小程序分享或 preview
- `share_safe=true` 时必须裁剪：
  - `raw_source_payload`
  - debug raw data
  - 内部 notes
- 这类裁剪属于：
  - `share_safety_warning`
  - `visibility_notes`

## 冻结规则

- 不要求当前 MVP 立即统一全局错误码
- 但不能破坏已有最小语义：
  - `404` 仍然表示资源不存在
  - `422` 仍然表示校验失败
  - import preview / commit 仍然保留结构化 `warnings / errors`
  - multi-surface draft 仍然保留 `draft / preview / not_sent` 边界说明
