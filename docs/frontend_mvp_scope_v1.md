# Frontend MVP Scope v1

## 目标

本文件固定 Frontend-1 的最小范围，防止前端第一版膨胀成完整产品后台。

## Frontend-1 只做什么

Frontend-1 最多只做 3 个核心页面：

1. 首页 / 今日 Research Pulse
2. 导入 / 导入预览
3. Research Pulse 详情

## 页面 1：首页 / 今日 Research Pulse

### 目标

让用户第一眼知道：

- 今天该看什么
- 哪些论文要处理
- 下一步做什么

### 页面内容

- 今日概览
- 今日重点论文
- 下一步动作
- 元数据待补全
- 新导入待筛选

### 主动作

- `刷新 / 生成今日 Pulse`

### 次动作

- `导入论文`

### 数据来源

- mock mode：`research_pulse.json` + `paper_progress_summary.json`
- real API mode：
  - `GET /papers/progress/summary`
  - `GET /papers/progress/pulse-context`
  - `POST /pulse/papers/daily`

## 页面 2：导入 / 导入预览

### 目标

用最短路径展示：

- 拖入 / 粘贴
- 自动识别
- 预览结果
- 确认可导入记录

### 页面内容

- 拖入区域
- 粘贴区域
- 预览统计
- 记录列表
- warning / error 列表

### 主动作

- `确认导入可导入记录`

### 次动作

- `只看问题记录`

### 数据来源

- mock mode：
  - `import_preview.json`
  - `import_commit.json`
- real API mode：
  - `POST /papers/import-preview`
  - `POST /papers/import-commit`

### 范围收口

- Frontend-1 不做复杂文件上传工程
- 可以先用文本粘贴和 mock 数据展示交互

## 页面 3：Research Pulse 详情

### 目标

完整展示 structure sections，并让用户知道后续可以继续生成哪些草稿。

### 页面内容

- 今日重点论文
- 继续阅读与分析
- 下一步动作
- 元数据待补全
- 新导入待筛选

### 主动作

- `生成公众号摘要草稿`

### 次动作

- `生成桌面通知草稿`
- `小程序详情预览`

### 数据来源

- mock mode：
  - `research_pulse.json`
  - 后续可读：
    - `official_account_daily_summary.json`
    - `desktop_notification.json`
    - `mini_program_daily_pulse_detail.json`
- real API mode：
  - `POST /pulse/papers/daily`
  - `POST /pulse/papers/official-account/daily-summary`
  - `POST /pulse/papers/desktop-notification/draft`
  - `POST /pulse/papers/mini-program/detail/preview`

## 可选但不进入 Frontend-1

以下页面可以在后续阶段再做，但不进入首版：

- 论文进度页
- 论文详情 drawer
- 公众号草稿页
- 桌面通知草稿页
- 小程序详情预览页
- 设置页

## Frontend-1 不做什么

明确不做：

- 登录注册
- 组织 / 团队
- admin 后台
- 真实微信投递
- 真实小程序前端
- 真实桌面客户端
- 真实文件上传复杂流程
- 长期任务 / 调度
- 复杂状态管理
- 富文本编辑
- 引文写作插件
- Zotero connector
- CNKI / Wanfang / VIP 正式集成

## Frontend-1 成功标准

只要前端第一版能稳定展示：

- 今天该看什么
- 哪些论文要处理
- 下一步做什么

并且能在 mock mode 下跑通 3 个页面，就达标。

