# Frontend Channel Draft Preview Pages v1

## 目标

本轮只新增 3 个渠道草稿 / 预览页面：

1. 公众号摘要草稿页
2. 桌面通知草稿页
3. 小程序详情预览页

边界保持不变：

- 只做 `draft / preview / payload` 展示
- 默认 `mock mode`
- 不接入真实微信公众号 API
- 不接入真实桌面通知
- 不接入真实小程序
- 不改 backend / API contract / schema contract

## 页面范围

### 公众号摘要草稿页

- 展示 `headline`
- 展示摘要 section
- 展示 publication preview
- 展示 template payload preview
- 主动作：复制 Markdown 草稿
- 状态：`draft / not_sent`

### 桌面通知草稿页

- 展示通知标题、正文、badge、urgency
- 展示通知条目和动作 deep link
- 展示 payload preview
- 主动作：复制通知 payload
- 状态：`draft / not_sent`

### 小程序详情预览页

- 支持 `daily_pulse / paper / next_actions / metadata_attention / triage` 切换
- 展示 cards、share card、navigation path
- 展示当前 detail payload
- 主动作：复制当前 detail payload
- 状态：`preview / share_safe`

## 数据来源

页面只消费 curated mock JSON：

- `apps/research-pulse-web/src/data/mock/official_account_daily_summary.json`
- `apps/research-pulse-web/src/data/mock/desktop_notification.json`
- `apps/research-pulse-web/src/data/mock/mini_program_daily_pulse_detail.json`
- `apps/research-pulse-web/src/data/mock/mini_program_paper_detail.json`
- `apps/research-pulse-web/src/data/mock/mini_program_next_actions_detail.json`
- `apps/research-pulse-web/src/data/mock/mini_program_metadata_attention_detail.json`
- `apps/research-pulse-web/src/data/mock/mini_program_triage_detail.json`

这些数据都是 synthetic preview data，不代表真实平台绑定、推送或微信能力。

## mock mode 规则

- 页面显式显示 `draft / preview / not_sent`
- copy 动作只复制本地文案或 payload
- 不会真实发送
- 不会真实推送
- 不会创建真实微信小程序页面
- `broken` 场景仍沿用 shell 级恢复逻辑

## 页面状态

当前至少覆盖：

- `default`
- `empty`
- `warning`
- `mock-only`

说明：

- `empty` 主要通过 `empty` 场景和 section 级空数据验证
- `warning` 用来明确模板、绑定、payload、share-safe 的边界

## 响应式

- `1280 / 1024`：双栏信息区仍保持清楚
- `820`：双栏收成单列
- `640`：按钮堆叠、payload 预览缩小字号

## 可访问性

- 页面按钮继续保留清晰中文说明
- tabs / chips 使用 button
- payload 区域有明确标题
- warning / mock-only 不只靠颜色表达

## 不做事项

- 不做真实微信发送
- 不做 access_token 管理
- 不做群发 / 模板消息 / 素材上传
- 不做系统通知调用
- 不做真实小程序登录 / 订阅消息 / 支付
- 不做登录 / admin / 设置 / 完整文献库
- 不改 backend contract

## 运行方式

```bash
cd apps/research-pulse-web
npm install
npm run dev
npm run build
npm run lint
npm run typecheck
```

仓库根目录仍需：

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest
```

## 下一阶段建议

优先做：

1. `Frontend-3 hardening`
2. 或在确认稳定后进入 `Frontend-4`

仍然不要直接接入真实平台。
