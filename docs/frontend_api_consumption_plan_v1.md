# Frontend API Consumption Plan v1

## 目标

本文件说明前端如何消费已冻结的 MVP API contract，以及如何在 mock mode 和 real API mode 之间切换。

## 总原则

1. 前端不推动 backend 改 contract。  
2. 前端优先消费已冻结 schema。  
3. `draft / preview / not_sent` 语义必须原样保留。  
4. warning 和 error 要翻译成中文建议，不直接暴露技术字段。  
5. 不直接展示 `raw_source_payload`。  
6. 小程序相关输出必须遵守 `share_safe` 边界。

## 首版需要的 endpoint 清单

Frontend-1 最小范围只需要关注以下 endpoint：

- `POST /papers/import-preview`
- `POST /papers/import-commit`
- `GET /papers/progress/summary`
- `GET /papers/progress/pulse-context`
- `POST /pulse/papers/daily`
- `POST /pulse/papers/official-account/daily-summary`
- `POST /pulse/papers/desktop-notification/draft`
- `POST /pulse/papers/mini-program/detail/preview`

补充说明：

- `POST /users` 当前仍属于 setup 阶段，不建议在 Frontend-1 做页面化入口。
- Frontend-1 在 real API mode 下应假设 demo user 已经存在。

## 页面到 endpoint 的映射

## 首页 / 今日 Research Pulse

### mock mode

- 读取：
  - `paper_progress_summary.json`
  - `research_pulse.json`

### real API mode

- `GET /papers/progress/summary`
- `GET /papers/progress/pulse-context`
- `POST /pulse/papers/daily`

### UI 关注字段

- summary:
  - `total_papers`
  - `reading_count`
  - `high_priority_count`
  - `urgent_count`
  - `with_next_action_count`
- pulse:
  - `title`
  - `summary`
  - `sections`
  - `warnings`
  - `dry_run`

## 导入 / 导入预览

### mock mode

- 读取：
  - `import_preview.json`
  - `import_commit.json`

### real API mode

- `POST /papers/import-preview`
- `POST /papers/import-commit`

### UI 关注字段

- preview:
  - `preview_id`
  - `total_records`
  - `valid_records_count`
  - `warning_records_count`
  - `error_records_count`
  - `records`
- commit:
  - `total_selected`
  - `committed_count`
  - `skipped_count`
  - `failed_count`
  - `record_results`

## Research Pulse 详情

### mock mode

- 读取：
  - `research_pulse.json`
  - 可选渠道侧产物：
    - `official_account_daily_summary.json`
    - `desktop_notification.json`
    - `mini_program_daily_pulse_detail.json`

### real API mode

- `POST /pulse/papers/daily`
- `POST /pulse/papers/official-account/daily-summary`
- `POST /pulse/papers/desktop-notification/draft`
- `POST /pulse/papers/mini-program/detail/preview`

### UI 关注字段

- pulse:
  - `sections`
  - `warnings`
  - `source_context_notes`
- official-account:
  - `title`
  - `headline`
  - `summary`
  - `publication_preview`
- desktop:
  - `title`
  - `body`
  - `urgency`
  - `delivery_state`
- mini:
  - `title`
  - `cards`
  - `share_card`
  - `navigation`
  - `delivery_state`

## request / response 关系

## 导入预览

- request：
  - `PaperImportPreviewCreateRequest`
- response：
  - `PaperImportPreviewResult`

前端展示重点：

- 结果统计
- 单条记录是否可提交
- warning / error 的中文说明

## 导入提交

- request：
  - `PaperImportCommitRequest`
- response：
  - `PaperImportCommitResult`

前端展示重点：

- 哪些记录 committed
- 哪些 skipped
- 哪些 failed

## Pulse

- request：
  - `ResearchPulseRequest`
- response：
  - `ResearchPulseResult`

前端展示重点：

- title / summary
- section title / description / items
- `dry_run`

## 公众号草稿

- request：
  - `OfficialAccountDailySummaryRequest`
- response：
  - `OfficialAccountDailySummaryResult`

前端展示重点：

- 它是草稿，不是发送结果
- `publication_preview`
- `template_payload_preview`

## 桌面通知草稿

- request：
  - `DesktopNotificationRequest`
- response：
  - `DesktopNotificationResult`

前端展示重点：

- `delivery_state = draft`
- `payload_preview`
- `actions`

## 小程序详情预览

- request：
  - `MiniProgramDetailRequest`
- response：
  - `MiniProgramDetailResult`

前端展示重点：

- `delivery_state = preview`
- `share_card.share_safe`
- `visibility_notes`

## `draft / preview / not_sent` 如何展示

前端必须把这些状态当作首屏语义，不是埋在 JSON 深处。

### 公众号草稿

- 用文案明确展示：
  - `草稿`
  - `未发送`

### 桌面通知

- 用文案明确展示：
  - `草稿`
  - `未推送`

### 小程序详情

- 用文案明确展示：
  - `预览`
  - `share-safe`

## warning / error 如何转成中文建议

前端不要直接展示：

- `missing_required_field`
- `invalid_tabular`
- 其他内部 code

前端应转成：

- 缺少题名，当前记录暂不可导入
- 这条记录还能继续导入，但建议补全年份
- 当前还没有可生成的 Pulse，建议先导入论文

## API 失败时的页面状态

### loading

- 页面保留当前结构骨架
- 不要让用户误以为已完成

### empty

- 给下一步动作
- 例如：
  - 先导入论文
  - 先生成今日 Pulse

### warning

- 允许继续
- 同时告诉用户建议处理什么

### error

- 说明当前无法继续
- 给出明确下一步：
  - 重试
  - 返回导入
  - 查看问题记录

## `raw_source_payload` 与 share-safe 边界

前端不应直接展示：

- `raw_source_payload`
- `import_raw_source_payload`
- `user_note`
- `research_note`

小程序详情只展示 share-safe 允许的字段。

## 开发期模式切换

## mock mode

适用阶段：

- Frontend-1 初期
- 设计联调
- 本地离线演示

特点：

- 不依赖 API
- 不依赖 token
- 直接读取 demo JSON

## real API mode

适用阶段：

- 内部开发联调
- contract 验证

前提：

- 已有 demo user
- 已有内部 bearer token
- 不做登录 UI

建议做法：

- 用一层很薄的 data source 开关
- 保持页面 UI 不变，只替换数据提供方

