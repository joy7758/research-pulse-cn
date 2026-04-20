# Import Formats Foundation v1

## Scope
- Pivot-2 adds a backend-only parser and normalizer foundation for paper metadata import.
- This phase is intentionally narrow:
  - no import UI
  - no database commit flow
  - no deduplication
  - no CNKI / Wanfang / VIP integration
  - no Zotero plugin or OAuth work

## Supported Formats
- `CSL JSON`
  - single object
  - array of objects
- `BibTeX`
  - common entry types such as `article`, `book`, `inproceedings`, `conference`, `thesis`, `phdthesis`, `mastersthesis`, `misc`
- `RIS`
  - multiple records separated by `ER`
- `Tabular spreadsheet-like input`
  - CSV
  - TSV
  - list-of-dict row payloads
- `PDF folder metadata placeholder`
  - filename-driven draft records only

## Normalized Fields
Each parsed record is normalized into one shared structure with at least:
- `title`
- `authors`
- `year`
- `venue`
- `abstract`
- `doi`
- `url`
- `keywords`
- `language`
- `source_format`
- `source_identifier`
- `raw_source_payload`
- `attachments`
- `notes`
- `warnings`
- `errors`

## Parser Contract
Each parser supports:
- format detection through `may_match(payload)`
- parsing through `parse(payload)`
- structured parse result with:
  - normalized records
  - top-level warnings
  - top-level errors
- record-level warnings and errors for malformed but recoverable data

The current service entrypoint is:
- `src/research_pulse_cn/services/import_formats.py`

The current shared models live in:
- `src/research_pulse_cn/domain/imports.py`
- `src/research_pulse_cn/schemas/imports.py`

## Format Notes

### CSL JSON
- Reads common fields such as:
  - `title`
  - `author`
  - `issued`
  - `container-title`
  - `publisher`
  - `DOI`
  - `URL`
  - `abstract`
  - `keyword`
  - `type`
- Missing or malformed fields become warnings instead of crashes where practical.

### BibTeX
- The parser is intentionally modest.
- It is suitable for Pivot-2 normalization and test coverage.
- It is not a full BibTeX engine.

### RIS
- The parser reads common tags such as:
  - `TY`
  - `TI` / `T1`
  - `AU` / `A1`
  - `PY` / `Y1`
  - `JO` / `T2` / `JF`
  - `DO`
  - `UR`
  - `AB`
  - `KW`
  - `ER`
- Unterminated records are recovered with warnings where possible.

### Tabular Input
- The current alias layer supports both English and Chinese headers.
- Examples:
  - `title / 题名 / 标题 / 篇名`
  - `authors / author / 作者`
  - `year / 年份 / 发表年份`
  - `venue / journal / 期刊 / 来源 / 会议`
  - `abstract / 摘要`
  - `keywords / tags / 关键词`
- Binary `.xlsx` parsing is deferred in v1 unless the repository later adopts a justified dependency.

### PDF Folder Placeholder
- Pivot-2 does not parse PDF content.
- Pivot-2 does not add OCR.
- Pivot-2 does not extract embedded PDF metadata.
- The placeholder creates draft records from filenames only and attaches explicit completeness warnings.

## Examples

### CSL JSON
```json
{
  "title": "Import Foundations for Research Pulse",
  "author": [{"given": "Alice", "family": "Zhang"}],
  "issued": {"date-parts": [[2024]]},
  "container-title": ["Journal of Import Systems"],
  "DOI": "10.1000/import.1"
}
```

### BibTeX
```bibtex
@article{zhang2024import,
  title = {Import Foundations for Research Pulse},
  author = {Alice Zhang and Bo Li},
  year = {2024},
  journal = {Journal of Import Systems}
}
```

### RIS
```text
TY  - JOUR
TI  - Import Foundations for Research Pulse
AU  - Alice Zhang
PY  - 2024
JO  - Journal of Import Systems
ER  -
```

### Tabular
```csv
title,authors,year,journal,keywords
Import Foundations,"Alice Zhang;Bo Li",2024,Journal of Import Systems,"imports;metadata"
```

## Known Limitations
- No import preview UI yet
- No import commit flow yet
- No deduplication yet
- No schema-to-database mapping yet
- No binary `.xlsx` parsing yet
- No real PDF metadata extraction yet
- No attachment ingestion yet
- No CNKI / Wanfang / VIP adapters yet
- No Zotero RDF / Better BibTeX compatibility layer yet

## Deferred Items
- CNKI import
- Wanfang import
- VIP import
- Zotero RDF compatibility
- Better BibTeX export compatibility
- binary `.xlsx` parsing
- real PDF metadata extraction
- import preview
- import commit
- deduplication
- UI
