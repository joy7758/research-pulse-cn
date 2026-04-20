# Frontend Demo Data Mapping v1

## 目标

本文件定义 Demo-1 输出文件如何映射到 Frontend-1 页面和组件。

## 总原则

1. 前端第一版先直接消费 demo JSON。  
2. 不要把 `/tmp` 输出直接纳入版本控制。  
3. 页面先围绕稳定 payload 建立，不要凭空造数据结构。  
4. 如果后续需要 curated demo output，应单独评估，本轮不提交大量生成产物。

## 文件到页面的映射

## `import_preview.json`

对应页面：

- 导入预览页

对应内容：

- 可导入数量
- warning 数量
- error 数量
- 记录列表
- 问题记录列表

## `import_commit.json`

对应页面：

- 导入完成状态

对应内容：

- `committed_count`
- `skipped_count`
- `failed_count`
- 每条记录结果

## `paper_progress_summary.json`

对应页面：

- 首页统计区
- 进度摘要卡片

对应内容：

- 总论文数
- 阅读中数量
- 高优先级数量
- 紧急数量
- 已写下一步动作数量

## `research_pulse.json`

对应页面：

- 首页
- Research Pulse 详情页

对应内容：

- title
- summary
- sections
- warnings
- dry_run

这是 Frontend-1 的核心数据文件。

## `official_account_daily_summary.json`

对应页面：

- 后续公众号草稿页

在 Frontend-1 中的用途：

- 可以先不单独做页面
- 可作为 Pulse 详情页中的后续能力占位依据

## `desktop_notification.json`

对应页面：

- 后续桌面通知草稿页

在 Frontend-1 中的用途：

- 可作为 Pulse 详情页中的后续能力占位依据

## `mini_program_daily_pulse_detail.json`

对应页面：

- 后续小程序详情预览页

在 Frontend-1 中的用途：

- 作为后续 detail payload 样本
- 不进入首版核心页面

## `mini_program_next_actions_detail.json`

对应页面：

- 后续小程序“下一步动作详情”预览

## `mini_program_metadata_attention_detail.json`

对应页面：

- 后续小程序“元数据待补全详情”预览

## `mini_program_triage_detail.json`

对应页面：

- 后续小程序“待筛选详情”预览

## `mini_program_paper_detail.json`

对应页面：

- 后续单篇论文详情预览

## `demo_summary.md`

对应用途：

- 给非技术同事解释演示输出
- 给设计师快速理解页面应呈现什么
- 给前端确认 mock 内容和中文文案基调

## Frontend-1 建议使用的 mock data 范围

首版只需要直接消费：

- `import_preview.json`
- `import_commit.json`
- `paper_progress_summary.json`
- `research_pulse.json`

其余文件先作为后续页面的参照样本，不进入首版核心渲染。

## mock data 目录建议

如果后续进入 Frontend-1，实现阶段建议：

- 不直接读取 `/tmp/research_pulse_cn_demo`
- 手动挑选一组 curated output
- 放到前端 app 自己的 `mock/` 或 `fixtures/` 目录

原因：

- `/tmp` 输出是运行产物
- 不适合直接纳入仓库
- curated output 更适合长期页面开发

## 本轮结论

本轮只做评估，不提交 curated generated output。

原因：

- 当前 demo script 已能稳定产出
- 先固定映射关系即可
- 真正进入 Frontend-1 时，再决定是否复制一份 curated demo JSON

