"""Import format foundations for paper metadata normalization."""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import PurePath
from typing import Any

from research_pulse_cn.domain.enums import PaperImportSourceFormat
from research_pulse_cn.domain.imports import PaperImportParser
from research_pulse_cn.schemas.imports import (
    PaperImportAttachmentPlaceholder,
    PaperImportParseResult,
    PaperImportProblem,
    PaperImportRecord,
)

TABULAR_COLUMN_ALIASES: dict[str, set[str]] = {
    "title": {"title", "题名", "标题", "篇名"},
    "authors": {"authors", "author", "作者"},
    "year": {"year", "年份", "发表年份", "年"},
    "venue": {"venue", "journal", "期刊", "来源", "会议", "conference"},
    "abstract": {"abstract", "摘要"},
    "doi": {"doi"},
    "url": {"url", "链接", "网址"},
    "keywords": {"keywords", "keyword", "tags", "tag", "关键词"},
    "language": {"language", "语言"},
}

UNSAFE_IMPORT_FIELD_TOKENS = (
    "token",
    "secret",
    "password",
    "rawalias",
    "rawsharetoken",
    "aliashash",
    "tokenhash",
    "localpath",
    "absolutepath",
    "sourcefile",
    "responsepayload",
)


class PaperImportFormatService:
    """Registry and entrypoint for supported paper import parsers."""

    def __init__(self, parsers: Sequence[PaperImportParser] | None = None) -> None:
        parser_list = list(parsers or get_default_paper_import_parsers())
        self._parsers = {parser.source_format: parser for parser in parser_list}
        self._ordered_formats = [parser.source_format for parser in parser_list]

    def available_formats(self) -> list[PaperImportSourceFormat]:
        return list(self._ordered_formats)

    def detect_formats(self, payload: Any) -> list[PaperImportSourceFormat]:
        return [
            parser.source_format for parser in self._parsers.values() if parser.may_match(payload)
        ]

    def parse(
        self,
        payload: Any,
        *,
        source_format: PaperImportSourceFormat,
    ) -> PaperImportParseResult:
        parser = self._parsers.get(source_format)
        if parser is None:
            raise ValueError(f"unsupported import source format: {source_format}")
        return parser.parse(payload)


class CslJsonPaperImportParser:
    """Parse CSL JSON objects or arrays into normalized records."""

    source_format = PaperImportSourceFormat.CSL_JSON

    def may_match(self, payload: Any) -> bool:
        normalized = _load_json_payload(payload)
        if normalized is None:
            return False
        if isinstance(normalized, Mapping):
            return _looks_like_csl_record(normalized)
        if isinstance(normalized, list):
            return bool(normalized) and all(
                isinstance(item, Mapping) and _looks_like_csl_record(item) for item in normalized
            )
        return False

    def parse(self, payload: Any) -> PaperImportParseResult:
        result = _new_result(self.source_format)
        normalized = _load_json_payload(payload)
        if normalized is None:
            result.errors.append(
                _problem("invalid_json", "Input is not valid JSON.", field="payload")
            )
            return result
        if isinstance(normalized, Mapping):
            result.records.append(self._parse_record(normalized, index=1))
            return result
        if not isinstance(normalized, list):
            result.errors.append(
                _problem(
                    "invalid_csl_top_level",
                    "CSL JSON input must be an object or an array of objects.",
                    field="payload",
                )
            )
            return result

        for index, item in enumerate(normalized, start=1):
            if not isinstance(item, Mapping):
                result.errors.append(
                    _problem(
                        "invalid_csl_record",
                        f"CSL JSON array item {index} is not an object.",
                        field=f"records[{index - 1}]",
                    )
                )
                continue
            result.records.append(self._parse_record(item, index=index))
        return result

    def _parse_record(self, payload: Mapping[str, Any], *, index: int) -> PaperImportRecord:
        warnings: list[PaperImportProblem] = []
        errors: list[PaperImportProblem] = []
        title = _coerce_first_text(payload.get("title"))
        authors, author_warnings = _parse_csl_authors(payload.get("author"))
        warnings.extend(author_warnings)
        year = _parse_csl_year(payload.get("issued"))
        if payload.get("issued") is not None and year is None:
            warnings.append(
                _problem("invalid_year", "Could not parse year from CSL issued field.", "issued")
            )
        venue = _coerce_first_text(payload.get("container-title")) or _coerce_text(
            payload.get("publisher")
        )
        keywords = _coerce_keyword_list(payload.get("keyword"))
        if not title:
            warnings.append(
                _problem("missing_title", "Imported record is missing a title.", "title")
            )

        return PaperImportRecord(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=_coerce_text(payload.get("abstract")),
            doi=_normalize_doi(payload.get("DOI")),
            url=_coerce_text(payload.get("URL")),
            keywords=keywords,
            language=_coerce_text(payload.get("language")),
            source_format=self.source_format,
            source_identifier=_coerce_text(payload.get("id"))
            or _normalize_doi(payload.get("DOI"))
            or _coerce_text(payload.get("URL"))
            or f"csl-{index}",
            raw_source_payload=_json_safe_mapping(payload),
            warnings=warnings,
            errors=errors,
        )


class BibtexPaperImportParser:
    """Parse common BibTeX entries into normalized records."""

    source_format = PaperImportSourceFormat.BIBTEX

    def may_match(self, payload: Any) -> bool:
        text = _coerce_payload_text(payload)
        if text is None:
            return False
        return re.search(r"@\w+\s*[{(]", text) is not None

    def parse(self, payload: Any) -> PaperImportParseResult:
        result = _new_result(self.source_format)
        text = _coerce_payload_text(payload)
        if text is None:
            result.errors.append(
                _problem("invalid_bibtex", "BibTeX input must be text.", field="payload")
            )
            return result
        entries, extract_errors = _extract_bibtex_entries(text)
        result.errors.extend(extract_errors)
        if not entries:
            result.errors.append(
                _problem("invalid_bibtex", "No BibTeX entries were found.", field="payload")
            )
            return result

        for index, entry_text in enumerate(entries, start=1):
            record, problems = _parse_bibtex_entry(entry_text, index=index)
            if record is None:
                result.errors.extend(problems)
                continue
            for problem in problems:
                if problem.code.startswith("invalid_") or problem.code.startswith("malformed_"):
                    record.errors.append(problem)
                else:
                    record.warnings.append(problem)
            result.records.append(record)
        return result


class RisPaperImportParser:
    """Parse RIS text records separated by ER markers."""

    source_format = PaperImportSourceFormat.RIS

    def may_match(self, payload: Any) -> bool:
        text = _coerce_payload_text(payload)
        if text is None:
            return False
        return "TY  -" in text or "ER  -" in text

    def parse(self, payload: Any) -> PaperImportParseResult:
        result = _new_result(self.source_format)
        text = _coerce_payload_text(payload)
        if text is None:
            result.errors.append(_problem("invalid_ris", "RIS input must be text.", "payload"))
            return result

        records, problems = _parse_ris_records(text)
        for problem in problems:
            if problem.code.startswith("invalid_"):
                result.errors.append(problem)
            else:
                result.warnings.append(problem)
        if not records:
            result.errors.append(
                _problem("invalid_ris", "No RIS records were recognized.", field="payload")
            )
            return result

        for index, payload_record in enumerate(records, start=1):
            result.records.append(_build_ris_record(payload_record, index=index))
        return result


class TabularPaperImportParser:
    """Parse spreadsheet-like rows from CSV, TSV, or mapping sequences."""

    source_format = PaperImportSourceFormat.TABULAR

    def may_match(self, payload: Any) -> bool:
        rows = _load_tabular_rows(payload)
        if rows is None:
            return False
        _, recognized_headers = _resolve_tabular_aliases(rows)
        return bool(recognized_headers)

    def parse(self, payload: Any) -> PaperImportParseResult:
        result = _new_result(self.source_format)
        rows = _load_tabular_rows(payload)
        if rows is None:
            result.errors.append(
                _problem(
                    "invalid_tabular",
                    "Tabular input must be CSV/TSV text or a list of row mappings.",
                    field="payload",
                )
            )
            return result

        alias_map, recognized_headers = _resolve_tabular_aliases(rows)
        if not recognized_headers:
            result.errors.append(
                _problem(
                    "missing_known_columns",
                    "Tabular input does not contain any supported column aliases.",
                    field="columns",
                )
            )
            return result

        for index, row in enumerate(rows, start=1):
            result.records.append(_build_tabular_record(row, alias_map=alias_map, index=index))
        return result


class PdfFolderPaperImportParser:
    """Create placeholder records from PDF-like file descriptors."""

    source_format = PaperImportSourceFormat.PDF_FOLDER

    def may_match(self, payload: Any) -> bool:
        descriptors = _load_pdf_descriptors(payload)
        return bool(descriptors)

    def parse(self, payload: Any) -> PaperImportParseResult:
        result = _new_result(self.source_format)
        descriptors = _load_pdf_descriptors(payload)
        if not descriptors:
            result.errors.append(
                _problem(
                    "invalid_pdf_folder_input",
                    "PDF placeholder input must be a list of PDF-like filenames or descriptors.",
                    field="payload",
                )
            )
            return result

        for descriptor in descriptors:
            filename = descriptor["filename"]
            inferred_title = _infer_title_from_filename(filename)
            result.records.append(
                PaperImportRecord(
                    title=inferred_title,
                    source_format=self.source_format,
                    source_identifier=filename,
                    raw_source_payload={"filename": filename},
                    attachments=[
                        PaperImportAttachmentPlaceholder(
                            label=filename,
                            path_hint=filename,
                            media_type="application/pdf",
                        )
                    ],
                    warnings=[
                        _problem(
                            "pdf_metadata_deferred",
                            "Real PDF metadata extraction is deferred in Pivot-2.",
                            "attachments",
                        ),
                        _problem(
                            "metadata_incomplete",
                            "Record is based on filename inference only.",
                            "title",
                        ),
                    ],
                    errors=[],
                )
            )
        return result


def get_default_paper_import_parsers() -> list[PaperImportParser]:
    """Return the default parser set used by later import preview phases."""

    return [
        CslJsonPaperImportParser(),
        BibtexPaperImportParser(),
        RisPaperImportParser(),
        TabularPaperImportParser(),
        PdfFolderPaperImportParser(),
    ]


def _new_result(source_format: PaperImportSourceFormat) -> PaperImportParseResult:
    return PaperImportParseResult(
        source_format=source_format,
        parsed_at=datetime.now(UTC),
    )


def _problem(code: str, message: str, field: str | None = None) -> PaperImportProblem:
    return PaperImportProblem(code=code, message=message, field=field)


def _load_json_payload(payload: Any) -> Any | None:
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(payload, list):
        return payload
    return None


def _looks_like_csl_record(payload: Mapping[str, Any]) -> bool:
    keys = set(payload)
    return bool(keys & {"title", "author", "issued", "DOI", "URL", "container-title", "type"})


def _coerce_payload_text(payload: Any) -> str | None:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = _normalize_whitespace(value)
        return cleaned or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _coerce_first_text(value: Any) -> str | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            text = _coerce_text(item)
            if text:
                return text
        return None
    return _coerce_text(value)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_doi(value: Any) -> str | None:
    text = _coerce_text(value)
    if not text:
        return None
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    normalized = re.sub(r"^doi:\s*", "", normalized, flags=re.IGNORECASE)
    return normalized or None


def _parse_csl_authors(value: Any) -> tuple[list[str], list[PaperImportProblem]]:
    warnings: list[PaperImportProblem] = []
    if value is None:
        return [], warnings
    if not isinstance(value, list):
        return [], [_problem("invalid_author", "CSL author field must be a list.", "author")]

    authors: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            warnings.append(
                _problem("invalid_author", "Skipped malformed CSL author item.", "author")
            )
            continue
        literal = _coerce_text(item.get("literal"))
        if literal:
            authors.append(literal)
            continue
        given = _coerce_text(item.get("given"))
        family = _coerce_text(item.get("family"))
        full_name = _normalize_whitespace(" ".join(part for part in [given, family] if part))
        if full_name:
            authors.append(full_name)
            continue
        warnings.append(_problem("invalid_author", "Skipped empty CSL author item.", "author"))
    return _dedupe_preserve_order(authors), warnings


def _parse_csl_year(value: Any) -> int | None:
    if isinstance(value, Mapping):
        date_parts = value.get("date-parts")
        if isinstance(date_parts, list) and date_parts:
            first_part = date_parts[0]
            if isinstance(first_part, Sequence) and first_part:
                return _parse_year(first_part[0])
        return _parse_year(value.get("raw"))
    return _parse_year(value)


def _parse_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = _coerce_text(value)
    if not text:
        return None
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    return int(match.group(0))


def _coerce_keyword_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [_coerce_text(item) for item in value]
        return _dedupe_preserve_order([item for item in items if item])
    text = _coerce_text(value)
    if not text:
        return []
    parts = re.split(r"[;,；、|]\s*", text)
    return _dedupe_preserve_order(
        [part for part in (_normalize_whitespace(item) for item in parts) if part]
    )


def _json_safe_mapping(payload: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload))


def _extract_bibtex_entries(text: str) -> tuple[list[str], list[PaperImportProblem]]:
    entries: list[str] = []
    errors: list[PaperImportProblem] = []
    position = 0
    while True:
        at_index = text.find("@", position)
        if at_index == -1:
            break
        open_index = _find_bibtex_open_delimiter(text, at_index)
        if open_index is None:
            errors.append(
                _problem(
                    "invalid_bibtex", "Found BibTeX entry without an opening delimiter.", "payload"
                )
            )
            break
        open_char = text[open_index]
        close_char = "}" if open_char == "{" else ")"
        end_index = _read_balanced_block_end(text, open_index, open_char, close_char)
        if end_index is None:
            errors.append(_problem("invalid_bibtex", "Found unterminated BibTeX entry.", "payload"))
            break
        entries.append(text[at_index : end_index + 1])
        position = end_index + 1
    return entries, errors


def _find_bibtex_open_delimiter(text: str, at_index: int) -> int | None:
    for index in range(at_index + 1, len(text)):
        if text[index] in "{(":
            return index
        if text[index] == "\n":
            continue
    return None


def _read_balanced_block_end(
    text: str,
    start_index: int,
    open_char: str,
    close_char: str,
) -> int | None:
    depth = 0
    in_quotes = False
    escaped = False
    for index in range(start_index, len(text)):
        char = text[index]
        if char == '"' and not escaped:
            in_quotes = not in_quotes
        if not in_quotes:
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    return index
        escaped = char == "\\" and not escaped
    return None


def _parse_bibtex_entry(
    entry_text: str,
    *,
    index: int,
) -> tuple[PaperImportRecord | None, list[PaperImportProblem]]:
    problems: list[PaperImportProblem] = []
    entry_text = entry_text.strip()
    open_index = _find_bibtex_open_delimiter(entry_text, 0)
    if open_index is None:
        return None, [_problem("invalid_bibtex", "Malformed BibTeX entry header.", "payload")]

    entry_type = entry_text[1:open_index].strip().lower()
    body = entry_text[open_index + 1 : -1].strip()
    comma_index = _find_top_level_comma(body)
    if comma_index is None:
        return None, [
            _problem("invalid_bibtex", "BibTeX entry is missing its field body.", "payload")
        ]
    entry_key = _normalize_whitespace(body[:comma_index])
    fields_text = body[comma_index + 1 :]
    fields, field_problems = _parse_bibtex_fields(fields_text)
    problems.extend(field_problems)

    title = _coerce_text(fields.get("title"))
    if not title:
        problems.append(_problem("missing_title", "Imported record is missing a title.", "title"))

    authors = _split_bibtex_authors(fields.get("author"))
    year = _parse_year(fields.get("year"))
    if fields.get("year") and year is None:
        problems.append(_problem("invalid_year", "Could not parse BibTeX year.", "year"))

    record = PaperImportRecord(
        title=title,
        authors=authors,
        year=year,
        venue=_coerce_text(fields.get("journal"))
        or _coerce_text(fields.get("booktitle"))
        or _coerce_text(fields.get("publisher"))
        or _coerce_text(fields.get("school")),
        abstract=_coerce_text(fields.get("abstract")),
        doi=_normalize_doi(fields.get("doi")),
        url=_coerce_text(fields.get("url")),
        keywords=_coerce_keyword_list(fields.get("keywords")),
        language=_coerce_text(fields.get("language")),
        source_format=PaperImportSourceFormat.BIBTEX,
        source_identifier=entry_key or _normalize_doi(fields.get("doi")) or f"bibtex-{index}",
        raw_source_payload={
            "entry_type": entry_type,
            "entry_key": entry_key,
            "fields": fields,
        },
    )
    return record, problems


def _find_top_level_comma(text: str) -> int | None:
    brace_depth = 0
    quote_depth = False
    escaped = False
    for index, char in enumerate(text):
        if char == '"' and not escaped:
            quote_depth = not quote_depth
        if quote_depth:
            escaped = char == "\\" and not escaped
            continue
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth = max(0, brace_depth - 1)
        elif char == "," and brace_depth == 0:
            return index
        escaped = char == "\\" and not escaped
    return None


def _parse_bibtex_fields(text: str) -> tuple[dict[str, str], list[PaperImportProblem]]:
    fields: dict[str, str] = {}
    problems: list[PaperImportProblem] = []
    index = 0
    while index < len(text):
        while index < len(text) and text[index] in {" ", "\n", "\t", "\r", ","}:
            index += 1
        if index >= len(text):
            break

        key_start = index
        while index < len(text) and text[index] not in {"=", "\n"}:
            index += 1
        if index >= len(text) or text[index] != "=":
            problems.append(
                _problem("malformed_field", "Skipped malformed BibTeX field.", "fields")
            )
            break
        field_name = _normalize_whitespace(text[key_start:index]).lower()
        index += 1
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            problems.append(
                _problem("malformed_field", "Skipped BibTeX field without a value.", field_name)
            )
            break

        value, index = _read_bibtex_value(text, index)
        if value is None:
            problems.append(
                _problem(
                    "malformed_field", f"Skipped malformed BibTeX field '{field_name}'.", field_name
                )
            )
            break
        fields[field_name] = value
    return fields, problems


def _read_bibtex_value(text: str, start_index: int) -> tuple[str | None, int]:
    char = text[start_index]
    if char == "{":
        end_index = _read_balanced_block_end(text, start_index, "{", "}")
        if end_index is None:
            return None, len(text)
        value = text[start_index + 1 : end_index]
        cleaned = _clean_bibtex_text(value)
        return cleaned, end_index + 1
    if char == '"':
        end_index = _read_bibtex_quoted_end(text, start_index)
        if end_index is None:
            return None, len(text)
        value = text[start_index + 1 : end_index]
        cleaned = _clean_bibtex_text(value)
        return cleaned, end_index + 1

    index = start_index
    while index < len(text) and text[index] != ",":
        index += 1
    value = text[start_index:index].strip()
    return _clean_bibtex_text(value), index


def _read_bibtex_quoted_end(text: str, start_index: int) -> int | None:
    escaped = False
    for index in range(start_index + 1, len(text)):
        char = text[index]
        if char == '"' and not escaped:
            return index
        escaped = char == "\\" and not escaped
    return None


def _clean_bibtex_text(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.replace("\n", " ")
    cleaned = re.sub(r"[{}]", "", cleaned)
    return _normalize_whitespace(cleaned)


def _split_bibtex_authors(value: Any) -> list[str]:
    text = _coerce_text(value)
    if not text:
        return []
    parts = [item.strip() for item in re.split(r"\band\b", text) if item.strip()]
    return _dedupe_preserve_order([_normalize_whitespace(part) for part in parts])


def _parse_ris_records(text: str) -> tuple[list[dict[str, list[str]]], list[PaperImportProblem]]:
    records: list[dict[str, list[str]]] = []
    problems: list[PaperImportProblem] = []
    current: dict[str, list[str]] | None = None
    current_tag: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line.strip():
            continue
        match = re.match(r"^([A-Z0-9]{2})\s{2}-\s?(.*)$", line)
        if match:
            tag, value = match.groups()
            if tag == "TY":
                if current is not None:
                    problems.append(
                        _problem(
                            "missing_er",
                            "RIS record ended without an ER terminator; recovered record anyway.",
                            f"line:{line_number}",
                        )
                    )
                    records.append(current)
                current = {"TY": [_normalize_whitespace(value)]}
                current_tag = "TY"
                continue
            if current is None:
                problems.append(
                    _problem(
                        "ignored_ris_line",
                        "Skipped RIS line outside a record.",
                        f"line:{line_number}",
                    )
                )
                continue
            if tag == "ER":
                records.append(current)
                current = None
                current_tag = None
                continue
            current.setdefault(tag, []).append(_normalize_whitespace(value))
            current_tag = tag
            continue

        if current is not None and current_tag is not None:
            current[current_tag][-1] = _normalize_whitespace(
                f"{current[current_tag][-1]} {line.strip()}"
            )
            problems.append(
                _problem(
                    "continued_line",
                    "Folded one RIS continuation line into the previous tag value.",
                    f"line:{line_number}",
                )
            )
            continue
        problems.append(
            _problem(
                "malformed_ris_line",
                "Skipped malformed RIS line.",
                f"line:{line_number}",
            )
        )

    if current is not None:
        problems.append(
            _problem("missing_er", "RIS input ended without a closing ER line.", "payload")
        )
        records.append(current)
    return records, problems


def _build_ris_record(payload: Mapping[str, list[str]], *, index: int) -> PaperImportRecord:
    title = _first_ris_value(payload, "TI", "T1")
    warnings: list[PaperImportProblem] = []
    if not title:
        warnings.append(_problem("missing_title", "Imported record is missing a title.", "TI"))

    return PaperImportRecord(
        title=title,
        authors=_dedupe_preserve_order(payload.get("AU", []) + payload.get("A1", [])),
        year=_parse_year(_first_ris_value(payload, "PY", "Y1")),
        venue=_first_ris_value(payload, "JO", "T2", "JF"),
        abstract=_first_ris_value(payload, "AB"),
        doi=_normalize_doi(_first_ris_value(payload, "DO")),
        url=_first_ris_value(payload, "UR"),
        keywords=_dedupe_preserve_order(payload.get("KW", [])),
        language=_first_ris_value(payload, "LA"),
        source_format=PaperImportSourceFormat.RIS,
        source_identifier=_normalize_doi(_first_ris_value(payload, "DO")) or f"ris-{index}",
        raw_source_payload={key: list(value) for key, value in payload.items()},
        warnings=warnings,
        errors=[],
    )


def _first_ris_value(payload: Mapping[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        values = payload.get(key)
        if values:
            return _coerce_text(values[0])
    return None


def _load_tabular_rows(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        rows: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, Mapping):
                return None
            rows.append({str(key): value for key, value in item.items()})
        return rows

    text = _coerce_payload_text(payload)
    if text is None:
        return None
    delimiter = _guess_tabular_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        return None
    return [{key or "": value for key, value in row.items()} for row in reader]


def _guess_tabular_delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:5])
    try:
        return csv.Sniffer().sniff(sample, delimiters=",\t;").delimiter
    except csv.Error:
        if sample.count("\t") >= sample.count(","):
            return "\t"
        return ","


def _resolve_tabular_aliases(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], set[str]]:
    if not rows:
        return {}, set()
    alias_map: dict[str, str] = {}
    recognized_headers: set[str] = set()
    for header in rows[0]:
        normalized_header = _normalize_header(header)
        for canonical_field, aliases in TABULAR_COLUMN_ALIASES.items():
            if normalized_header in {_normalize_header(alias) for alias in aliases}:
                alias_map.setdefault(canonical_field, header)
                recognized_headers.add(header)
                break
    return alias_map, recognized_headers


def _build_tabular_record(
    row: Mapping[str, Any],
    *,
    alias_map: Mapping[str, str],
    index: int,
) -> PaperImportRecord:
    title = _coerce_text(row.get(alias_map.get("title", "")))
    warnings: list[PaperImportProblem] = []
    if not title:
        warnings.append(_problem("missing_title", "Imported row is missing a title.", "title"))

    authors = _split_author_text(_coerce_text(row.get(alias_map.get("authors", ""))))
    keywords = _coerce_keyword_list(row.get(alias_map.get("keywords", "")))
    return PaperImportRecord(
        title=title,
        authors=authors,
        year=_parse_year(row.get(alias_map.get("year", ""))),
        venue=_coerce_text(row.get(alias_map.get("venue", ""))),
        abstract=_coerce_text(row.get(alias_map.get("abstract", ""))),
        doi=_normalize_doi(row.get(alias_map.get("doi", ""))),
        url=_coerce_text(row.get(alias_map.get("url", ""))),
        keywords=keywords,
        language=_coerce_text(row.get(alias_map.get("language", ""))),
        source_format=PaperImportSourceFormat.TABULAR,
        source_identifier=_normalize_doi(row.get(alias_map.get("doi", ""))) or f"row-{index}",
        raw_source_payload={str(key): value for key, value in row.items()},
        warnings=warnings,
        errors=[],
    )


def _normalize_header(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", value).strip().lower()


def _split_author_text(text: str | None) -> list[str]:
    if not text:
        return []
    for separator in (";", "；", "\n", " and ", "、", "|"):
        if separator in text:
            parts = [item.strip() for item in text.split(separator) if item.strip()]
            return _dedupe_preserve_order(parts)
    if "," in text:
        comma_parts = [item.strip() for item in text.split(",") if item.strip()]
        if len(comma_parts) == 2 and all(" " in item for item in comma_parts):
            return _dedupe_preserve_order(comma_parts)
        if len(comma_parts) > 2:
            return _dedupe_preserve_order(comma_parts)
    return [text]


def _load_pdf_descriptors(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes, bytearray)):
        return []
    descriptors: list[dict[str, str]] = []
    for item in payload:
        if isinstance(item, str):
            filename = PurePath(item).name
        elif isinstance(item, Mapping):
            filename = _coerce_text(item.get("filename") or item.get("name") or item.get("path"))
        else:
            continue
        if not filename or not filename.lower().endswith(".pdf"):
            continue
        descriptors.append({"filename": filename})
    return descriptors


def _infer_title_from_filename(filename: str) -> str:
    stem = PurePath(filename).stem
    cleaned = re.sub(r"[_\-]+", " ", stem)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or filename


def _dedupe_preserve_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def validate_import_payload_is_safe(payload: Any) -> list[PaperImportProblem]:
    """Validate nested payload keys against known unsafe field names."""

    problems: list[PaperImportProblem] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                normalized = _normalize_header(str(key))
                if any(token in normalized for token in UNSAFE_IMPORT_FIELD_TOKENS):
                    problems.append(
                        _problem(
                            "unsafe_field_detected",
                            "Detected an unsafe field name in parsed payload.",
                            path or str(key),
                        )
                    )
                _walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")

    _walk(payload, "")
    return problems
