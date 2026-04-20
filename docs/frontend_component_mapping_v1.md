# Frontend Component Mapping v1

## 目标

本文件把 Design-2 / Design-3 的组件清单映射到 Frontend-1 的最小实现范围。

## Frontend-1 必需组件

## 1. AppShell

- 来源文档：
  - `docs/mvp_component_inventory_v1.md`
  - `docs/mvp_component_visual_rules_v1.md`
- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
  - 导入 / 导入预览
  - Pulse 详情
- 最小 props / data fields：
  - `currentPage`
  - `pageTitle`
  - `pageState`
- 暂缓内容：
  - 多层 workspace 结构

## 2. LeftNav

- 首版是否需要：
  - 需要
- 使用页面：
  - 全部首版页面
- 最小 props：
  - `items`
  - `activeKey`
- 暂缓内容：
  - 深层分组导航

## 3. TopStatusBar

- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
  - 导入 / 导入预览
  - Pulse 详情
- 最小 props：
  - `title`
  - `subtitle`
  - `generatedAt`
  - `deliveryState`
  - `primaryAction`
- 暂缓内容：
  - 全局次级工具条

## 4. PulseSummaryCard

- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
- 最小 props：
  - `label`
  - `count`
  - `hint`

## 5. PulseSection

- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
  - Pulse 详情
- 最小 props：
  - `sectionId`
  - `title`
  - `description`
  - `items`
  - `emptyReason`

## 6. PaperCard

- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
  - Pulse 详情
- 最小 props：
  - `title`
  - `authors`
  - `year`
  - `venue`
  - `readingStatus`
  - `priority`
  - `nextAction`

## 7. PaperProgressBadge

- 首版是否需要：
  - 需要
- 使用页面：
  - PaperCard
- 最小 props：
  - `readingStatus`
  - `researchStage`

## 8. PriorityBadge

- 首版是否需要：
  - 需要
- 使用页面：
  - PaperCard
  - PulseSection
- 最小 props：
  - `priority`

## 9. MetadataWarningBadge

- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
  - 导入预览页
  - Pulse 详情页
- 最小 props：
  - `warnings`

## 10. NextActionCard

- 首版是否需要：
  - 需要
- 使用页面：
  - 首页
  - Pulse 详情页
- 最小 props：
  - `paperTitle`
  - `nextAction`
  - `priority`

## 11. ImportDropzone

- 首版是否需要：
  - 需要
- 使用页面：
  - 导入页
- 最小 props：
  - `acceptedFormats`
  - `disabled`
- 暂缓内容：
  - 真实拖入文件复杂处理

## 12. PasteImportPanel

- 首版是否需要：
  - 需要
- 使用页面：
  - 导入页
- 最小 props：
  - `placeholder`
  - `value`

## 13. ImportPreviewTable

- 首版是否需要：
  - 需要
- 使用页面：
  - 导入预览页
- 最小 props：
  - `records`
  - `validCount`
  - `warningCount`
  - `errorCount`

## 14. ImportIssueList

- 首版是否需要：
  - 需要
- 使用页面：
  - 导入预览页
- 最小 props：
  - `issues`
  - `filter`

## 15. DraftStateBanner

- 首版是否需要：
  - 需要
- 使用页面：
  - Pulse 详情页中草稿占位区
- 最小 props：
  - `state`
  - `message`

## 16. EmptyState

- 首版是否需要：
  - 需要
- 使用页面：
  - 全部首版页面
- 最小 props：
  - `title`
  - `description`
  - `primaryActionLabel`

## 17. WarningState

- 首版是否需要：
  - 需要
- 使用页面：
  - 导入预览
  - Pulse 详情
- 最小 props：
  - `title`
  - `recommendation`

## 18. ErrorState

- 首版是否需要：
  - 需要
- 使用页面：
  - 全部首版页面
- 最小 props：
  - `title`
  - `nextStep`

## 19. LoadingState

- 首版是否需要：
  - 需要
- 使用页面：
  - 全部首版页面
- 最小 props：
  - `label`

## Frontend-1 暂缓组件

以下组件明确暂缓，不进入首版：

- `PaperDetailDrawer`
- `PayloadPreviewPanel`
- `ShareCardPreview`
- `MiniProgramPathPreview`
- `CopyActionBar`
- `SettingsForm`

## 暂缓原因

- 这些组件更适合第二阶段页面扩展
- 首版只做 3 个页面，不需要为了后续渠道页把结构提前做复杂
- 先把首页、导入、Pulse 三页做顺，再扩展细页

