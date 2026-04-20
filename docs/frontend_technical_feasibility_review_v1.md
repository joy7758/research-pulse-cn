# Frontend Technical Feasibility Review v1

## 目标

本文件审查当前 `research-pulse-cn` 仓库是否适合引入一个最小 Web UI，并明确 Frontend-1 的安全边界、最小范围和推荐实施方式。

本文件只做规划，不新增任何前端实现。

## 结论先行

当前仓库已经具备做 **最小独立 Web shell** 的工程条件，但 **还不适合直接做完整产品前端**。

更合理的路线是：

```text
Frontend-1 = 极小独立 Web shell
只做 3 个页面
先支持 demo JSON mock mode
再预留 real API mode
不做登录
不做 admin
不做真实投递
```

## 当前仓库结构观察

### 1. 后端结构

- 当前后端是 FastAPI。
- OpenAPI 已可用。
- API contract 和 schema contract 已冻结：
  - `docs/api_contract_mvp_v1.md`
  - `docs/schema_contract_mvp_v1.md`
  - `docs/error_warning_contract_mvp_v1.md`

这意味着前端不需要重新发明接口，也不应该推动 backend 改 contract。

### 2. demo 资产

当前仓库已经有本地演示入口：

- `scripts/run_mvp_demo.py`
- `demo/fixtures/mvp/*`

它能稳定产出：

- `import_preview.json`
- `import_commit.json`
- `paper_progress_summary.json`
- `research_pulse.json`
- `official_account_daily_summary.json`
- `desktop_notification.json`
- `mini_program_*`
- `demo_summary.md`

这使得前端第一版完全可以先用 demo JSON 做 mock mode。

### 3. 已有前端技术栈痕迹

仓库中已经存在多个 thin web shells：

- `apps/subscription-editor-web`
- `apps/result-share-web`
- `apps/group-workspace-admin-web`
- `apps/group-workspace-invite-web`
- `apps/user-workbench-admin-web`

这些 shell 的共同点是：

- React
- Vite
- TypeScript
- npm + `package-lock.json`

所以，从仓库工程惯例上看：

- **做一个新的极小独立 Web app 是可行的**
- **没有必要在 Frontend-1 里引入新的前端技术栈**

### 4. FastAPI static / templates 习惯

当前仓库没有明显的 `StaticFiles` / `Jinja2Templates` 习惯。

这意味着：

- 把 MVP 前端直接塞进 FastAPI templates 不是当前项目的自然路径
- 如果后续要做前端，实现形态更适合继续沿用 `apps/*` 的独立 web shell 模式

### 5. 当前真实 API 使用门槛

一个关键现实约束是：

- 当前核心 MVP API 都在 admin JWT 保护之后
- `POST /papers/import-preview`、`POST /pulse/papers/daily` 等都不是匿名接口

所以 Frontend-1 不能假装自己已经是“面向最终用户直接可用”的完整产品。

更准确的定位应是：

- **内部演示和开发验证用的最小 Web shell**
- 先跑 mock mode
- real API mode 只作为内部开发联调用入口

## 可选前端方案比较

## 方案一：极小独立 Web app

示例方向：

- `apps/research-pulse-web`
- React + Vite + TypeScript
- 先 mock mode，再接 real API mode

### 优点

- 符合当前仓库已有 `apps/*` 模式
- 能独立消费 frozen API contract
- 适合后续逐步扩展页面
- 可以清楚隔离 MVP 用户界面和旧 admin shells
- 更容易直接复用 Design-1 / Design-2 / Design-3 文档

### 风险

- 如果页面范围不收紧，很容易继续膨胀
- 如果一开始接真实 API，马上会撞到登录、token、用户选择等非 MVP 问题
- 如果复用旧 admin 壳，界面容易滑向“后台系统感”

### 对仓库影响

- 后续会新增一个独立 app 目录
- 会新增 `package.json`
- 会引入前端构建流程

### 适合何时采用

- 现在就适合做 **Frontend-1 minimal web shell**
- 但必须严格收在 3 个核心页面内

## 方案二：FastAPI static / templates 超轻页面

### 优点

- 表面上看，依赖更少
- 可以少一个前端 app 目录

### 风险

- 不符合仓库现有前端惯例
- 很快会在交互层遇到限制
- 不利于 mock mode / API mode 切换
- 不利于后续把首页、导入预览、Pulse detail 做成清晰前端状态机
- 容易把前端和 backend transport 绑死

### 对交互复杂度限制

- 对导入预览、多 section、状态矩阵和 mock 切换都不友好

### 适合 demo 还是长期产品

- 只适合极临时内部 demo
- 不适合作为 MVP 前端基线

## 方案三：先只做静态 clickable prototype

### 优点

- 风险最低
- 继续停留在设计验证
- 不碰数据联动

### 风险

- 当前已经有 Design-2 / Design-3 文档
- 再做一轮静态原型，信息增量有限
- 不能验证 payload 和页面结构是否真正顺手

### 适用场景

- 当团队还不准备进入任何实现阶段时

### 当前判断

- 对本项目来说已经不够
- 因为我们已经有可稳定运行的 demo JSON 和 API contract

## 方案四：继续不做前端，只用 demo JSON

### 何时仍然合理

- 只做内部接口评审
- 只做后端验证
- 只给技术团队看

### 何时不再合理

- 需要给设计师做页面层验证
- 需要给非技术同事演示真实使用路径
- 需要验证“首页是否真的能回答今天该做什么”

### 当前判断

- 继续只看 JSON 已经不够
- 但还不应该直接跳到完整前端

## 推荐方案

推荐：

```text
方案一：极小独立 Web app
```

但要附带强约束：

1. 先只做 mock mode  
直接消费 Demo-1 生成的 JSON。

2. 后续再加 real API mode  
仅用于内部联调，不引入登录流程。

3. 只做 3 个页面  
- 首页 / 今日 Research Pulse  
- 导入 / 导入预览  
- Research Pulse 详情

4. 不扩展成后台  
不碰 admin、组织、复杂筛选、设置中心、权限中心。

## 不推荐方案及原因

### 不推荐直接做完整前端

原因：

- API 虽然冻结了，但用户级鉴权流程还不是前端优先事项
- 页面层目标必须先验证最小闭环
- 很容易把 MVP 工作台做成复杂系统

### 不推荐把页面塞进 FastAPI templates

原因：

- 不符合当前工程模式
- 会削弱未来前端独立迭代能力

### 不推荐继续完全停留在文档和 JSON

原因：

- 已经到了可以做最小交互壳的阶段
- 否则设计文档难以真正验证

## Frontend-1 的前置条件

进入 Frontend-1 之前，建议满足以下条件：

1. API contract 保持冻结  
不要在前端过程中推动接口漂移。

2. demo fixture 和 demo output 继续稳定  
前端先基于这些 mock 数据实现。

3. 明确 Frontend-1 是内部演示壳，不是生产用户端  
避免误加登录、权限、组织、真实平台接入。

4. 采用现有仓库前端惯例  
如果进入实现，优先延续 `apps/*` 的 React + Vite + TypeScript 轻壳模式。

5. 明确 real API mode 的使用前提  
只允许：
  - 内部 bearer token
  - 固定 demo user
  - 本地或测试环境  
不做用户登录。

