# Frontend Paper Progress Page v1

## 目标

Frontend-2 只新增第 4 页：论文进度页。

本页不做完整文献库，不做后台管理系统，不做真实写入，只帮助用户快速判断：

- 哪些论文待读
- 哪些在略读 / 精读
- 哪些有下一步动作
- 哪些元数据待补全
- 哪些是高优先级

## 页面范围

本轮只新增：

1. 论文进度页

不新增：

- 第 5 页
- 论文详情 drawer
- 公众号草稿页
- 桌面通知草稿页
- 小程序详情预览页
- 设置页
- 登录 / admin / 团队 / 组织

## 页面结构

论文进度页包括：

- 页面标题与说明
- `mock mode / 本地预览` 状态说明
- 进度统计卡片
- 筛选 chip
- 搜索框
- 论文卡片列表
- 唯一主动作：`更新选中论文进度`
- 次动作：
  - 返回今日 Pulse
  - 导入更多论文
  - 查看 Pulse 详情

## 数据来源

当前只消费 curated mock data：

- `apps/research-pulse-web/src/data/mock/paper_progress_items.json`
- `apps/research-pulse-web/src/data/mock/paper_progress_summary.json`

这些数据全部是 synthetic demo data，不包含真实论文全文、敏感 payload 或外部服务数据。

## mock mode

论文进度页继续沿用当前 shell 的 mock 场景：

- `default`
- `empty`
- `issues`
- `broken`

其中：

- `default`：正常展示统计、筛选和卡片
- `empty`：验证无论文时的引导
- `issues`：验证待补全 warning 与 disabled 主动作
- `broken`：验证异常数据恢复路径

## 筛选规则

当前支持轻量筛选：

- 全部
- 待读
- 略读中
- 精读中
- 已读
- 高优先级
- 有下一步动作
- 待补全

并支持按以下字段做关键词搜索：

- 题名
- 作者
- 来源
- 标签
- 关键词
- next_action

## 页面状态

已覆盖：

- default
- empty
- warning
- error
- disabled
- mock-only

说明：

- 没有选中论文时，唯一主动作保持 disabled
- 点击主动作后只显示本地预览反馈，不真实写入论文库

## 响应式

- desktop-first
- `1280 / 1180 / 1024 / 820 / 640` 断点下保持可读
- 窄屏下：
  - 筛选 chip 可换行
  - 统计卡片堆叠
  - 卡片保持单列
  - 主按钮整行展示

## 可访问性

- 筛选 chip 使用 button
- `aria-pressed` 标记当前筛选
- 搜索框有 label
- 主按钮 disabled 时有文字说明
- 状态不只靠颜色表达
- selected card 有文字和视觉双重提示

## 不做事项

- 不真实保存进度
- 不改 backend API
- 不改 schema contract
- 不接真实微信 / 小程序 / 桌面通知
- 不接外部 LLM / 外部网络
- 不做复杂批量编辑
- 不做完整文献库

## 运行方式

```bash
cd apps/research-pulse-web
npm install
npm run dev
npm run build
npm run lint
npm run typecheck
```

仓库根目录仍需运行：

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest
```

## 下一步建议

更稳妥的顺序仍然是：

1. `Frontend-2 hardening`
2. `Frontend-3：channel draft preview pages`

不建议在本轮之后直接膨胀成完整产品前端。
