# Frontend Minimal Web Shell Hardening v1

## 目标

Frontend-1 Hardening 只打磨现有最小 Web shell，不新增页面，不扩大产品范围。

本轮继续严格限制在 3 个页面：

1. 首页 / 今日 Research Pulse
2. 导入 / 导入预览
3. Research Pulse 详情

## 本轮打磨内容

### 页面状态覆盖

- 首页：
  - default
  - empty
  - warning
  - error（通过异常 mock 场景验证）
  - draft / preview / not_sent
  - refresh loading
- 导入 / 导入预览：
  - default
  - empty
  - warning
  - error
  - disabled
  - mock 入口说明
- Research Pulse 详情：
  - default
  - empty section
  - warning
  - draft / preview / not_sent
  - disabled

### 响应式规则

- 保持 desktop-first
- 在 `1280 / 1180 / 1024 / 820 / 640` 断点收敛布局
- 窄屏下：
  - sidebar 堆叠到顶部
  - summary card 改为单列或双列
  - 导入表格降级为卡片视图
  - 主按钮改为整行宽度

### 可访问性规则

- 使用语义标签和 `aria-current`
- `StatusBanner` 根据严重程度使用 `status` / `alert`
- `button / select / textarea` 增加 `focus-visible`
- badge 不只靠颜色，保留明确文字
- warning / error 一律给出中文解释和下一步动作

### mock mode 规则

- 明确显示当前是 `mock mode`
- 增加 4 个 curated mock 场景：
  - `default`
  - `empty`
  - `issues`
  - `broken`
- 通过场景切换验证空状态、问题状态和异常恢复路径
- mock 数据缺失时优先显示恢复提示，不假装真实 API 可用

## 本轮新增 mock 数据

- `apps/research-pulse-web/src/data/mock/empty_paper_progress_summary.json`
- `apps/research-pulse-web/src/data/mock/empty_import_preview.json`
- `apps/research-pulse-web/src/data/mock/empty_import_commit.json`
- `apps/research-pulse-web/src/data/mock/empty_research_pulse.json`
- `apps/research-pulse-web/src/data/mock/import_preview_with_errors.json`

这些文件全部是 synthetic / mock data，不包含真实论文全文、真实外部平台数据或敏感 payload。

## 本轮不做事项

- 不新增第 4 页
- 不新增论文进度页
- 不新增论文详情 drawer
- 不新增公众号草稿页
- 不新增桌面通知草稿页
- 不新增小程序详情预览页
- 不新增设置页
- 不做登录 / 注册 / 组织 / 团队 / admin
- 不接真实微信 / 小程序 / 桌面通知
- 不接外部 LLM / 外部网络
- 不改 backend API
- 不改 schema contract

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

构建与检查：

```bash
npm run build
npm run lint
npm run typecheck
```

后端保持不变，仍需从仓库根目录运行：

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest
```

## 下一步建议

更稳妥的下一步有两个：

1. 继续 `Frontend-1 hardening`
2. 进入 `Frontend-2：paper progress page`

如果当前 3 页在窄屏、空状态和文案边界上还不够稳，优先继续 hardening，不急着新增第 4 页。
