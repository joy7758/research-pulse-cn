# 桌面通知 MVP v1

## Pivot-7 目标

Pivot-7 的目标是在 Pivot-5 已生成的 `ResearchPulseResult` 基础上，补一层**适合桌面端消费的本地提醒草稿 / payload preview**。

这一层只解决两件事：

- 把每日 Research Pulse 草稿压缩成适合桌面提醒展示的短标题、短正文和重点条目
- 为未来桌面客户端提供稳定的 actions、deep link placeholder 和 payload preview

本阶段仍然**不是客户端实现阶段**，也不是操作系统级提醒阶段。

## 输入来源：Research Pulse draft

Pivot-7 不重新计算论文上下文，而是直接复用 Pivot-5：

- `ResearchPulseService.generate_daily_pulse(...)`

因此桌面通知草稿始终基于：

- 已导入论文
- 阅读状态
- 研究阶段
- 优先级
- 下一步动作
- 元数据缺失提醒
- 导入来源格式

## Desktop Notification Draft Flow

1. Pivot-5 生成 `ResearchPulseResult`
2. Pivot-7 读取 `sections`
3. 依固定顺序抽取桌面提醒项
4. 生成短标题 `title`
5. 生成短正文 `body`
6. 生成 `actions`
7. 生成 `deep_link`
8. 生成 `payload_preview`
9. 返回 `delivery_state = draft`

## Request 字段

`DesktopNotificationRequest` 当前包括：

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

说明：

- `timezone` 默认 `Asia/Shanghai`
- `max_items` 控制桌面提醒条目数量，默认 `3`
- `title_prefix` 默认 `今日科研 Pulse`
- `include_actions=false` 时只保留标题、正文和 payload preview
- `dry_run=false` 目前也不会进入真实交付流程

## Result 字段

`DesktopNotificationResult` 当前包括：

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

## Item 字段

`DesktopNotificationItem` 当前包括：

- `paper_id`
- `title`
- `line`
- `reason`
- `suggested_action`
- `priority`
- `reading_status`
- `research_stage`
- `metadata_warnings`
- `url`
- `doi`
- `tags`
- `source_format`

这些字段会给未来桌面客户端保留足够上下文，但通知正文本身不会把它们全部展开。

## Action 字段

`DesktopNotificationAction` 当前包括：

- `action_id`
- `label`
- `kind`
- `deep_link`
- `payload`

当前 action 主要是本地 deep link placeholder，例如：

- `research-pulse://pulse/daily/YYYY-MM-DD`
- `research-pulse://papers/progress?filter=next_action`
- `research-pulse://papers/progress?filter=metadata_attention`
- `research-pulse://papers/progress?filter=triage`

## title / body 生成规则

Pivot-7 的标题和正文都尽量短，适合桌面提醒样式。

标题规则：

- 有重点论文时：
  - `今日科研 Pulse：N 个重点事项`
- 没有重点论文但有下一步动作时：
  - `今日科研 Pulse：N 个下一步动作`
- 没有重点项但有待补全提醒时：
  - `今日科研 Pulse：N 条待补全提醒`
- 没有任何论文上下文时：
  - `今日科研 Pulse：今天没有重点提醒`

正文规则：

- 优先组合：
  - 高优先级论文数量
  - 下一步动作数量
  - 元数据待补全数量
  - 新导入待筛选数量
- 例如：
  - `有 2 篇高优先级论文、1 个下一步动作、1 条元数据待补全。`
- 如果没有重点内容：
  - `今天没有高优先级论文，建议先筛选新导入记录。`

## payload_preview 规则

`payload_preview` 当前包括：

- `notification_title`
- `notification_body`
- `badge_count`
- `urgency`
- `deep_link`
- `actions`
- `source_pulse_draft_id`
- `generated_at`
- `delivery_state`
- `notification_type`

这一层只描述未来桌面端可能消费的提醒结构，不代表任何真实交付已经发生。

## urgency / badge_count 规则

`urgency` 当前规则：

- `high`
  - 今日重点论文里存在 `urgent / high`
  - 或选中的桌面提醒条目里存在 `urgent`
- `normal`
  - 有提醒条目但没有达到 `high`
- `low`
  - 没有提醒条目

`badge_count` 当前规则：

- 统计以下 section 中去重后的论文数量：
  - `today_focus`
  - `next_actions`
  - `metadata_attention`
  - `newly_imported_triage`
- 上限 `99`

## delivery_state 语义

Pivot-7 当前固定返回：

- `delivery_state = draft`

对应语义是：

- 当前只生成本地桌面提醒草稿
- 没有进入真实交付
- 没有进入系统级提醒接口
- 没有进入任何推送服务

## deep link placeholder 规则

Pivot-7 只生成 deep link placeholder，不保证已有真实客户端解析。

当前约定：

- 默认入口：
  - `research-pulse://pulse/daily/YYYY-MM-DD`
- 下一步动作：
  - `research-pulse://papers/progress?filter=next_action`
- 元数据补全：
  - `research-pulse://papers/progress?filter=metadata_attention`
- 新导入筛选：
  - `research-pulse://papers/progress?filter=triage`

## 中文内容生成边界

Pivot-7 继续保持 deterministic / template-based 中文内容生成。

允许：

- 中文标题
- 中文正文
- 中文条目行文
- 中文动作标签

不允许：

- 编造论文摘要
- 假装已经阅读全文
- 根据不存在的 abstract / note 编造内容
- 输出“已发送成功”或“已推送成功”之类误导状态
- 调用外部模型自由改写

## 与 Pivot-5 的关系

Pivot-7 直接复用 Pivot-5 的 `ResearchPulseResult`，不是独立的一套提醒引擎。

因此：

- Pivot-5 负责结构化科研摘要
- Pivot-7 负责把摘要压缩成桌面端可消费的提醒草稿

## 与未来桌面客户端的边界

Pivot-7 到此为止，不继续：

- Electron 客户端
- Tauri 客户端
- 原生桌面程序
- 操作系统级提醒接口
- 定时提醒任务
- 本地托盘逻辑

未来如果要做真实桌面客户端，应该消费本阶段输出的：

- `title`
- `body`
- `items`
- `actions`
- `deep_link`
- `payload_preview`

而不是重新发明一套桌面提醒数据结构。

## 中国市场使用场景

- 研究生每天打开桌面端时先看到“今日科研 Pulse”
- 博士生快速知道今天是否有高优先级论文需要推进
- 课题组成员快速查看是否存在明确的下一步动作
- PDF 文件夹导入后，桌面端能提醒哪些论文还缺元数据
- 批量导入后，桌面端能提醒哪些论文还在待筛选队列

## 示例

标题示例：

- `今日科研 Pulse：3 个重点事项`
- `今日科研 Pulse：2 个下一步动作`

正文示例：

- `有 2 篇高优先级论文、1 个下一步动作、1 条元数据待补全。`
- `今天没有高优先级论文，建议先筛选新导入记录。`

action 示例：

- `查看今日 Pulse`
- `查看下一步动作`
- `补全元数据`
- `筛选新导入论文`

## 已知限制

- 当前不创建桌面交付任务
- 当前不调用操作系统级提醒接口
- 当前不管理提醒时间或频率
- 当前不生成托盘状态或角标同步
- 当前不生成客户端专属富交互 UI

## 暂缓事项

- Electron / Tauri / 原生桌面客户端
- macOS / Windows / Linux 操作系统级提醒
- APNs / FCM / Web Push
- 真实推送服务
- 定时任务
- 复杂订阅系统
- 运营后台
- 微信公众号真实发送
- 小程序详情页
- 外部检索
- 外部 LLM 调用
- CNKI / Wanfang / VIP 正式导入
- Zotero connector / plugin / sync
- PDF metadata extraction
- OCR
- frontend UI
