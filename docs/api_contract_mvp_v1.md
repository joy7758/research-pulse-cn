# API Contract MVP v1

## 目标

本文件冻结当前 China-first Research Pulse MVP 主链路的 API 契约。

当前冻结对象只覆盖这条 backend 主链路：

```text
import formats
-> import preview
-> import commit
-> paper progress
-> Research Pulse draft
-> official-account daily summary draft
-> desktop notification draft
-> mini-program detail preview
```

本文件的重点不是描述内部实现，而是固定：

- 当前可依赖的 API 路径
- 每个 endpoint 的用途
- request / response schema 名称
- draft / preview / not_sent 边界
- 当前不应被误解为“真实发送”或“真实平台接入”的地方

## MVP API 路径清单

### 1. 用户与导入入口

#### `POST /users`
- 用途：
  - 创建研究用户档案，供后续导入、进度和 Pulse 流程使用
- request schema：
  - `UserProfileCreate`
- response schema：
  - `UserProfileRead`
- 外部行为：
  - 真实写库
  - 不触发外部网络

#### `POST /papers/import-preview`
- 用途：
  - 把 `CSL JSON / BibTeX / RIS / 表格类文本 / PDF folder placeholder` 解析成 import preview
- request schema：
  - `PaperImportPreviewCreateRequest`
- response schema：
  - `PaperImportPreviewResult`
- 外部行为：
  - 不提交论文
  - 不触发真实发送
  - 不访问外部网络

#### `POST /papers/import-commit`
- 用途：
  - 提交选中的 preview records，生成可管理的 paper records
- request schema：
  - `PaperImportCommitRequest`
- response schema：
  - `PaperImportCommitResult`
- 外部行为：
  - 会写入现有 `PaperProfile`
  - 不触发微信公众号、桌面通知、小程序
  - 不访问外部网络

### 2. 论文进度工作台

#### `GET /papers/progress`
- 用途：
  - 返回论文进度列表
- request 形态：
  - query params：`user_id`, `reading_status`, `research_stage`, `priority`, `keyword`, `has_next_action`, `source_format`, `limit`, `offset`
- response schema：
  - `PaperProgressListResponse`
- 外部行为：
  - 只读
  - 不触发真实发送

#### `GET /papers/progress/summary`
- 用途：
  - 返回论文进度 summary
- request 形态：
  - query params 与 `/papers/progress` 对齐
- response schema：
  - `PaperProgressSummaryRead`
- 外部行为：
  - 只读

#### `GET /papers/progress/pulse-context`
- 用途：
  - 返回 Pulse 使用的轻量进度上下文
- request 形态：
  - query params：`user_id`, `limit`
- response schema：
  - `PaperProgressPulseContextRead`
- 外部行为：
  - 只读
  - 不生成实际 Pulse 内容

#### `GET /papers/{paper_id}/progress`
- 用途：
  - 返回单篇论文进度详情
- response schema：
  - `PaperProgressItemRead`
- 外部行为：
  - 只读

#### `PATCH /papers/{paper_id}/progress`
- 用途：
  - 更新阅读状态、研究阶段、优先级、下一步动作、轻量笔记和 tags
- request schema：
  - `PaperProgressUpdateRequest`
- response schema：
  - `PaperProgressItemRead`
- 外部行为：
  - 真实写入现有 paper progress 状态
  - 不触发真实发送

### 3. Research Pulse 草稿

#### `POST /pulse/papers/daily`
- 用途：
  - 基于已导入论文和论文进度生成每日 Research Pulse 草稿
- request schema：
  - `ResearchPulseRequest`
- response schema：
  - `ResearchPulseResult`
- draft 语义：
  - deterministic / template-based 草稿
  - `dry_run=true` 是当前推荐调用方式
- 外部行为：
  - 不调用外部 LLM
  - 不触发真实发送
  - 不访问外部网络

### 4. 公众号每日摘要草稿

#### `POST /pulse/papers/official-account/daily-summary`
- 用途：
  - 把 `ResearchPulseResult` 转成公众号每日摘要 draft / payload preview
- request schema：
  - `OfficialAccountDailySummaryRequest`
- response schema：
  - `OfficialAccountDailySummaryResult`
- draft 语义：
  - 只生成 daily summary draft
  - 只生成 `publication_preview` 与 `template_payload_preview`
- 外部行为：
  - 不真实发送
  - 不创建真实 publication job
  - 不调用真实微信 API

### 5. 桌面通知草稿

#### `POST /pulse/papers/desktop-notification/draft`
- 用途：
  - 把 `ResearchPulseResult` 转成桌面通知草稿 / payload preview
- request schema：
  - `DesktopNotificationRequest`
- response schema：
  - `DesktopNotificationResult`
- draft 语义：
  - `delivery_state = draft`
  - 只输出 title / body / actions / deep_link / payload_preview
- 外部行为：
  - 不调用系统通知
  - 不调用 APNs / FCM / Web Push
  - 不创建真实推送任务

### 6. 小程序详情 preview

#### `POST /pulse/papers/mini-program/detail/preview`
- 用途：
  - 生成微信小程序详情页所需的后端 detail payload / preview / share-safe data
- request schema：
  - `MiniProgramDetailRequest`
- response schema：
  - `MiniProgramDetailResult`
- preview 语义：
  - `delivery_state = preview`
  - 只返回 detail payload 和 path placeholder
- 外部行为：
  - 不做真实小程序交互
  - 不做微信登录
  - 不做订阅消息、支付、小程序码

## Endpoint 用途与边界总结

### import preview
- 只负责解析、归一化、验证
- 不写入论文
- 不是真实导入完成

### import commit
- 只负责把可提交记录变成 `PaperProfile`
- 不触发 Pulse、公众号、桌面或小程序

### paper progress
- 只负责研究状态管理
- 不直接生成多端内容

### Research Pulse
- 只负责生成 Research Pulse draft
- 不真实投递
- 不依赖外部模型

### official-account daily summary
- 只生成 draft 和 payload preview
- 不等于公众号真实发送

### desktop notification
- 只生成 draft 和 deep-link placeholder
- 不等于桌面系统通知已发送

### mini-program detail
- 只生成 preview 和 share-safe payload
- 不等于小程序前端已存在或已接入微信能力

## request / response schema 清单

### Import
- `PaperImportPreviewCreateRequest`
- `PaperImportPreviewResult`
- `PaperImportCommitRequest`
- `PaperImportCommitResult`

### Paper progress
- `PaperProgressItemRead`
- `PaperProgressListResponse`
- `PaperProgressUpdateRequest`
- `PaperProgressSummaryRead`
- `PaperProgressPulseContextRead`

### Research Pulse
- `ResearchPulseRequest`
- `ResearchPulseResult`
- `ResearchPulseSection`
- `ResearchPulseItem`

### Official account
- `OfficialAccountDailySummaryRequest`
- `OfficialAccountDailySummaryResult`
- `OfficialAccountDailySummarySection`
- `OfficialAccountDailySummaryItem`

### Desktop
- `DesktopNotificationRequest`
- `DesktopNotificationResult`
- `DesktopNotificationItem`
- `DesktopNotificationAction`

### Mini program
- `MiniProgramDetailRequest`
- `MiniProgramDetailResult`
- `MiniProgramDetailCard`
- `MiniProgramDetailItem`
- `MiniProgramDetailAction`
- `MiniProgramShareCard`
- `MiniProgramNavigation`

## 禁止误解

- official-account endpoint 只生成 draft，不真实发送
- desktop endpoint 只生成 draft，不触发系统通知
- mini-program endpoint 只生成 preview，不做真实小程序交互
- Research Pulse 是 deterministic / template-based，不调用外部 LLM
- import 不做 `CNKI / Wanfang / VIP` 正式集成
- Zotero 只是参考策略，不做 plugin / connector / sync
- 当前 MVP 不应被解释为：
  - 已接通真实微信公众号 API
  - 已接通真实桌面通知
  - 已接通真实微信小程序 frontend
  - 已接通外部模型服务
