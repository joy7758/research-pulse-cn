# MVP Demo Fixture Pack V1

## 目标

这组 fixture 用于本地离线演示 Research Pulse CN 的 MVP 主链路：

```text
导入样本
-> import preview
-> import commit
-> paper progress
-> Research Pulse draft
-> 公众号摘要草稿
-> 桌面通知草稿
-> 小程序详情预览
```

它的目标不是模拟真实平台接入，而是给开发、设计、销售演示、投资人演示和内部测试提供一套稳定、可重复的输入样本。

## 数据性质

- 所有数据都是 synthetic demo data。
- 题名、作者、来源、摘要和链接均为演示占位。
- 不包含真实 CNKI / Wanfang / VIP 数据。
- 不包含真实论文全文。
- 不包含受版权保护的真实论文摘要。
- 不包含真实微信公众号、小程序或桌面通知凭证。

## fixture 位置

当前 fixture pack 位于：

```text
demo/fixtures/mvp/
```

包含以下文件：

- `demo_papers_cn.csv`
- `demo_papers_csl.json`
- `demo_papers.bib`
- `demo_papers.ris`
- `demo_pdf_folder_manifest.json`

## 每个 fixture 文件的用途

### `demo_papers_cn.csv`

- 面向最容易理解的中文表格导入演示。
- 使用中文列名：
  - `题名`
  - `作者`
  - `年份`
  - `来源`
  - `摘要`
  - `关键词`
  - `doi`
  - `链接`
- 适合给产品、设计、运营或非技术同事演示。

### `demo_papers_csl.json`

- 用于演示标准化论文元数据导入。
- 适合验证 `CSL JSON -> import preview -> commit` 这条链路。

### `demo_papers.bib`

- 用于演示 BibTeX 导入。
- 适合给学术写作、LaTeX 和题录管理用户演示。

### `demo_papers.ris`

- 用于演示 RIS 导入。
- 适合验证常见文献导出格式兼容性。

### `demo_pdf_folder_manifest.json`

- 用于演示 PDF 文件夹占位导入。
- 不做真实 PDF metadata extraction。
- 只根据文件名推断题名，并触发元数据待补全提醒。

## 覆盖的用户场景

这组 fixture 至少覆盖以下场景：

1. 高优先级论文  
包含 `urgent / reviewing / reading / next_action` 场景。

2. 持续阅读论文  
包含 `skimming / relevant` 场景，用于 `继续阅读与分析` section。

3. 元数据不完整论文  
缺失 `year / venue / doi` 中至少一项，用于触发 metadata attention。

4. 新导入待筛选论文  
包含 `triage / unread` 场景。

5. 已读 / 已引用论文  
用于展示进度不是只有待读和处理中。

6. 低优先级 / parked / archived 论文  
用于验证默认过滤和 `include_low_priority / include_archived` 行为。

7. 不可导入记录  
至少有一条缺题名记录，用于演示 preview 阶段的可解释错误。

## 与真实平台的边界

这组 fixture 只服务于：

- 本地演示
- 自动化测试
- 前端联调前的 payload 对齐
- 设计评审

这组 fixture 不代表：

- 真实微信数据
- 真实知网 / 万方 / 维普 导入
- 真实 Zotero connector / plugin / sync
- 真实桌面通知
- 真实小程序详情页数据来源

## 建议使用方式

- 默认先用 `demo_papers_cn.csv` 演示整条 MVP 链路。
- 如果要强调格式兼容性，再切换到：
  - `csl`
  - `bibtex`
  - `ris`
  - `pdf_manifest`
- 前端和设计评审时，优先查看 demo script 生成的 JSON 与 `demo_summary.md`。

