# 微信公众号每日摘要 MVP v1

## Pivot-6 的目标

Pivot-6 的目标是在 Pivot-5 已生成的论文型 `ResearchPulseResult` 基础上，补一层**适合微信公众号模板消息的每日摘要 draft / payload preview**。

这一层的作用是：

- 复用已导入论文与论文进度上下文
- 生成适合公众号模板的标题、副标题、重点条目和落地信息
- 输出安全的 payload preview
- 对接现有 official-account delivery path 的数据结构

本阶段仍然**不是实际投递阶段**。

## Daily Summary Generation Flow

1. Pivot-2 负责导入格式解析与归一化。
2. Pivot-3 将选中的导入结果写入现有 `PaperProfile`。
3. Pivot-4 提供论文进度工作台与 `pulse context`。
4. Pivot-5 生成基于论文进度的 `ResearchPulseResult`。
5. Pivot-6 把 `ResearchPulseResult` 转成公众号每日摘要 draft、`publication_preview` 和模板 payload preview。

## 输入来源

Pivot-6 不重新计算论文进度，而是直接消费 Pivot-5：

- `ResearchPulseService.generate_daily_pulse(...)`
- `PaperProgressWorkbenchService` 输出的论文进度上下文

因此本阶段的每日摘要始终基于：

- 已导入论文
- 阅读状态
- 研究阶段
- 优先级
- 下一步动作
- 元数据缺失提醒
- 导入来源格式

## Request 字段

`OfficialAccountDailySummaryRequest` 当前包括：

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

说明：

- `timezone` 默认 `Asia/Shanghai`
- `max_highlights` 控制公众号重点条目数量，默认 `3`
- `binding_id` 只用于预览某个已激活公众号绑定的 payload 形状
- `dry_run=false` 目前也不会创建真实发送任务

## Result 字段

`OfficialAccountDailySummaryResult` 当前包括：

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

## Section 设计

Pivot-6 直接复用 Pivot-5 的 section 结构，再压缩成更适合公众号摘要的展示项：

### 1. 今日重点论文

- 优先展示 `urgent / high`
- 有 `next_action` 的论文优先
- 适合公众号摘要里的首屏重点

### 2. 继续阅读与分析

- 适合研究生、博士生日常推进略读和精读
- 帮助公众号摘要形成“继续读什么”的提醒

### 3. 下一步动作

- 直接整理已明确写下 `next_action` 的论文
- 有利于在公众号摘要里形成清晰行动提示

### 4. 元数据待补全

- 特别适合 PDF 文件夹占位导入后的补全提醒
- 提醒作者、年份、来源、DOI 等关键字段缺失

### 5. 新导入待筛选

- 让表格导入、引文导入或 PDF 导入后的论文进入筛选流程

## Highlight 规则

`digest_highlights` 从上述 section 中按固定顺序提取：

1. 先遍历 section 顺序
2. 再遍历 section 内条目顺序
3. 同一篇论文只保留第一次出现
4. 截断到 `max_highlights`

每条 highlight 至少包括：

- `sort_order`
- `section_id`
- `section_title`
- `paper_id`
- `title`
- `summary`
- `why_now`
- `suggested_action`

## publication_preview 兼容策略

Pivot-6 明确复用了既有 digest publication preview 的命名习惯，输出：

- `digest_title`
- `digest_subtitle`
- `digest_highlights`
- `primary_cta_text`
- `primary_cta_path`
- `mini_program_path`
- `article_url`

这样后续如果要把 paper-based pulse 正式接到现有 official-account delivery path，可以继续沿用相同的数据形状，而不必在发送前再做一次大规模重构。

当前默认落地路径：

- `primary_cta_path = /mini/today`
- `mini_program_path = mini/today`

如果已配置 `APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL`，会同步生成 `article_url` 预览。

## 模板 payload preview

本阶段只生成**安全的模板 payload 预览**，不生成真实发送请求。

`template_payload_preview` 当前包括：

- `template_id_configured`
- `field_mapping`
- `logical_fields`
- `payload_preview`

其中：

- `field_mapping` 复用现有模板字段映射配置；未配置时使用内置默认值
- `payload_preview` 只展示模板消息的字段形状
- 如果存在目标绑定，只返回 `touser_masked`
- 不返回真实 openid

## Binding Preview

`binding_preview` 用于说明当前用户是否已经具备后续投递所需的公众号绑定条件：

- `active_binding_count`
- `selected_binding`
- `notes`

active binding 的定义沿用现有 digest 逻辑：

- channel 为 `official_account`
- `bind_state = active`
- `subscribed = true`
- `digest_enabled = true`

## Provider Preview

`provider_preview` 只做安全配置预览，不读取 token、不做真实发送。

当前输出：

- `provider_mode`
- `transport_kind`
- `template_id_configured`
- `template_field_mapping_configured`
- `article_base_url_configured`
- `mini_program_app_id_configured`
- `callback_enabled`
- `real_send_enabled`
- `notes`

这意味着即使当前 provider mode 是 `disabled`，仍然可以生成公众号摘要草稿。

## 中文内容生成边界

Pivot-6 的中文标题、headline、summary、reason、suggested action 仍然保持 deterministic / template-based。

允许：

- 按已有优先级、阅读状态、研究阶段生成中文摘要
- 输出行动导向、运营可读的公众号摘要草稿

不允许：

- 编造论文摘要
- 假装已经阅读全文
- 凭空生成不存在的研究结论
- 调用第三方模型改写内容

## 持久化策略

Pivot-6 当前**不新增 migration，也不落任何新的公众号摘要表**。

采用策略：

- 复用 Pivot-5 的 `ResearchPulseService`
- 复用现有公众号绑定 repository
- 生成 `publication_preview`
- 生成模板 payload preview
- 不创建 `PulseDigestIssue`
- 不创建 `DigestPublicationJob`
- 不创建发送 attempt

这保证了本阶段边界仍然清晰：**只做每日摘要 draft 和 payload preview，不做真实投递。**

## 与后续阶段的边界

Pivot-6 到此为止，不继续：

- 真实公众号发送
- 定时调度
- 复杂订阅系统扩展
- 小程序详情页
- 桌面通知

后续阶段分工：

- Pivot-7：桌面通知 MVP
- Pivot-8：小程序详情 MVP

公众号真实投递能力如果需要继续推进，应在后续阶段复用本阶段输出的 `publication_preview` 和模板 payload preview，而不是另起一套摘要结构。

## 中国市场使用场景

- 研究生每天先看“今日重点论文”和“下一步动作”
- 博士生用公众号摘要快速回顾当前高优先级论文
- 课题组可先用公众号摘要 preview 做日更模板内容校验
- PDF 文件夹导入后的论文可通过“元数据待补全” section 提醒尽快整理
- 表格导入后的批量论文可通过“新导入待筛选”进入正式研究流程

## 示例

标题示例：

- `2026-04-19 公众号每日摘要草稿`

headline 示例：

- `今日优先推进 2 篇重点论文，明确执行 1 项下一步动作`

summary 示例：

- `今日已从 8 篇已导入论文中整理出 2 篇重点论文，3 篇继续阅读与分析，1 项下一步动作，共准备 3 条公众号摘要重点。`

highlight 示例：

- 标题：`高优先级方法论文`
- summary：`该论文处于精读中且属于高优先级，建议继续整理方法与实验设计；建议：先整理方法对比表`

## 已知限制

- 当前不生成真实发送任务
- 当前不创建 digest issue
- 当前不绑定具体发布时间
- 当前不生成公众号图文封面、排版或富文本正文
- 当前不生成小程序详情页正文
- 当前不做桌面提醒

## 暂缓事项

- 微信公众号真实投递
- 定时任务
- 小程序详情页
- 桌面通知
- CNKI 正式导入
- Wanfang 正式导入
- VIP 正式导入
- Zotero connector / plugin / sync
- PDF metadata extraction
- OCR
- 前端 UI
