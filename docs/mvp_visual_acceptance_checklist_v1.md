# MVP Visual Acceptance Checklist v1

## 目标

本清单用于验收 Design-3 的视觉语言与原型规格，也用于后续前端实现前的视觉对齐检查。

## 整体视觉

- [ ] 整体视觉干净、低干扰。
- [ ] 页面更像科研工作台，而不是后台管理系统。
- [ ] 页面不具有强营销 landing page 气质。
- [ ] 没有大面积高饱和色污染整页。

## 首页

- [ ] 首页第一屏就是今日 Research Pulse。
- [ ] 首页第一屏直接回答：
  - [ ] 今天该看什么
  - [ ] 哪些论文要处理
  - [ ] 下一步做什么
- [ ] 首页不是复杂文献库或总表格。

## 动作层级

- [ ] 每页只有一个主动作。
- [ ] 按钮层级清楚。
- [ ] 次动作没有和主动作争抢注意力。

## 状态视觉

- [ ] warning 不吓人，但可见且可处理。
- [ ] error 清楚且可恢复。
- [ ] `draft / preview / not_sent` 有稳定视觉语义。
- [ ] `draft / preview / not_sent` 不是 success 风格。

## 文案与可读性

- [ ] 没有“已发送成功”“已推送成功”“已登录微信”等误导文案。
- [ ] 中文标题、按钮、说明清楚可读。
- [ ] 论文标题、作者、年份、来源可扫读。
- [ ] 长标题不会被粗暴截断为不可理解状态。

## 组件视觉

- [ ] `PriorityBadge` 的 urgent/high 清楚但不让整页警报化。
- [ ] `MetadataWarningBadge` 像“建议补全”，不是“系统故障”。
- [ ] `DraftStateBanner` 首屏清楚显示状态。
- [ ] `PayloadPreviewPanel` 不喧宾夺主。
- [ ] `EmptyState` 有下一步动作。

## 小程序与渠道边界

- [ ] 小程序详情明确只是 `preview / share-safe`。
- [ ] 公众号页面明确只是 `draft / not_sent`。
- [ ] 桌面通知页面明确只是 `draft / not_sent`。
- [ ] 不出现真实发送、真实推送、微信登录、支付、订阅消息、小程序码等能力暗示。

## 技术边界

- [ ] 本轮只有文档变更。
- [ ] 没有 frontend 变更。
- [ ] 没有 backend 变更。
- [ ] 没有 migration 变更。
- [ ] 没有 dependency 变更。
- [ ] 没有恢复 admin preset / report / print / registry 旧轨道。

## Design-3 通过标准

只有当以下条件同时满足，Design-3 才算通过：

1. 视觉语言清楚。
2. 设计 tokens 完整。
3. 组件视觉规则清楚。
4. 可点击原型路径完整。
5. 响应式与可读性规则清楚。
6. 没有跨到前端或 backend 实现层。
