# Mini Program Detail MVP v1

## Pivot-8 目标

- 在不实现真实微信小程序 frontend 的前提下，提供适合小程序详情页消费的后端 detail payload / preview。
- 输入来源限定为：
  - 已导入论文
  - 论文进度上下文
  - Pivot-5 的 `ResearchPulseResult`
- 输出必须保持 share-safe、deterministic、中文可读。

## 输入来源

- `daily_pulse`、`next_actions`、`metadata_attention`、`triage` 详情复用 `ResearchPulseService`。
- `paper` 详情复用 `PaperProgressWorkbenchService` 与现有 `PaperProfile`。
- 本轮不读取真实微信身份，不接入 openid / unionid，不做订阅消息或支付。

## Detail Preview Flow

1. 接收 `MiniProgramDetailRequest`
2. 解析 `detail_type`
3. 复用 `ResearchPulseService` 或 `PaperProgressWorkbenchService`
4. 生成：
   - `cards`
   - `actions`
   - `share_card`
   - `navigation`
5. 对 `share_safe=true` 的结果做裁剪
6. 返回 `MiniProgramDetailResult`

## Request 字段

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

## Result 字段

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

## Card / Item / Action / Share Card / Navigation

### Card

- `card_id`
- `card_type`
- `title`
- `subtitle`
- `body`
- `items`
- `badges`
- `warnings`
- `empty_reason`

### Item

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

### Action

- `action_id`
- `label`
- `kind`
- `path`
- `payload`

### Share Card

- `title`
- `summary`
- `path`
- `image_placeholder`
- `share_safe`
- `redacted_fields`

### Navigation

- `current_path`
- `back_path`
- `related_paths`

## detail_type 设计

### `daily_pulse`

- 用于展示今日 Research Pulse 详情概览。
- 默认生成：
  - 今日概览
  - 今日重点论文
  - 继续阅读与分析
  - 下一步动作
  - 元数据待补全
  - 新导入待筛选
- path placeholder：
  - `/pages/pulse/detail?date=YYYY-MM-DD`

### `paper`

- 用于展示单篇论文详情。
- 只返回适合小程序详情页消费的基础元数据、进度字段和 share-safe 摘要。
- 若 `paper_id` 缺失或无效，返回结构化空状态，不抛出小程序侧错误。
- path placeholder：
  - `/pages/papers/detail?id=PAPER_ID`

### `next_actions`

- 用于展示已有 `next_action` 的论文列表。
- 默认排除 `low` 优先级；开启 `include_low_priority=true` 后可放开。
- path placeholder：
  - `/pages/papers/list?filter=next_action`

### `metadata_attention`

- 仅展示作者、年份、来源、DOI 等元数据待补全的论文。
- 不把“高优先级但未写 next action”之类非元数据 warning 混入该详情。
- path placeholder：
  - `/pages/papers/list?filter=metadata_attention`

### `triage`

- 展示 `inbox / triage / unread` 的新导入待筛选论文。
- path placeholder：
  - `/pages/papers/list?filter=triage`

## Share-Safe 规则

- `share_safe=true` 时：
  - 不暴露原始导入 payload
  - 不暴露 `user_note` / `research_note`
  - 不暴露内部调试字段
  - 只允许输出 `safe_abstract`
- `share_safe=false` 时：
  - 仍然不暴露 token、微信身份字段或真实敏感数据
  - 仍然不直接返回 `raw_source_payload`

## Path Placeholder 规则

- 所有 path 都是未来小程序 frontend 的占位路径。
- 当前仅输出字符串，不触发任何真实微信 API。
- 典型 path：
  - `/pages/pulse/detail?date=YYYY-MM-DD`
  - `/pages/papers/detail?id=PAPER_ID`
  - `/pages/papers/list?filter=next_action`
  - `/pages/papers/list?filter=metadata_attention`
  - `/pages/papers/list?filter=triage`

## visibility_notes / delivery_state 语义

- `delivery_state` 固定为 `preview`
- 语义是：
  - 当前结果只是详情页 preview
  - 不是微信小程序真实页面
  - 不是微信登录态
  - 不是订阅消息或支付结果
- `visibility_notes` 用来明确：
  - 当前 path 只是前端占位
  - 当前结果经过 share-safe 裁剪

## 与 Pivot-5 / Pivot-7 的关系

- Pivot-5 负责生成 `ResearchPulseResult`
- Pivot-7 负责生成桌面通知草稿
- Pivot-8 负责把 pulse/progress 数据转成小程序详情 payload
- 三者都只做结构化 preview，不做真实外部投递

## 中国市场使用场景

- 研究生查看今日应优先推进的论文
- 博士生在小程序详情里继续跟进 `next_action`
- 导师或课题组成员查看待筛选论文队列
- 表格导入或 PDF 文件夹导入后，优先补齐元数据

## 示例

### daily_pulse

- title: `2026-04-19 科研 Pulse 详情`
- subtitle: `面向微信小程序详情页的结构化预览`
- summary: `今日已从 6 篇已导入论文中整理出 2 篇重点推进论文，1 项明确的下一步动作。`

### paper

- title: `Paper Detail Preview`
- subtitle: `论文详情预览`
- share card summary: `当前为高优先级，精读中，研究阶段为阅读分析中。`

## 已知限制

- 还没有真实小程序 frontend
- 还没有微信登录态
- 还没有小程序页面渲染
- 还没有真实分享链路
- `safe_abstract` 只在已有抽象文本可安全提取时返回

## 暂缓事项

- 真实微信小程序 frontend
- 微信登录
- openid / unionid 绑定
- 订阅消息
- 支付
- 微信 API 调用
- access_token 管理
- 小程序码生成
- 真实分享追踪
- 定时任务
- 复杂订阅系统
- 运营后台
- 微信公众号真实发送
- 桌面真实通知
- 外部检索
- 外部 LLM 调用
- CNKI / Wanfang / VIP 正式导入
- Zotero connector / plugin / sync
- PDF metadata extraction
- OCR
- frontend UI
