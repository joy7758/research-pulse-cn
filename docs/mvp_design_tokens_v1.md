# MVP Design Tokens v1

## 目标

本文件定义 documentation-only 的设计 token 规格。

这些 token 用于未来前端实现对齐同一套视觉语言，但本阶段不提供任何框架代码。

## 设计原则

- 低饱和
- 高可读
- 中文优先
- 视觉克制
- 状态明确
- 不制造发送或发布错觉

## 色彩 Tokens

## 背景

### `background.page`

- 用途：页面主背景
- 建议语义：非常浅、低干扰、接近纸面感
- 要求：
  - 不偏营销色
  - 不做强对比大底

### `background.surface`

- 用途：卡片、面板、drawer 内容区
- 建议语义：比页面背景更实一点，但仍保持轻
- 要求：
  - 适合长期阅读

### `background.subtle`

- 用途：次级区块、过滤条、状态容器
- 建议语义：轻微分层，不形成沉重块感

## 文本

### `text.primary`

- 用途：页面主标题、正文核心内容
- 要求：
  - 高对比
  - 支持中文长时间阅读

### `text.secondary`

- 用途：次级说明、作者信息、来源信息
- 要求：
  - 清晰可读
  - 不能过浅

### `text.muted`

- 用途：注释、状态补充、辅助说明
- 要求：
  - 可弱化，但不能丢失可读性

## 边框

### `border.default`

- 用途：卡片、面板、输入区、表格边界
- 要求：
  - 轻
  - 稳定
  - 不要厚重

### `border.subtle`

- 用途：轻分隔线、区块内分界
- 要求：
  - 只提供结构，不抢视觉焦点

## 交互强调

### `accent.primary`

- 用途：主按钮、主链接、主要焦点
- 要求：
  - 清晰但不刺眼
  - 不要大面积使用

### `accent.primary.subtle`

- 用途：主按钮悬停、选中容器、轻强调背景
- 要求：
  - 作为辅助强调存在

## 状态色

### `status.success`

- 用途：保存完成、可用状态、成功反馈
- 要求：
  - 稳定
  - 不抢主内容

### `status.warning`

- 用途：建议补全、问题提醒、可继续的异常
- 要求：
  - 可见
  - 不刺眼
  - 不能做成严重故障红

### `status.error`

- 用途：当前不可继续的错误
- 要求：
  - 明确
  - 仅局部使用
  - 不污染整页

### `status.info`

- 用途：说明、帮助、提示类信息
- 要求：
  - 中性
  - 清楚

### `status.draft`

- 用途：公众号草稿、桌面通知草稿
- 要求：
  - 与 success 明确区分
  - 视觉上偏中性，不像成功态

### `status.preview`

- 用途：小程序详情预览、payload 预览
- 要求：
  - 与 draft 可区分
  - 传达“仅预览，不代表发布”

### `status.not_sent`

- 用途：未发送、未推送、未发布说明
- 要求：
  - 要醒目到能避免误解
  - 但不形成“失败”印象

## 优先级色

### `priority.low`

- 用途：低优先级 badge
- 要求：
  - 轻量、克制

### `priority.normal`

- 用途：默认优先级 badge
- 要求：
  - 中性

### `priority.high`

- 用途：高优先级 badge
- 要求：
  - 明显但不造成警报感

### `priority.urgent`

- 用途：紧急优先级 badge
- 要求：
  - 最明显
  - 仅在 badge、局部标识中使用
  - 不能让整页变红

## 字体层级 Tokens

### `typography.display`

- 用途：首页大标题、页面主标题
- 要求：
  - 中文清楚
  - 长标题可换行
  - 不追求夸张展示感

### `typography.page_title`

- 用途：普通页面主标题
- 要求：
  - 稳定
  - 有重量感但不过重

### `typography.section_title`

- 用途：section 标题
- 要求：
  - 比正文显著，但不压制页面标题

### `typography.card_title`

- 用途：论文标题、卡片标题
- 要求：
  - 可支持 2 到 3 行换行
  - 适合中英文混排

### `typography.body`

- 用途：正文、说明
- 要求：
  - 行高舒适
  - 中文阅读优先

### `typography.body_small`

- 用途：次级说明、作者/来源信息
- 要求：
  - 清楚
  - 不能太小

### `typography.caption`

- 用途：辅助标签、时间、状态说明
- 要求：
  - 可弱化，但不能丢失可读性

### `typography.badge`

- 用途：状态 badge、优先级 badge
- 要求：
  - 短文本清楚
  - 中英文都可读

### `typography.code`

- 用途：payload preview、path placeholder
- 要求：
  - 与正文有明显区分
  - 不抢整体视觉主导

## 间距 Tokens

### `spacing.4`

- 用途：极近文本与 icon 间距

### `spacing.8`

- 用途：小型组件内部间距

### `spacing.12`

- 用途：badge、字段组、轻量卡片内容间距

### `spacing.16`

- 用途：默认组件内部边距

### `spacing.24`

- 用途：卡片与区块之间的标准间距

### `spacing.32`

- 用途：大区块之间的页面节奏

### `spacing.48`

- 用途：首页关键 section 之间的宽松留白

### 间距要求

- 页面留白足够
- 卡片之间层级清楚
- 信息密集区仍能阅读

## 圆角 / 阴影 / 边框

### `radius.small`

- 用途：badge、轻量按钮、输入框

### `radius.medium`

- 用途：卡片、面板、drawer

### `radius.large`

- 用途：大容器、拖拽区、突出主卡片

### `shadow.none`

- 用途：最基础层，不强调浮起感

### `shadow.subtle`

- 用途：卡片与页面区分、drawer 与主区分
- 要求：
  - 轻
  - 不做厚重投影

### `border.default`

- 用途：默认容器边界
- 要求：
  - 比阴影更重要
  - 先靠边框定义结构，再少量辅以阴影

## 密度 Tokens

### `density.comfortable`

- 用途：
  - 首页
  - Pulse 详情
  - 公众号草稿页
- 特征：
  - 更宽松
  - 决策型阅读

### `density.compact`

- 用途：
  - 论文列表
  - 导入预览表
- 特征：
  - 信息更多
  - 但仍不能像后台管理表

### `density.reading`

- 用途：
  - 论文详情
  - 小程序详情预览
  - payload preview 外层说明区
- 特征：
  - 适合较长中文文本

## Token 使用规则

1. token 优先按语义命名，不按具体色值命名。
2. `draft / preview / not_sent` 必须有稳定 token，不借用 success。
3. `urgent` 只用于局部，不污染页面整体。
4. `warning` 用于建议补全，不营造崩溃感。
5. 中文阅读优先于“设计感炫技”。
