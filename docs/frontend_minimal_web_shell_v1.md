# Frontend Minimal Web Shell v1

## 目标

Frontend-1 只提供一个极小 Web shell，用来把已经冻结的 MVP 主链路转成可点击、可读、可本地演示的前端界面。

本轮范围严格限制在 3 个页面：

1. 首页 / 今日 Research Pulse
2. 导入 / 导入预览
3. Research Pulse 详情

## 技术栈

- React
- Vite
- TypeScript
- plain CSS

本轮刻意不引入：

- 大型 UI 组件库
- Tailwind
- 复杂状态管理
- React Router
- Electron / Tauri

## 目录结构

```text
apps/research-pulse-web/
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  tsconfig.node.json
  eslint.config.js
  src/
    App.tsx
    App.css
    main.tsx
    data/mock/
      import_preview.json
      import_commit.json
      paper_progress_summary.json
      research_pulse.json
    lib/
      dataSource.ts
      types.ts
    components/
    pages/
```

## 三页范围

### 1. 首页 / 今日 Research Pulse

包含：

- 今日概览
- 今日重点论文
- 下一步动作
- 元数据待补全
- 新导入待筛选
- 主动作：刷新今日 Pulse
- 次动作：导入论文、查看 Pulse 详情

### 2. 导入 / 导入预览

包含：

- 拖入区域 mock
- 粘贴区域 mock
- 可导入 / warning / error 统计
- 字段预览表格
- 问题记录列表
- 主动作：确认导入可导入记录
- 次动作：只看问题记录、返回首页

### 3. Research Pulse 详情

包含：

- 五个 section 的完整展开
- `draft / preview / not_sent` 状态标识
- 主动作：生成公众号摘要草稿
- 次动作：返回首页

## mock mode

Frontend-1 默认使用 mock mode。

当前直接消费的 curated demo JSON：

- `import_preview.json`
- `import_commit.json`
- `paper_progress_summary.json`
- `research_pulse.json`

这些文件基于 Demo-1 的输出结构整理而来，用于本地离线演示，不依赖真实后端请求。

## API mode 预留

本轮只做非常薄的 API mode 预留，不默认启用。

已在代码中预留的 endpoint 入口：

- `POST /papers/import-preview`
- `POST /papers/import-commit`
- `GET /papers/progress/summary`
- `GET /papers/progress/pulse-context`
- `POST /pulse/papers/daily`

当前约束：

- 不接登录
- 不接 bearer token 流程
- 不改 backend contract
- 只作为后续内部联调入口

## 运行方式

安装依赖：

```bash
cd apps/research-pulse-web
npm install
```

开发模式：

```bash
npm run dev
```

构建：

```bash
npm run build
```

静态检查：

```bash
npm run lint
npm run typecheck
```

## 页面边界

Frontend-1 明确不做：

- 登录 / 注册
- admin 后台
- 组织 / 团队
- 完整文献库
- 论文详情 drawer
- 公众号草稿页
- 桌面通知草稿页
- 小程序详情预览页
- 设置页
- 真实微信、小程序、桌面通知
- 外部 LLM、外部网络

## 视觉与交互要求

- 中文界面
- 每页一个主动作
- 首页第一屏回答“今天该做什么”
- `warning` 翻译成建议
- `error` 给出下一步动作
- `draft / preview / not_sent` 必须有文字说明，不能只靠颜色

## 下一阶段建议

更稳妥的顺序是二选一：

1. `Frontend-1 hardening`
2. `Frontend-2 paper progress page`

不建议在本轮之后直接膨胀成完整产品前端。
