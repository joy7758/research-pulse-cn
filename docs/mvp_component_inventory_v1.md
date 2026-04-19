# MVP Component Inventory v1

## 目标

本文件定义 MVP 的组件清单，但只写产品规格，不写实现代码。

组件目标是帮助后续：

- 做 wireframe 到前端实现的映射
- 避免重复命名
- 避免页面组件失控扩张

## 组件列表

## 1. AppShell

- 用途：
  - 承载全局布局
- 主要字段：
  - `current_page`
  - `page_title`
  - `global_status`
- 状态：
  - default
  - loading
- 主动作：
  - 无
- 适用页面：
  - 全部页面
- 中文文案注意事项：
  - 不用“控制台”“后台”这类运维词

## 2. LeftNav

- 用途：
  - 一级导航
- 主要字段：
  - `nav_items`
  - `active_item`
- 状态：
  - default
  - collapsed
- 主动作：
  - 切换页面
- 适用页面：
  - 全部页面
- 中文文案注意事项：
  - 优先“今日 Pulse”“导入”“论文进度”

## 3. TopStatusBar

- 用途：
  - 展示页面标题、日期、生成时间、状态
- 主要字段：
  - `title`
  - `subtitle`
  - `generated_at`
  - `delivery_state`
- 状态：
  - default
  - loading
  - draft
  - preview
- 主动作：
  - 触发当前页主动作入口
- 适用页面：
  - 首页、Pulse、草稿、预览页
- 中文文案注意事项：
  - 必须显式出现“草稿”“预览”“未发送”

## 4. PulseSummaryCard

- 用途：
  - 展示今日概览统计
- 主要字段：
  - `high_priority_count`
  - `next_action_count`
  - `metadata_attention_count`
  - `triage_count`
- 状态：
  - default
  - empty
  - warning
- 主动作：
  - 进入对应列表
- 适用页面：
  - 首页
- 中文文案注意事项：
  - 先写结论，再写数量

## 5. PulseSection

- 用途：
  - 展示 Research Pulse 中的一个 section
- 主要字段：
  - `section_id`
  - `title`
  - `description`
  - `items`
  - `empty_reason`
- 状态：
  - default
  - empty
  - warning
- 主动作：
  - 查看该 section 详情
- 适用页面：
  - 首页
  - Research Pulse 详情
- 中文文案注意事项：
  - section 标题必须短且工作导向

## 6. PaperCard

- 用途：
  - 展示单篇论文摘要卡片
- 主要字段：
  - `title`
  - `authors`
  - `year`
  - `venue`
  - `reading_status`
  - `priority`
  - `next_action`
- 状态：
  - default
  - warning
  - selected
- 主动作：
  - 打开详情侧栏
- 适用页面：
  - 首页
  - 论文进度页
  - Pulse 详情页
- 中文文案注意事项：
  - 不要把卡片写成数据库行

## 7. PaperProgressBadge

- 用途：
  - 展示阅读状态或研究阶段
- 主要字段：
  - `reading_status`
  - `research_stage`
- 状态：
  - default
  - highlighted
- 主动作：
  - 无
- 适用页面：
  - PaperCard
  - Drawer
- 中文文案注意事项：
  - 用“待读”“精读中”，不要直接暴露枚举值

## 8. PriorityBadge

- 用途：
  - 展示优先级
- 主要字段：
  - `priority`
- 状态：
  - low
  - normal
  - high
  - urgent
- 主动作：
  - 无
- 适用页面：
  - PaperCard
  - Drawer
  - PulseSection
- 中文文案注意事项：
  - `high` 和 `urgent` 应更醒目，但文案仍用中文

## 9. MetadataWarningBadge

- 用途：
  - 提示元数据待补全
- 主要字段：
  - `warnings`
  - `severity`
- 状态：
  - warning
  - hidden
- 主动作：
  - 查看问题详情
- 适用页面：
  - PaperCard
  - 导入预览页
  - 论文详情侧栏
- 中文文案注意事项：
  - 要写可操作建议，不写技术异常名

## 10. NextActionCard

- 用途：
  - 突出展示下一步动作
- 主要字段：
  - `paper_title`
  - `next_action`
  - `priority`
  - `deadline_hint`
- 状态：
  - default
  - warning
- 主动作：
  - 继续处理
- 适用页面：
  - 首页
  - Pulse 详情页
- 中文文案注意事项：
  - 语句应短，动词开头更好

## 11. ImportDropzone

- 用途：
  - 接收拖入文件或文件夹
- 主要字段：
  - `accepted_types`
  - `last_drop_summary`
- 状态：
  - idle
  - drag_over
  - loading
  - error
- 主动作：
  - 开始识别
- 适用页面：
  - 导入页
- 中文文案注意事项：
  - 不要求用户先懂格式

## 12. PasteImportPanel

- 用途：
  - 粘贴 BibTeX / RIS / CSL JSON / 表格文本
- 主要字段：
  - `placeholder_text`
  - `pasted_length`
- 状态：
  - empty
  - filled
  - error
- 主动作：
  - 开始识别
- 适用页面：
  - 导入页
- 中文文案注意事项：
  - 占位文案要明确可粘贴内容

## 13. ImportPreviewTable

- 用途：
  - 展示导入预览记录
- 主要字段：
  - `records`
  - `can_commit`
  - `warnings`
  - `errors`
- 状态：
  - default
  - warning
  - error
- 主动作：
  - 确认导入可导入记录
- 适用页面：
  - 导入预览页
- 中文文案注意事项：
  - 列标题应面向用户字段，不是内部 schema

## 14. ImportIssueList

- 用途：
  - 集中展示问题记录
- 主要字段：
  - `issue_type`
  - `message`
  - `record_index`
- 状态：
  - warning
  - error
  - empty
- 主动作：
  - 查看问题记录
- 适用页面：
  - 导入预览页
  - 导入完成页
- 中文文案注意事项：
  - 明确“可继续 / 暂不可继续”

## 15. PaperDetailDrawer

- 用途：
  - 在主流程中查看和更新论文详情
- 主要字段：
  - `paper_id`
  - `title`
  - `authors`
  - `year`
  - `venue`
  - `reading_status`
  - `research_stage`
  - `priority`
  - `next_action`
  - `user_note`
  - `metadata_warnings`
- 状态：
  - closed
  - open
  - loading
  - error
- 主动作：
  - 保存进度
- 适用页面：
  - 论文进度页
  - Pulse 详情页
- 中文文案注意事项：
  - 不要让用户离开当前页面

## 16. DraftStateBanner

- 用途：
  - 显示当前结果是草稿或预览
- 主要字段：
  - `delivery_state`
  - `notes`
- 状态：
  - draft
  - preview
  - not_sent
- 主动作：
  - 无
- 适用页面：
  - 公众号草稿页
  - 桌面通知草稿页
  - 小程序详情预览页
- 中文文案注意事项：
  - 必须避免误导用户“已发送”

## 17. CopyActionBar

- 用途：
  - 承载复制类次级操作
- 主要字段：
  - `copy_targets`
- 状态：
  - default
  - disabled
  - success_hint
- 主动作：
  - 复制当前主内容
- 适用页面：
  - 公众号草稿页
  - 桌面通知草稿页
  - 小程序详情页
- 中文文案注意事项：
  - 按钮文案直接说复制什么

## 18. PayloadPreviewPanel

- 用途：
  - 展示结构化 payload 预览
- 主要字段：
  - `payload_preview`
  - `redacted_fields`
- 状态：
  - default
  - preview
  - warning
- 主动作：
  - 复制 payload
- 适用页面：
  - 公众号草稿页
  - 桌面通知草稿页
  - 小程序详情预览页
- 中文文案注意事项：
  - 只展示用户可理解字段，不放 debug 噪音

## 19. ShareCardPreview

- 用途：
  - 展示分享卡片摘要
- 主要字段：
  - `title`
  - `summary`
  - `path`
  - `share_safe`
- 状态：
  - default
  - preview
- 主动作：
  - 复制 share card
- 适用页面：
  - 小程序详情预览页
- 中文文案注意事项：
  - 短、清楚、适合转发前预览

## 20. MiniProgramPathPreview

- 用途：
  - 展示 path placeholder
- 主要字段：
  - `path`
  - `detail_type`
- 状态：
  - default
  - preview
- 主动作：
  - 复制 path
- 适用页面：
  - 小程序详情预览页
- 中文文案注意事项：
  - 要明确这是占位 path，不是真实小程序发布态

## 21. EmptyState

- 用途：
  - 展示当前无数据但并非错误
- 主要字段：
  - `title`
  - `message`
  - `next_step`
- 状态：
  - empty
- 主动作：
  - 回到当前页主动作
- 适用页面：
  - 全部页面
- 中文文案注意事项：
  - 不责怪用户，不留空白

## 22. WarningState

- 用途：
  - 告诉用户可以继续，但有问题需要处理
- 主要字段：
  - `warnings`
  - `recommended_actions`
- 状态：
  - warning
- 主动作：
  - 继续主流程或处理问题
- 适用页面：
  - 导入预览
  - 导入完成
  - 论文详情
  - Pulse
- 中文文案注意事项：
  - 先说还能不能继续，再说为什么

## 23. ErrorState

- 用途：
  - 展示当前无法继续
- 主要字段：
  - `title`
  - `message`
  - `retry_action`
- 状态：
  - error
- 主动作：
  - 重试
- 适用页面：
  - 全部页面
- 中文文案注意事项：
  - 不显示原始异常栈

## 24. LoadingState

- 用途：
  - 展示生成中或加载中
- 主要字段：
  - `loading_message`
- 状态：
  - loading
- 主动作：
  - 无
- 适用页面：
  - 全部页面
- 中文文案注意事项：
  - 说明正在做什么，不要只显示空转

## 组件总规则

1. 组件命名用英文，用户文案用中文。
2. 组件优先承载“工作流意义”，不要优先承载技术对象。
3. 组件状态必须兼容 `draft / preview / not_sent / warning / error`。
4. 组件默认不暴露 raw payload、debug 信息或未实现平台能力。
