# Frontend Channel Draft Preview Pages v2

## 目标

本轮不新增新的平台能力，也不重复新增页面。仍然围绕已有 3 个渠道页继续收紧细节：

1. 公众号摘要草稿页
2. 桌面通知草稿页
3. 小程序详情预览页

这一轮的重点是：

- 继续保持 `mock-only`
- 继续保持 `draft / preview / not_sent / share_safe`
- 进一步增强复制反馈、键盘可达性和长内容溢出处理
- 不引入真实平台 API

## 本轮增强

### 复制反馈重置

- 场景切换后，公众号页和桌面通知页的复制反馈会自动清空
- 小程序页在切换 `detail_type` tabs 后也会自动清空旧的复制反馈

目的：

- 避免用户把旧的“已复制”提示误认为当前 tab 或当前场景的数据反馈

### 小程序 tabs 键盘导航

当前 `detail_type` tabs 继续保留：

- `今日 Pulse`
- `单篇论文`
- `下一步动作`
- `待补全`
- `待筛选`

并新增：

- `ArrowLeft / ArrowUp`
- `ArrowRight / ArrowDown`
- `Home`
- `End`

键盘切换能力。

目的：

- 让 `tablist / tab / tabpanel` 语义真正可操作，而不是只有点击可用

### 长内容溢出处理

继续收紧：

- channel item card
- channel section card
- channel note list
- channel link list

让长标题、长 path、长说明在窄屏下不撑破布局。

## 页面范围

仍然只有这 3 个渠道页：

- `OfficialAccountDraftPage`
- `DesktopNotificationDraftPage`
- `MiniProgramDetailPreviewPage`

不新增：

- 登录 / 注册
- admin
- 设置页
- 真实微信 / 小程序 / 桌面通知
- 第 8 页

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

## 下一步建议

下一步更合理的方向有两个：

1. 继续做一轮 `Frontend-4 hardening`
2. 或者在边界不变的前提下进入后续 mock-only 前端展示页
