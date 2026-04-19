# Schema Contract MVP v1

## 目标

本文件冻结当前 MVP 主链路里最关键的 request / response schema 字段契约。

冻结重点是：

- 调用方稳定可依赖的字段
- 不随意删除的关键字段
- `draft / preview / share_safe / warnings / errors` 相关字段语义

本文件不追求枚举所有内部字段，而是强调对客户端、测试和后续接入方稳定有意义的部分。

## 核心 schema 分组

### 1. Import preview / commit

#### `PaperImportPreviewResult`
关键字段：
- `preview_id`
- `source_format`
- `created_at`
- `total_records`
- `valid_records_count`
- `warning_records_count`
- `error_records_count`
- `records`
- `warnings`
- `errors`

#### `PaperImportPreviewRecord`
关键字段：
- `source_index`
- `normalized_record`
- `title`
- `authors`
- `year`
- `venue`
- `doi`
- `url`
- `keywords`
- `warnings`
- `errors`
- `can_commit`
- `selected`

#### `PaperImportCommitResult`
关键字段：
- `preview_id`
- `user_id`
- `source_format`
- `dry_run`
- `committed_at`
- `total_selected`
- `committed_count`
- `skipped_count`
- `failed_count`
- `committed_record_ids`
- `record_results`
- `warnings`
- `errors`

#### `PaperImportCommitRecordResult`
关键字段：
- `source_index`
- `status`
- `reason`
- `paper_id`
- `warnings`
- `errors`

### 2. Paper progress

#### `PaperProgressItemRead`
关键字段：
- `paper_id`
- `user_id`
- `title`
- `authors`
- `year`
- `venue`
- `doi`
- `url`
- `source_format`
- `reading_status`
- `research_stage`
- `priority`
- `priority_score`
- `next_action`
- `user_note`
- `research_note`
- `tags`
- `imported_at`
- `created_at`
- `updated_at`
- `last_touch_at`
- `warnings`

#### `PaperProgressUpdateRequest`
关键字段：
- `reading_status`
- `research_stage`
- `priority`
- `next_action`
- `clear_next_action`
- `user_note`
- `research_note`
- `tags`

#### `PaperProgressSummaryRead`
关键字段：
- `total_papers`
- `unread_count`
- `reading_count`
- `read_count`
- `high_priority_count`
- `urgent_count`
- `with_next_action_count`
- `by_reading_status`
- `by_research_stage`
- `by_priority`

### 3. Research Pulse

#### `ResearchPulseRequest`
关键字段：
- `user_id`
- `pulse_date`
- `timezone`
- `max_items_per_section`
- `include_low_priority`
- `include_archived`
- `source_format_filter`
- `dry_run`

#### `ResearchPulseResult`
关键字段：
- `draft_id`
- `user_id`
- `pulse_date`
- `timezone`
- `dry_run`
- `title`
- `summary`
- `sections`
- `total_source_papers`
- `total_items`
- `warnings`
- `generated_at`
- `source_context_notes`

#### `ResearchPulseSection`
关键字段：
- `section_id`
- `title`
- `description`
- `items`
- `empty_reason`

#### `ResearchPulseItem`
关键字段：
- `paper_id`
- `title`
- `authors`
- `year`
- `venue`
- `doi`
- `url`
- `priority`
- `reading_status`
- `research_stage`
- `next_action`
- `reason`
- `suggested_action`
- `metadata_warnings`
- `tags`
- `source_format`

### 4. Official-account daily summary

#### `OfficialAccountDailySummaryRequest`
关键字段：
- `user_id`
- `pulse_date`
- `timezone`
- `max_items_per_section`
- `max_highlights`
- `include_low_priority`
- `include_archived`
- `source_format_filter`
- `binding_id`
- `dry_run`

#### `OfficialAccountDailySummaryResult`
关键字段：
- `draft_id`
- `source_research_pulse_draft_id`
- `user_id`
- `pulse_date`
- `timezone`
- `dry_run`
- `title`
- `headline`
- `summary`
- `sections`
- `highlight_count`
- `publication_preview`
- `template_payload_preview`
- `binding_preview`
- `provider_preview`
- `total_source_papers`
- `warnings`
- `generated_at`
- `source_context_notes`

### 5. Desktop notification

#### `DesktopNotificationRequest`
关键字段：
- `user_id`
- `pulse_date`
- `timezone`
- `max_items`
- `include_low_priority`
- `include_archived`
- `source_format_filter`
- `title_prefix`
- `include_actions`
- `dry_run`

#### `DesktopNotificationResult`
关键字段：
- `draft_id`
- `source_research_pulse_draft_id`
- `user_id`
- `pulse_date`
- `timezone`
- `title`
- `body`
- `notification_type`
- `urgency`
- `badge_count`
- `items`
- `actions`
- `deep_link`
- `payload_preview`
- `total_source_papers`
- `total_items`
- `warnings`
- `generated_at`
- `delivery_state`
- `delivery_notes`

#### `DesktopNotificationAction`
关键字段：
- `action_id`
- `label`
- `kind`
- `deep_link`
- `payload`

### 6. Mini-program detail

#### `MiniProgramDetailRequest`
关键字段：
- `user_id`
- `detail_type`
- `pulse_date`
- `timezone`
- `paper_id`
- `source_research_pulse_draft_id`
- `max_items`
- `include_low_priority`
- `include_archived`
- `source_format_filter`
- `share_safe`
- `dry_run`

#### `MiniProgramDetailResult`
关键字段：
- `detail_id`
- `detail_type`
- `user_id`
- `pulse_date`
- `timezone`
- `title`
- `subtitle`
- `summary`
- `cards`
- `actions`
- `share_card`
- `navigation`
- `source_research_pulse_draft_id`
- `total_source_papers`
- `total_items`
- `warnings`
- `generated_at`
- `delivery_state`
- `visibility_notes`

#### `MiniProgramDetailCard`
关键字段：
- `card_id`
- `card_type`
- `title`
- `subtitle`
- `body`
- `items`
- `badges`
- `warnings`
- `empty_reason`

#### `MiniProgramDetailItem`
关键字段：
- `item_id`
- `paper_id`
- `title`
- `authors`
- `year`
- `venue`
- `doi`
- `url`
- `priority`
- `reading_status`
- `research_stage`
- `next_action`
- `reason`
- `suggested_action`
- `metadata_warnings`
- `tags`
- `source_format`
- `safe_abstract`
- `detail_path`

#### `MiniProgramShareCard`
关键字段：
- `title`
- `summary`
- `path`
- `image_placeholder`
- `share_safe`
- `redacted_fields`

#### `MiniProgramNavigation`
关键字段：
- `current_path`
- `back_path`
- `related_paths`

## 稳定性规则

### 不随意删除字段
- 已进入：
  - API contract 文档
  - smoke test
  - contract tests
  的关键字段，不应随意删除。

### 不随意改变字段类型
- 不应把：
  - `list` 改成 `dict`
  - `str` 改成 `bool`
  - `UUID` 改成不兼容类型
- 如果必须变更，应先新增兼容字段，再迁移调用方。

### 新字段应尽量向后兼容
- 新增字段优先：
  - optional
  - 有默认值
  - 不影响现有消费者

### `draft / preview / not_sent` 相关字段语义不能漂移
- `ResearchPulseRequest.dry_run`
- `OfficialAccountDailySummaryRequest.dry_run`
- `DesktopNotificationResult.delivery_state`
- `MiniProgramDetailResult.delivery_state`
- `MiniProgramDetailResult.visibility_notes`

这些字段或等价语义必须继续表达：
- 当前结果只是草稿或预览
- 并不代表真实发送成功

### `warnings / errors` 语义不能漂移
- import preview / commit 里的 `warnings / errors` 应继续用于结构化解释
- 不应把警告 silently 吞掉
- 不应把 warning 变成不透明字符串集合而失去核心字段

### `share_safe=true` 时不能暴露原始导入内容
- `MiniProgramDetailRequest.share_safe=true` 时：
  - 不暴露 `raw_source_payload`
  - 不暴露调试字段
  - 不暴露内部 notes
  - 只允许 `safe_abstract`

## 当前冻结范围

本文件冻结的是当前 MVP 主链路契约，不冻结：
- admin overbuild 旧轨道
- 外部检索扩展
- 真实微信 / 桌面 / 小程序平台接入
- 后续大版本 schema 设计
