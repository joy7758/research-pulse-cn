# 导入预览与导入提交 v1

## Pivot-3 目标
- 在 Pivot-2 的导入格式基础层之上，补齐可确认、可选择、可提交的后端导入流程。
- 本轮重点是：
  - 创建导入预览
  - 标记哪些记录可提交
  - 提交所选记录
  - 返回结构化提交结果
- 本轮不做前端 UI，不做复杂字段映射界面，不做大规模导入工作台。

## Preview Flow
1. 调用方提交：
   - `source_format`
   - `payload`
2. 后端调用 Pivot-2 parser。
3. 生成标准化 preview records。
4. 对每条记录补充：
   - `source_index`
   - `warnings`
   - `errors`
   - `can_commit`
   - `selected`
5. 汇总 preview 统计字段。

## Commit Flow
1. 调用方提交：
   - `user_id`
   - `source_format`
   - `preview_records`
   - `selected_source_indexes`
2. 后端只处理被选中的且 `can_commit=true` 的记录。
3. 对不可提交记录返回 `skipped`，不让整批崩溃。
4. 对单条写入失败记录返回 `failed`，其他记录继续处理。
5. 返回批量 commit 结果。

## Preview Record 字段
- `source_index`
- `normalized_record`
- `title`
- `authors`
- `year`
- `venue`
- `doi`
- `url`
- `keywords`
- `warnings`
- `errors`
- `can_commit`
- `selected`

## Commit Request 字段
- `user_id`
- `source_format`
- `preview_id`
- `preview_records`
- `selected_source_indexes`
- `collection_label`
- `dry_run`
- `default_type`
- `default_stage`
- `default_priority`

## Commit Result 字段
- `preview_id`
- `user_id`
- `source_format`
- `dry_run`
- `committed_at`
- `total_selected`
- `committed_count`
- `skipped_count`
- `failed_count`
- `committed_record_ids`
- `record_results`
- `warnings`
- `errors`

每条 `record_result` 至少包括：
- `source_index`
- `status`
- `reason`
- `paper_id`
- `warnings`
- `errors`

## 可提交 / 不可提交规则
- 缺少 `title`：
  - 不可提交
  - 增加 `missing_required_field` error
- 有 warning 但无 error：
  - 仍然可提交
- 有 error：
  - 不可提交
- `selected=false` 或未出现在 `selected_source_indexes` 中：
  - 本轮不会提交

## Warnings / Errors 规则
- parser 在 Pivot-2 产生的 warning / error 会保留。
- Pivot-3 会补充预览层校验：
  - `title` 缺失时补 `missing_required_field`
- commit 阶段会补充批处理结果：
  - `record is not importable`
  - `selected source index was not present in preview payload`
  - `commit_failed`

## 批内轻量重复提示
本轮只做 batch 内部轻量 duplicate warning，不做复杂去重：

- DOI 完全相同：
  - `duplicate_doi_in_batch`
- title 规范化后完全相同：
  - `duplicate_title_in_batch`

这些只作为 warning：
- 不自动拦截提交
- 不查询网络
- 不做跨库去重
- 不做模糊相似度算法

## 当前持久化策略
- 本轮复用现有 `PaperProfile` 持久化模型。
- 不新增 migration。
- 不新增新的 paper/import 专用表。
- 提交时把 normalized import record 映射进现有 paper 结构：
  - `title`
  - `venue`
  - `source_links`
  - `identifiers`
- 导入来源相关元数据放入现有 `identifiers` JSON 字段，例如：
  - `doi`
  - `import_source_format`
  - `import_source_identifier`
  - `import_authors`
  - `import_keywords`
  - `import_language`
  - `import_raw_source_payload`
  - `import_attachments`
  - `import_notes`

## 示例

### 创建 Preview
```json
{
  "source_format": "csl_json",
  "payload": [
    {
      "title": "Import Preview Example",
      "author": [{"given": "Alice", "family": "Zhang"}],
      "issued": {"date-parts": [[2024]]},
      "DOI": "10.1000/example"
    }
  ]
}
```

### 提交选中记录
```json
{
  "user_id": "00000000-0000-0000-0000-000000000000",
  "source_format": "csl_json",
  "preview_id": "example-preview-id",
  "preview_records": [],
  "selected_source_indexes": [1],
  "dry_run": false,
  "default_type": "published",
  "default_stage": "imported",
  "default_priority": 3
}
```

## 中国市场场景说明
- 本轮已经覆盖：
  - CSV / TSV 表格导入
  - 中文列名
  - PDF 文件夹占位导入
- 这为后续承接中国市场常见来源做准备：
  - 知网导出表格
  - 万方导出表格
  - 维普导出表格
- 但本轮还没有实现这些正式 parser。

## 已知限制
- 没有前端 UI
- 没有字段映射确认界面
- 没有跨库去重
- 没有批量附件入库
- 没有真实 PDF metadata extraction
- 没有 OCR
- 没有复杂 collection/library 模型
- preview 不做长期 session 持久化

## 暂缓事项
- 完整 UI
- 字段映射 UI
- 跨库去重
- 知网 CNKI 正式导入
- 万方 Wanfang 正式导入
- 维普 VIP 正式导入
- Zotero connector / plugin / sync
- PDF metadata extraction
- OCR
- 公众号投递
- 小程序详情页
- 桌面通知
