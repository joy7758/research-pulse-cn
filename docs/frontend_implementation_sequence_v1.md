# Frontend Implementation Sequence v1

## 目标

本文件给 Frontend-1 提供实现顺序，确保前端第一版不从复杂功能开始。

## 总原则

- 先 mock，后 API
- 先首页，后细页
- 先结构，后 polish
- 先主动作，后次动作

## Step 0：创建最小前端 shell

目标：

- 只建立最小目录
- 只建立最小运行方式
- 不引入复杂状态管理
- 不接真实平台

本阶段不做：

- 登录
- 权限
- 复杂路由
- 后台布局系统

## Step 1：加载 demo JSON

目标：

- 先把 mock mode 跑起来
- 首页可以直接展示 `research_pulse.json`

建议：

- 只做一层非常薄的 data source abstraction
- 支持：
  - `mock mode`
  - `api mode`

## Step 2：首页 Today Research Pulse

目标：

- 先把产品第一屏做出来

内容：

- 今日概览
- 今日重点论文
- 下一步动作
- 元数据待补全
- 新导入待筛选

要求：

- 首页第一屏就回答“今天该做什么”
- 每页一个主动作

## Step 3：导入预览页

目标：

- 把 import preview 的用户感知跑通

内容：

- 拖入 / 粘贴入口
- import preview 统计
- warning / error 文案
- 可导入记录确认动作

要求：

- 不先做复杂文件上传工程
- 可以先 mock

## Step 4：Research Pulse 详情页

目标：

- 展开首页摘要，看到完整 section 结构

内容：

- 全量 sections
- item 列表
- 渠道草稿按钮

要求：

- 草稿按钮可以先是 mock 或 disabled
- 先表达产品意图，不急着接真实渠道 payload

## Step 5：接真实 API

目标：

- 在不改变 UI 结构的前提下，把 mock data source 替换成 real API source

前提：

- demo user 已存在
- 内部 bearer token 可用
- 仅供内部联调

要求：

- UI 保持不变
- contract 不变

## Step 6：后续页面

只有在前 5 步稳定之后，才考虑：

- 论文进度页
- 详情 drawer
- 公众号草稿页
- 桌面通知草稿页
- 小程序详情预览页

## Frontend-1 明确不要做

- 登录
- 真实文件上传复杂工程
- 真实投递
- 复杂路由体系
- 复杂全局状态管理
- 高级筛选
- admin 后台

## 建议节奏

```text
mock mode
-> 首页
-> 导入预览
-> Pulse 详情
-> internal API mode
-> 再扩页面
```

