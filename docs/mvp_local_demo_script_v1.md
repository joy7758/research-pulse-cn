# MVP Local Demo Script V1

## 目标

`scripts/run_mvp_demo.py` 提供一个本地离线、确定性运行的 MVP 演示入口。

它复用现有 FastAPI 路由和业务服务，在临时 SQLite 环境中跑通：

```text
导入样本
-> import preview
-> import commit
-> paper progress
-> Research Pulse draft
-> 公众号摘要草稿
-> 桌面通知草稿
-> 小程序详情预览
-> JSON / Markdown 演示输出
```

## 运行方式

最小命令：

```bash
.venv/bin/python scripts/run_mvp_demo.py \
  --output-dir /tmp/research_pulse_cn_demo \
  --date 2026-04-19 \
  --format csv \
  --max-items-per-section 3
```

## 参数

- `--fixture-dir`
  - 默认：`demo/fixtures/mvp`
- `--output-dir`
  - 默认：`/tmp/research_pulse_cn_demo`
- `--format`
  - 默认：`csv`
  - 可选：`csv` / `csl` / `bibtex` / `ris` / `pdf_manifest`
- `--date`
  - 默认：`2026-04-19`
- `--max-items-per-section`
  - 默认：`3`

## 输出文件

脚本会写出：

- `import_preview.json`
- `import_commit.json`
- `paper_progress_summary.json`
- `research_pulse.json`
- `official_account_daily_summary.json`
- `desktop_notification.json`
- `mini_program_daily_pulse_detail.json`
- `mini_program_paper_detail.json`
- `mini_program_next_actions_detail.json`
- `mini_program_metadata_attention_detail.json`
- `mini_program_triage_detail.json`
- `demo_summary.md`

## 输出解释

### `import_preview.json`

- 演示哪些记录可导入
- 哪些记录只有 warning
- 哪些记录因为缺题名等原因不可导入

### `import_commit.json`

- 演示 commit 阶段的：
  - `committed`
  - `skipped`
  - `failed`

### `paper_progress_summary.json`

- 演示导入完成后工作台的结构化统计结果。

### `research_pulse.json`

- 演示 deterministic Research Pulse 草稿。

### `official_account_daily_summary.json`

- 保留当前 API contract 的原始草稿 payload。
- 通过 `dry_run=true`、标题和 `source_context_notes` 表达它是草稿。
- 这里不会创建真实发送任务。

### `desktop_notification.json`

- 演示桌面通知草稿 payload。
- `delivery_state = draft`

### `mini_program_*`

- 演示小程序详情预览。
- `delivery_state = preview`
- `share_safe = true`

### `demo_summary.md`

- 面向非技术人员的演示摘要。
- 适合设计师、前端、投资人或内部评审快速阅读。

## 草稿和预览语义

- 公众号摘要：`draft / not_sent`
- 桌面通知：`draft / not_sent`
- 小程序详情：`preview / share-safe`

这些语义在脚本控制台输出和 `demo_summary.md` 中会显式说明。

## 演示建议

### 给设计师 / 前端演示

优先看：

- `research_pulse.json`
- `desktop_notification.json`
- `mini_program_daily_pulse_detail.json`
- `demo_summary.md`

### 给投资人 / 非技术同事演示

优先看：

- 控制台中文摘要
- `demo_summary.md`
- `official_account_daily_summary.json`

### 给测试 / 开发演示

优先看：

- `import_preview.json`
- `import_commit.json`
- `paper_progress_summary.json`
- 全部 `mini_program_*.json`

## 常见问题

### 1. 为什么不直接发公众号？

因为当前 MVP 只做草稿与 payload 预览，不做真实发送。

### 2. 为什么桌面通知没有真实弹窗？

因为当前只输出本地草稿 payload，不调用系统通知 API。

### 3. 为什么小程序只有 path 和 share card？

因为当前只做 detail preview / share-safe payload，不做真实小程序前端。

### 4. 为什么没有外部模型增强？

当前 demo 必须本地离线、确定性运行，不依赖外部模型或网络。

## 边界

这个 demo script 明确不做：

- 真实微信公众号 API
- `access_token` 管理
- 群发 / 素材上传 / 模板消息 / 客服消息
- 真实桌面通知
- 真实小程序 frontend
- 微信登录 / `openid` / `unionid`
- 订阅消息 / 支付
- 外部模型调用
- 外部网络请求
- CNKI / Wanfang / VIP 正式导入
- Zotero plugin / connector / sync

