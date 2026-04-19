# 基于已导入论文生成 Research Pulse v1

## Pivot-5 的目标

Pivot-5 的目标不是投递，而是基于 Pivot-2 到 Pivot-4 已经沉淀下来的论文导入与论文进度上下文，生成一个**结构化、可解释、可复用的 Research Pulse 草稿**。

本阶段强调：

- 输入来自已导入论文和进度工作台
- 输出是结构化草稿，不是发送任务
- 中文内容使用 deterministic / template-based 规则生成
- 不调用外部 LLM
- 不访问外部网络
- 不接公众号、小程序、桌面通知

## Research Pulse Generation Flow

1. Pivot-2 解析多种导入格式并归一化论文元数据。
2. Pivot-3 将选中的导入记录写入现有 `PaperProfile`。
3. Pivot-4 基于 `PaperProfile` 构建论文进度工作台与 `pulse context`。
4. Pivot-5 读取 progress workbench 的论文进度项和 pulse context。
5. 根据确定性排序与中文模板规则，生成 Research Pulse draft。

## 输入来源：Imported Papers + Progress Context

Pivot-5 的输入主要来自两部分：

- `PaperProgressWorkbenchService.list_papers_for_pulse_context(...)`
- `PaperProgressWorkbenchService.get_progress_context_for_pulse(...)`

也就是说，Pulse draft 不再依赖外部检索或外部模型，而是直接消费：

- 已导入论文
- 阅读状态
- 研究阶段
- 优先级
- 下一步动作
- 元数据缺失提醒
- 导入来源格式

## ResearchPulseRequest 字段

当前请求结构至少包括：

- `user_id`
- `pulse_date`
- `timezone`
- `max_items_per_section`
- `include_low_priority`
- `include_archived`
- `source_format_filter`
- `dry_run`

说明：

- `timezone` 默认 `Asia/Shanghai`
- `include_low_priority=false` 时，低优先级论文不会进入“今日重点论文” section
- `include_archived=false` 时，默认排除 `archived` 阅读状态
- `dry_run` 当前只是显式说明“本轮不落库”，即使传 `false` 也不会持久化

## ResearchPulseResult 字段

当前结果结构至少包括：

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

## ResearchPulseSection 字段

每个 section 至少包括：

- `section_id`
- `title`
- `description`
- `items`
- `empty_reason`

## ResearchPulseItem 字段

每个 item 至少包括：

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

## Section 设计

Pivot-5 当前固定输出这五个 section：

### 1. 今日重点论文

适合优先推进的论文，重点参考：

- `priority = urgent / high`
- 是否有 `next_action`
- 是否处于 `reading / reviewing / relevant`

### 2. 继续阅读与分析

面向研究生、博士生日常阅读推进，重点覆盖：

- `reading_status = skimming / reading`
- `research_stage = reviewing / relevant`

### 3. 下一步动作

直接整理当前已经明确写下 `next_action` 的论文。

### 4. 元数据待补全

提醒导入后的记录还缺少：

- 作者
- 年份
- 期刊 / 会议来源
- DOI
- 导入来源格式

尤其适合 PDF 文件夹占位导入后的补全场景。

### 5. 新导入待筛选

帮助用户把刚导入但还没进入研究流程的论文从 `inbox / triage` 往前推进。

## Item 排序规则

本阶段只做轻量、可解释、确定性的排序。

核心排序因子：

- `priority`: `urgent > high > normal > low`
- 有 `next_action` 优先
- `reading_status`: `reading > skimming > unread > read > archived`
- `research_stage`: `reviewing > relevant > triage > inbox > cited > implemented > parked`
- 最近更新或最近触达优先
- `title` 和 `paper_id` 作为最终稳定兜底排序

注意：

- 同样输入下，输出顺序稳定
- 不做 embedding
- 不做相似度算法
- 不做外部推荐

## 中文内容生成边界

Pivot-5 只做基于现有字段的中文模板生成。

允许：

- 中文标题
- 中文 section 标题
- 中文 summary
- 中文 reason
- 中文 suggested_action

不允许：

- 伪造论文摘要
- 假装已经阅读全文
- 根据不存在的 abstract / note 编造内容
- 调用外部模型生成自由文本

因此所有中文内容都必须能回溯到已有字段，例如：

- `priority`
- `reading_status`
- `research_stage`
- `next_action`
- `warnings`

## 持久化策略

Pivot-5 当前**不新增持久化结构**。

采用策略：

- 复用现有 `PaperProfile` 作为输入来源
- 复用现有 `PaperProgressWorkbenchService` 作为上下文层
- 新增 `ResearchPulseService` 只生成 draft
- 不落 `PulseJob`
- 不落 `PulseCard`
- 不创建 delivery / notification / schedule 记录

这样可以保持本阶段边界明确：**只生成草稿，不投递，不调度**。

## 与 Pivot-4 的关系

Pivot-4 提供的是论文进度工作台基础层。

Pivot-5 直接消费 Pivot-4 的：

- `progress item`
- `summary`
- `pulse context`

因此 Pivot-5 不是替代 Pivot-4，而是把 Pivot-4 已经整理好的研究上下文转成每日科研摘要草稿。

## 与 Pivot-6 / Pivot-7 / Pivot-8 的边界

Pivot-5 到此为止，不继续：

- 微信公众号投递
- 小程序详情页
- 桌面通知
- 定时调度
- 订阅策略扩展

这些都留给后续阶段：

- Pivot-6：微信公众号每日摘要 MVP
- Pivot-7：桌面通知 MVP
- Pivot-8：小程序详情 MVP

## 中国市场使用场景

Pivot-5 面向中国科研用户的常见场景：

- 研究生每天先看“今日重点论文”和“继续阅读与分析”
- 博士生先执行“下一步动作”，再补齐“元数据待补全”
- 导师或课题组可以快速识别当前最值得推进的论文
- 批量表格导入之后，可以通过 Pulse 草稿快速看到哪些论文还在 `inbox / triage`
- PDF 文件夹导入后，如果元数据不完整，会直接进入“元数据待补全”

## 示例

标题示例：

- `2026-04-19 科研 Pulse 草稿`

摘要示例：

- `今日已从 8 篇已导入论文中整理出 2 篇重点推进论文，3 篇继续阅读与分析论文，2 项明确的下一步动作，另有 1 条元数据补全提醒。`

reason 示例：

- `该论文当前标记为 high 优先级，且已经定义下一步动作，目前处于精读中，适合作为今天的重点推进对象。`
- `该记录仍缺少作者、年份、DOI 等关键元数据，后续筛选和引用追踪会受限。`

suggested_action 示例：

- `先整理方法对比表`
- `先补全作者、年份、期刊或 DOI 等基础元数据。`

## 已知限制

- 仍然没有前端 UI
- 仍然不投递
- 仍然不调度
- 仍然不做外部检索
- 仍然不做外部模型调用
- section 仍然是固定模板，不支持用户自定义
- `dry_run` 当前只是显式说明“本轮不持久化”

## 暂缓事项

- 微信公众号投递
- 小程序详情页
- 桌面通知
- 定时任务
- 外部检索
- 外部 LLM 调用
- CNKI 正式导入
- Wanfang 正式导入
- VIP 正式导入
- Zotero connector / plugin / sync
- PDF metadata extraction
- OCR
- 前端 UI
