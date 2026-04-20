# 论文进度工作台 v1

## 目标

Pivot-4 在 Pivot-2 导入格式基础层和 Pivot-3 导入预览/提交基础层之上，补齐“已导入论文如何被持续管理”的后端能力。

本阶段只做后端基础能力，不做前端 UI，不做公众号、小程序、桌面通知，不做实际 Research Pulse 生成。

目标是让导入后的 `PaperProfile` 可以被视为研究对象，并支持：

- 阅读状态管理
- 研究阶段管理
- 优先级管理
- 下一步动作管理
- 轻量研究备注
- 工作台统计摘要
- 为后续 Pulse 生成提供结构化上下文

## Progress Workbench Flow

1. Pivot-2 解析论文元数据，形成 normalized import record。
2. Pivot-3 生成 import preview，并将 selected records 提交为 `PaperProfile`。
3. Pivot-4 基于现有 `PaperProfile`、`identifiers`、`stage`、`priority`、`next_action` 构建 progress item。
4. 调用方可以读取 progress 列表、详情、摘要，并对单篇论文进行进度更新。
5. Pivot-5 再基于 progress workbench 输出的结构化上下文生成 Research Pulse。

## Reading Status

代码标识符保持英文，面向中国市场的语义说明如下：

- `unread`：未读，通常刚导入或尚未进入筛选
- `skimming`：略读中，适合快速判断是否相关
- `reading`：精读中，已经进入重点阅读和分析
- `read`：已读，主要内容已完成阅读
- `archived`：已归档，当前不再主动跟进

默认情况下，如果未显式存储阅读状态，系统会把论文视为 `unread`。

## Research Stage

研究阶段使用现有 `PaperProfile.stage` 字段承载，不新增数据库字段。

- `inbox`：收件箱，刚导入或待整理
- `triage`：待筛选，准备判断是否值得继续跟进
- `relevant`：相关，已经确认与当前研究问题相关
- `reviewing`：阅读分析中，正在深入阅读、摘录或比较
- `cited`：已引用，已经进入综述、笔记或草稿引用链路
- `implemented`：已转化为研究动作，例如实验设计、方法实现、选题调整
- `parked`：暂停，暂时不跟进但保留上下文

对 Pivot-3 之前遗留的 `stage` 值，例如 `imported`、`published`、`revision`，工作台会做只读兼容映射，并在 `warnings` 中提示。

## Priority

优先级在工作台接口中使用语义化枚举，但仍复用现有 `PaperProfile.priority` 数字字段持久化：

- `low` -> `1`
- `normal` -> `3`
- `high` -> `4`
- `urgent` -> `5`

这样可以兼容现有模型、排序逻辑和旧测试。

## Progress Item 字段

工作台返回的 progress item 至少包含：

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

其中：

- `research_stage` 复用 `PaperProfile.stage`
- `priority` 是工作台语义值，`priority_score` 是底层数字值
- `reading_status`、`user_note`、`research_note`、`tags` 保存在 `identifiers.progress_workbench`
- `source_format`、`authors`、`year`、`keywords` 优先从导入链路保存的 import metadata 中恢复

## Progress Update 字段

Pivot-4 支持的更新字段：

- `reading_status`
- `research_stage`
- `priority`
- `next_action`
- `clear_next_action`
- `user_note`
- `research_note`
- `tags`

规则：

- `clear_next_action=true` 时会清空 `next_action`
- `reading_status`、`user_note`、`research_note`、`tags` 写入 `identifiers.progress_workbench`
- `research_stage` 更新现有 `PaperProfile.stage`
- `priority` 更新现有 `PaperProfile.priority`
- 每次更新都会刷新 `last_touch_at`

## Summary 字段

工作台摘要当前至少提供：

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

这组摘要适合后续桌面端、小程序或 API 调用方直接做工作台概览。

## Pulse Context 边界

Pivot-4 不生成实际 Pulse，只提供结构化上下文。

当前 `get_progress_context_for_pulse` 输出：

- `high_priority_papers`
- `papers_with_next_action`
- `active_review_papers`
- `metadata_attention_papers`
- `notes`

边界非常明确：

- 只返回论文进度上下文
- 不做文案生成
- 不做摘要生成
- 不调用模型
- 不触发投递

这些上下文会在 Pivot-5 被消费，用于生成基于已导入论文的 Research Pulse。

## 与导入链路的关系

Pivot-4 明确依赖 Pivot-2 / Pivot-3：

- Pivot-2 提供格式解析与 normalized import record
- Pivot-3 提供 import preview 与 import commit
- Pivot-4 读取 Pivot-3 已落库的 `PaperProfile`

为了减少 schema 扩张，本阶段继续复用 `PaperProfile`：

- `stage` 承载 research stage
- `priority` 承载 priority score
- `next_action` 继续作为下一步动作主字段
- `identifiers` 承载 progress workbench 轻量扩展信息

## 中国市场使用场景

本阶段的工作台语义优先面向中国市场论文管理场景：

- 研究生可以把批量导入的论文先放进 `inbox`，再逐步筛到 `triage` / `relevant`
- 博士生可以把重点论文标成 `high` 或 `urgent`，并维护明确 `next_action`
- 导师或课题组可以基于高优先级论文和 `with_next_action` 论文快速识别当前研究重点
- 表格导入后可以通过 `reading_status`、`research_stage`、`priority` 做快速筛选
- PDF 文件夹占位导入如果元数据不完整，会在 `warnings` 里提醒后续补全

## 示例

### 列表过滤

- `GET /papers/progress?user_id=<uuid>&reading_status=reading`
- `GET /papers/progress?user_id=<uuid>&priority=urgent&has_next_action=true`
- `GET /papers/progress?user_id=<uuid>&keyword=关键论文`

### 详情

- `GET /papers/{paper_id}/progress`

### 更新

```json
{
  "reading_status": "reading",
  "research_stage": "reviewing",
  "priority": "high",
  "next_action": "整理方法对比表",
  "user_note": "导师要求本周内看完",
  "research_note": "重点比较实验设置和评价指标",
  "tags": ["baseline", "materials"]
}
```

### 统计摘要

- `GET /papers/progress/summary?user_id=<uuid>`

### Pulse 上下文

- `GET /papers/progress/pulse-context?user_id=<uuid>`

## 已知限制

- 仍然没有完整前端 UI
- `reading_status`、备注、标签当前保存在 `identifiers.progress_workbench`
- 仅做 batch 内和本地工作台层面的轻量上下文，不做复杂任务编排
- 不做复杂笔记编辑器
- 不做跨库去重
- 不做实际 Pulse 生成

## 暂缓事项

- 完整前端 UI
- 批量编辑 UI
- 复杂任务管理
- 复杂笔记系统
- 跨库去重
- CNKI 正式导入
- Wanfang 正式导入
- VIP 正式导入
- Zotero connector / plugin / sync
- PDF metadata extraction
- OCR
- 公众号投递
- 小程序详情页
- 桌面通知
- 实际 Research Pulse 生成
