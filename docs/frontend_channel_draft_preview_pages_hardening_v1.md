# Frontend Channel Draft Preview Pages Hardening v1

## 目标

本轮只打磨 Frontend-3 已有的 3 个渠道页：

1. 公众号摘要草稿页
2. 桌面通知草稿页
3. 小程序详情预览页

范围保持不变：

- 继续只做 `draft / preview / not_sent / share_safe` 展示
- 继续只做 `mock mode`
- 不接真实微信公众号 API
- 不接真实桌面通知
- 不接真实小程序
- 不改 backend / API contract / schema contract
- 不新增页面

## 页面状态增强

### 公众号摘要草稿页

- 主动作 disabled 时明确提示“当前没有可复制的摘要内容”
- 绑定预览为空时显示 compact empty state
- 模板字段为空时显示 compact empty state
- provider notes 为空时显示 fallback 文案
- 继续显式显示 `draft / not_sent`

### 桌面通知草稿页

- 主动作 disabled 时明确提示“当前没有可复制的桌面通知内容”
- 通知动作为空时显示 compact empty state
- 交付说明为空时显示 fallback 文案
- 新增 `urgency / deep link / notification_type` 边界说明
- 继续显式显示 `draft / not_sent`

### 小程序详情预览页

- 主动作 disabled 时明确提示“当前没有可复制的详情内容”
- `detail_type` tabs 补齐 tab / tabpanel 语义
- 当前 detail_type 的 actions 为空时显示 compact empty state
- `visibility_notes` 为空时显示 fallback 文案
- 继续显式显示 `preview / share_safe`

## 复制与反馈

- 公众号页：复制 Markdown 草稿后显示中文反馈
- 桌面通知页：复制 payload 后显示中文反馈
- 小程序页：复制 detail payload / path / share card 后显示中文反馈
- 所有复制反馈都保持 mock-only 语义，不暗示真实发送或真实推送

## 响应式规则

- `1280px`：信息双栏保持清楚
- `1024px`：`channel-double-grid` 收成单列，避免草稿页信息拥挤
- `820px`：卡片头部改为更易读的纵向布局
- `640px`：按钮全宽堆叠，payload 区缩小字号但保持可复制

## 可访问性规则

- 公众号页、桌面通知页、小程序页的主动作都补了 `aria-label`
- 主动作 disabled 时通过 `aria-describedby` 解释原因
- 小程序 tabs 补了：
  - `role="tablist"`
  - `role="tab"`
  - `aria-selected`
  - `aria-controls`
  - `role="tabpanel"`
- 复制反馈继续通过状态 banner 暴露给读屏器
- 状态不只靠颜色表达

## mock-only 边界

- 公众号页只复制 Markdown 草稿，不发送公众号摘要
- 桌面通知页只复制 payload，不调用系统通知
- 小程序页只复制 `detail payload / path / share card`，不触发真实微信能力
- mock JSON 仅为 synthetic preview data，不代表真实绑定、发送、登录、订阅消息或支付

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

## 不做事项

- 不接 access_token
- 不做群发 / 模板消息 / 素材上传
- 不做系统通知调用
- 不做真实小程序登录 / 订阅消息 / 支付
- 不做登录 / admin / 设置 / 完整文献库
- 不改 backend contract
- 不新增依赖

## 下一阶段建议

优先二选一：

1. 继续做一轮 `Frontend-3 hardening`
2. 进入 `Frontend-4`，但仍然只做 mock-only 的前端展示页
