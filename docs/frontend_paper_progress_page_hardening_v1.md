# Frontend Paper Progress Page Hardening v1

## 目标

本轮只打磨已有 `论文进度` 页，不新增第 5 页，不引入真实 API，也不扩大前端范围。

重点是让这 1 页在 mock mode 下更稳定、更容易理解：

- 筛选组合状态更清楚
- 搜索反馈更可读
- 卡片信息层级更稳
- 主动作 disabled / mock-only 说明更明确
- 窄屏布局和键盘可达性更完整

## 页面状态增强

本轮重点覆盖：

- `default`
- `empty`
- `filtered_empty`
- `warning`
- `disabled`
- `mock-only`

说明：

- `error` 仍保留 shell 级 `broken` 场景作为恢复路径
- 页面本身补了更稳的 fallback 文案，避免无结果时看起来像故障

## 筛选与搜索规则

当前支持：

- 全部
- 待读
- 略读中
- 精读中
- 已读
- 高优先级
- 有下一步动作
- 待补全

增强点：

- 每个筛选项显示数量
- 当前筛选项有明确 selected 状态
- 搜索与筛选同时生效
- 显示当前条件摘要
- 提供 `清除筛选` / `清除搜索` 次动作
- 筛选结果为空时给出恢复建议，不把 warning / empty 写成错误提示

## 卡片信息层级

`ProgressPaperCard` 现在按以下顺序呈现：

1. 题名
2. 作者 / 年份 / 来源
3. 优先级 / 阅读状态 / 研究阶段 badge
4. 下一步动作
5. 来源格式 / 最近触达
6. 建议补全
7. 标签 / 关键词

约束保持不变：

- 高优先级不把整张卡渲染成红色警报
- 元数据 warning 用“建议补全”语气
- 空作者 / 空年份 / 空来源显示“待补全”

## 主动作规则

论文进度页仍然只有一个视觉主动作：

- `更新选中论文进度`

稳定化规则：

- 未选中论文时保持 disabled
- 页面显式说明“请选择一篇论文后再更新进度”
- 点击后只显示本地预览提示
- 明确写出“不会真实修改论文库”

## 响应式规则

重点保持：

- `1440 / 1280`：统计、筛选、卡片舒展
- `1024`：统计卡片自动换行
- `768`：筛选 chip 换行，卡片单列
- `640`：主动作和次动作堆叠，搜索相关动作换行

保持不做：

- 不改成后台密集表格
- 不增加复杂分页或高级筛选面板

## 可访问性规则

本轮补充：

- 筛选 chip 保持 button + `aria-pressed`
- 搜索框保留显式 label
- 统计卡片补充可读 `aria-label`
- 论文卡片支持键盘 focus 和 Enter / Space 选中
- selected card 使用文字和视觉双重提示
- focus-visible 更清楚
- warning / mock-only / disabled 都有文字说明，不只靠颜色

## mock-only 边界

论文进度页继续只消费：

- `apps/research-pulse-web/src/data/mock/paper_progress_items.json`
- `apps/research-pulse-web/src/data/mock/paper_progress_summary.json`

不做：

- 真实保存
- 真实进度 API 写入
- 真实外部平台同步

## 不做事项

- 不新增第 5 页
- 不新增登录 / admin / 设置
- 不新增论文详情 drawer
- 不新增公众号 / 桌面通知 / 小程序详情页面
- 不改 backend API
- 不改 API / schema contract
- 不新增依赖

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

## 下一阶段建议

优先顺序：

1. `Frontend-3：channel draft preview pages`
2. 如果进度页还需要细修，可继续做一轮 `Frontend-2 hardening`

仍然不要直接膨胀成完整产品前端。
