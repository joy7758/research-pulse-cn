你正在处理仓库 research-pulse-cn。

当前基线：
235455f demo: add mvp fixture pack and local demo script

当前阶段：
Frontend-1：minimal web shell

目标：
只做最小 Web UI 骨架，用来展示已经冻结的 MVP 主链路。

本轮最多只做 3 个页面：

1. 首页 / 今日 Research Pulse
2. 导入 / 导入预览
3. Research Pulse 详情

必须先阅读：

- README.md
- docs/api_contract_mvp_v1.md
- docs/schema_contract_mvp_v1.md
- docs/error_warning_contract_mvp_v1.md
- docs/mvp_demo_fixture_pack_v1.md
- docs/mvp_local_demo_script_v1.md
- docs/mvp_interface_principles_v1.md
- docs/mvp_wireframes_v1.md
- docs/mvp_component_inventory_v1.md
- docs/mvp_interaction_spec_v1.md
- docs/mvp_visual_language_v1.md
- docs/mvp_component_visual_rules_v1.md
- docs/frontend_technical_feasibility_review_v1.md
- docs/frontend_mvp_scope_v1.md
- docs/frontend_api_consumption_plan_v1.md
- docs/frontend_demo_data_mapping_v1.md
- docs/frontend_component_mapping_v1.md
- docs/frontend_implementation_sequence_v1.md
- docs/frontend_acceptance_checklist_v1.md

实现边界：

- 只做最小 Web shell
- 不做完整前端产品
- 不做登录
- 不做 admin
- 不做真实微信
- 不做真实小程序
- 不做真实桌面通知
- 不做真实文件上传复杂工程
- 不做 CNKI / Wanfang / VIP
- 不做 Zotero plugin / connector / sync
- 不做复杂状态管理
- 不做复杂筛选
- 不做完整视觉系统

数据策略：

1. 先支持 demo JSON mock mode
2. 再预留 API mode
3. 不修改 backend contract

mock mode 至少支持读取：

- import_preview.json
- import_commit.json
- paper_progress_summary.json
- research_pulse.json

API mode 预留这些 endpoint：

- POST /papers/import-preview
- POST /papers/import-commit
- GET /papers/progress/summary
- GET /papers/progress/pulse-context
- POST /pulse/papers/daily

页面要求：

## 页面 1：首页 / 今日 Research Pulse

- 今日概览
- 今日重点论文
- 下一步动作
- 元数据待补全
- 新导入待筛选
- 主动作：刷新 / 生成今日 Pulse
- 次动作：导入论文

## 页面 2：导入 / 导入预览

- 拖入或粘贴入口
- import preview 统计
- warning / error 列表
- 主动作：确认导入可导入记录
- 次动作：只看问题记录

## 页面 3：Research Pulse 详情

- sections
- items
- 主动作：生成公众号摘要草稿
- 次动作：桌面通知草稿 / 小程序详情预览

设计要求：

- 中文界面
- 每页一个主动作
- 首页不是文献库，是今日 Research Pulse
- warning/error 变成建议
- `draft / preview / not_sent` 必须明确
- 不暴露技术字段
- 不要做成后台管理系统

实现建议：

- 优先复用仓库已有轻量 web shell 技术栈风格
- 保持组件数量最少
- 先把 mock mode 跑通
- 再考虑 real API mode

最终报告必须使用中文，包含：

1. 3 个页面实际落在哪些文件
2. 使用了哪些 mock JSON
3. 是否保留了 API mode 入口
4. 是否保持每页一个主动作
5. 是否明确 `draft / preview / not_sent`
6. 是否没有新增真实微信 / 小程序 / 桌面通知能力
7. 是否没有新增 admin / 登录 / 复杂后台

