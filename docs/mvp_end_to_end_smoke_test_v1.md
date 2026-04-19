# MVP End-to-End Smoke Test v1

## 目标

Pivot-9 不再扩展新功能，而是验证当前 China-first Research Pulse MVP 的主链路已经在本地打通：

1. 导入论文
2. 生成 import preview
3. 提交 import commit
4. 进入 paper progress workbench
5. 生成 Research Pulse 草稿
6. 生成公众号每日摘要草稿
7. 生成桌面通知草稿
8. 生成小程序详情 preview

本阶段只验证 backend 服务链路，不新增真实投递、真实桌面通知、真实小程序前端或外部模型调用。

## MVP 主链路

```text
import formats
-> import preview
-> import commit
-> paper progress
-> Research Pulse draft
-> official-account daily summary draft
-> desktop notification draft
-> mini-program detail preview
```

## 每一步输入与输出

### 1. Import formats
- 输入：
  - `CSL JSON`
  - `BibTeX`
  - `RIS`
  - `CSV/TSV/表格类文本`
  - `PDF folder placeholder`
- 输出：
  - 归一化 `PaperImportRecord`
  - 结构化 `warnings / errors`

### 2. Import preview
- 输入：
  - `POST /papers/import-preview`
- 输出：
  - `preview_id`
  - `total_records / valid_records_count / warning_records_count / error_records_count`
  - `records[]`
  - 每条记录的 `can_commit / warnings / errors`

### 3. Import commit
- 输入：
  - `POST /papers/import-commit`
  - `preview_records`
  - `selected_source_indexes`
- 输出：
  - `committed / skipped / failed`
  - `committed_record_ids`
  - `record_results[]`

### 4. Paper progress
- 输入：
  - `GET /papers/progress`
  - `GET /papers/progress/summary`
  - `GET /papers/progress/pulse-context`
  - `PATCH /papers/{paper_id}/progress`
- 输出：
  - 论文阅读状态
  - 研究阶段
  - 优先级
  - 下一步动作
  - 工作台 summary
  - Pulse 上下文

### 5. Research Pulse draft
- 输入：
  - `POST /pulse/papers/daily`
- 输出：
  - `ResearchPulseResult`
  - `today_focus`
  - `continue_reading`
  - `next_actions`
  - `metadata_attention`
  - `newly_imported_triage`

### 6. Official-account daily summary draft
- 输入：
  - `POST /pulse/papers/official-account/daily-summary`
- 输出：
  - `OfficialAccountDailySummaryResult`
  - `publication_preview`
  - `template_payload_preview`
  - `binding_preview`
- 语义：
  - 只生成草稿与 payload preview
  - 不创建真实发送任务

### 7. Desktop notification draft
- 输入：
  - `POST /pulse/papers/desktop-notification/draft`
- 输出：
  - `DesktopNotificationResult`
  - `title / body`
  - `actions`
  - `deep_link`
  - `payload_preview`
- 语义：
  - `delivery_state = draft`
  - 不调用真实系统通知

### 8. Mini-program detail preview
- 输入：
  - `POST /pulse/papers/mini-program/detail/preview`
- 输出：
  - `MiniProgramDetailResult`
  - `cards / items / actions / navigation`
  - `share_card`
  - `visibility_notes`
- 语义：
  - `delivery_state = preview`
  - 只输出 share-safe detail payload

## Draft / Preview / Not Sent 语义

- Import preview：
  - 只是解析与预览，不写入草稿投递层
- Research Pulse：
  - `dry_run=true` 的结构化草稿
- Official-account daily summary：
  - 草稿与模板 payload preview
  - 不创建 `PulseDigestIssue` 或 `DigestPublicationJob`
- Desktop notification：
  - `delivery_state = draft`
  - 不创建 `DeliveryJob`
- Mini-program detail：
  - `delivery_state = preview`
  - 不做真实微信交互

## 当前 API 路径清单

主链路直接使用这些 backend endpoint：

- `POST /users`
- `POST /papers/import-preview`
- `POST /papers/import-commit`
- `GET /papers/progress`
- `GET /papers/progress/summary`
- `GET /papers/progress/pulse-context`
- `GET /papers/{paper_id}/progress`
- `PATCH /papers/{paper_id}/progress`
- `POST /pulse/papers/daily`
- `POST /pulse/papers/official-account/daily-summary`
- `POST /pulse/papers/desktop-notification/draft`
- `POST /pulse/papers/mini-program/detail/preview`

可选的公众号绑定预置路径：

- `POST /admin/wechat-bindings`

## 当前 service 清单

Pivot-9 smoke test 直接或间接覆盖：

- `PaperImportFormatService`
- `PaperImportService`
- `PaperService`
- `PaperProgressWorkbenchService`
- `ResearchPulseService`
- `OfficialAccountDailySummaryService`
- `DesktopNotificationService`
- `MiniProgramDetailService`

## Smoke test 清单

建议保留一条完整主链路测试：

- `tests/test_mvp_end_to_end_smoke.py`

覆盖点：

1. 中文表格导入 preview
2. import commit 的 committed / skipped 结果
3. progress 更新与 summary / pulse-context
4. Research Pulse 草稿 section 生成
5. official-account daily summary 草稿
6. desktop notification 草稿
7. mini-program daily / paper / next_actions / metadata_attention / triage 详情 preview
8. share-safe 裁剪
9. 全链路 `draft / preview / not_sent` 边界

## 中国市场使用场景

- 研究生先用中文表格批量导入论文
- 导入后在后台标记：
  - 待读
  - 略读中
  - 精读中
  - 待筛选
  - 高优先级
- 系统生成当天的 Research Pulse 草稿
- 同一份论文上下文再被转换成：
  - 公众号每日摘要草稿
  - 桌面提醒草稿
  - 小程序详情 preview

## 已知限制

- 目前链路仍以 deterministic / template-based 为主
- official-account / desktop / mini-program 都还是草稿层
- 没有真实投递
- 没有真实小程序前端
- 没有真实桌面客户端通知
- 没有跨库去重
- 没有 PDF 深度元数据抽取

## 暂缓事项

- 知网 CNKI 正式导入
- 万方 Wanfang 正式导入
- 维普 VIP 正式导入
- Zotero connector / plugin / sync
- 真实微信公众号 API 发送
- `access_token` 管理
- 群发 / 素材上传 / 模板消息 / 客服消息
- 真实桌面通知
- Electron / Tauri / native desktop app 扩展
- 真实微信小程序 frontend
- 微信登录 / `openid` / `unionid`
- 订阅消息
- 支付
- 定时任务
- 运营后台
- 外部检索
- 外部 LLM 调用
- PDF metadata extraction
- OCR
- frontend UI
