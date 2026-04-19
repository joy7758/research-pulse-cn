import json

from research_pulse_cn.domain.enums import PaperImportSourceFormat
from research_pulse_cn.services.import_formats import (
    BibtexPaperImportParser,
    CslJsonPaperImportParser,
    PaperImportFormatService,
    PdfFolderPaperImportParser,
    RisPaperImportParser,
    TabularPaperImportParser,
    validate_import_payload_is_safe,
)


def test_csl_json_single_record_is_normalized() -> None:
    parser = CslJsonPaperImportParser()

    result = parser.parse(
        json.dumps(
            {
                "id": "paper-1",
                "title": "Clean-room Import Foundations",
                "author": [
                    {"given": "Alice", "family": "Zhang"},
                    {"literal": "Bo Li"},
                ],
                "issued": {"date-parts": [[2024, 4, 1]]},
                "container-title": ["Journal of Import Systems"],
                "DOI": "10.1000/test-doi",
                "URL": "https://example.com/paper-1",
                "abstract": "A parser foundation for structured paper import.",
                "keyword": "imports; metadata",
                "language": "en",
                "type": "article-journal",
            }
        )
    )

    assert result.source_format == PaperImportSourceFormat.CSL_JSON
    assert result.errors == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record.title == "Clean-room Import Foundations"
    assert record.authors == ["Alice Zhang", "Bo Li"]
    assert record.year == 2024
    assert record.venue == "Journal of Import Systems"
    assert record.doi == "10.1000/test-doi"
    assert record.keywords == ["imports", "metadata"]


def test_csl_json_array_is_supported() -> None:
    parser = CslJsonPaperImportParser()

    result = parser.parse(
        json.dumps(
            [
                {"title": "First CSL Record", "issued": {"date-parts": [[2022]]}},
                {"title": "Second CSL Record", "issued": {"raw": "2023-01-02"}},
            ]
        )
    )

    assert len(result.records) == 2
    assert [record.year for record in result.records] == [2022, 2023]


def test_malformed_csl_json_returns_structured_error() -> None:
    parser = CslJsonPaperImportParser()

    result = parser.parse('{"title": "broken"')

    assert result.records == []
    assert [problem.code for problem in result.errors] == ["invalid_json"]


def test_csl_json_invalid_year_becomes_warning() -> None:
    parser = CslJsonPaperImportParser()

    result = parser.parse(
        json.dumps(
            {
                "title": "Yearless Record",
                "issued": {"date-parts": [["unknown"]]},
            }
        )
    )

    assert result.errors == []
    assert result.records[0].year is None
    assert [problem.code for problem in result.records[0].warnings] == ["invalid_year"]


def test_bibtex_article_is_normalized() -> None:
    parser = BibtexPaperImportParser()

    result = parser.parse(
        """
        @article{smith2024import,
          title = {Import Foundations for Research Pulse},
          author = {Alice Zhang and Bo Li},
          year = {2024},
          journal = {Import Journal},
          doi = {10.1000/import.1},
          url = {https://example.com/import.1},
          abstract = {Structured import metadata.},
          keywords = {imports; metadata}
        }
        """
    )

    assert result.errors == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record.source_identifier == "smith2024import"
    assert record.title == "Import Foundations for Research Pulse"
    assert record.authors == ["Alice Zhang", "Bo Li"]
    assert record.year == 2024
    assert record.venue == "Import Journal"


def test_bibtex_inproceedings_is_normalized() -> None:
    parser = BibtexPaperImportParser()

    result = parser.parse(
        """
        @inproceedings{zhang2025pivot,
          title = {Pivoting Toward Paper Imports},
          author = {Alice Zhang and Chen Wu},
          year = {2025},
          booktitle = {Proceedings of ImportConf},
          publisher = {ImportConf Press},
          keywords = {pivot,imports}
        }
        """
    )

    assert result.errors == []
    record = result.records[0]
    assert record.title == "Pivoting Toward Paper Imports"
    assert record.venue == "Proceedings of ImportConf"
    assert record.keywords == ["pivot", "imports"]


def test_bibtex_multiple_records_are_supported() -> None:
    parser = BibtexPaperImportParser()

    result = parser.parse(
        """
        @article{first, title = {First Record}, author = {Alice Zhang}, year = {2022}}
        @misc{second, title = {Second Record}, author = {Bo Li}, year = {2023}}
        """
    )

    assert len(result.records) == 2
    assert [record.title for record in result.records] == ["First Record", "Second Record"]


def test_malformed_bibtex_returns_error() -> None:
    parser = BibtexPaperImportParser()

    result = parser.parse("@article{broken, title={Missing close brace}")

    assert result.records == []
    assert [problem.code for problem in result.errors] == ["invalid_bibtex", "invalid_bibtex"]


def test_ris_single_record_is_normalized() -> None:
    parser = RisPaperImportParser()

    result = parser.parse(
        """
        TY  - JOUR
        TI  - RIS Import Record
        AU  - Alice Zhang
        AU  - Bo Li
        PY  - 2021
        JO  - RIS Journal
        DO  - 10.1000/ris.1
        UR  - https://example.com/ris.1
        AB  - RIS metadata import.
        KW  - ris
        KW  - metadata
        ER  -
        """
    )

    assert result.errors == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record.title == "RIS Import Record"
    assert record.authors == ["Alice Zhang", "Bo Li"]
    assert record.year == 2021
    assert record.venue == "RIS Journal"
    assert record.keywords == ["ris", "metadata"]


def test_ris_multiple_records_are_supported() -> None:
    parser = RisPaperImportParser()

    result = parser.parse(
        """
        TY  - JOUR
        TI  - First RIS
        ER  -
        TY  - CONF
        TI  - Second RIS
        ER  -
        """
    )

    assert [record.title for record in result.records] == ["First RIS", "Second RIS"]


def test_malformed_ris_returns_error() -> None:
    parser = RisPaperImportParser()

    result = parser.parse("this is not ris")

    assert result.records == []
    assert [problem.code for problem in result.errors] == ["invalid_ris"]


def test_tabular_parser_supports_english_aliases() -> None:
    parser = TabularPaperImportParser()

    result = parser.parse(
        "title,authors,year,journal,abstract,doi,url,keywords\n"
        "English Table Record,Alice Zhang;Bo Li,2024,Tabular Journal,"
        "Table import foundation,10.1000/table.1,https://example.com/table.1,"
        '"imports;tabular"\n'
    )

    assert result.errors == []
    record = result.records[0]
    assert record.title == "English Table Record"
    assert record.authors == ["Alice Zhang", "Bo Li"]
    assert record.year == 2024
    assert record.venue == "Tabular Journal"
    assert record.keywords == ["imports", "tabular"]


def test_tabular_parser_supports_chinese_aliases() -> None:
    parser = TabularPaperImportParser()

    result = parser.parse(
        "标题\t作者\t发表年份\t来源\t摘要\t关键词\t链接\n"
        "中文表格记录\t张三；李四\t2023\t研究进展\t中文导入基础\t导入；论文\t"
        "https://example.com/cn\n"
    )

    assert result.errors == []
    record = result.records[0]
    assert record.title == "中文表格记录"
    assert record.authors == ["张三", "李四"]
    assert record.year == 2023
    assert record.venue == "研究进展"
    assert record.keywords == ["导入", "论文"]


def test_pdf_folder_placeholder_builds_attachment_placeholders() -> None:
    parser = PdfFolderPaperImportParser()

    result = parser.parse(
        [
            "papers/Deep_Learning_for_Import_Systems.pdf",
            {"path": "/tmp/Structured Research Pulse.pdf"},
        ]
    )

    assert result.errors == []
    assert len(result.records) == 2
    first_record = result.records[0]
    assert first_record.title == "Deep Learning for Import Systems"
    assert first_record.attachments[0].media_type == "application/pdf"
    assert {problem.code for problem in first_record.warnings} == {
        "pdf_metadata_deferred",
        "metadata_incomplete",
    }


def test_warning_and_error_behavior_remains_structured() -> None:
    service = PaperImportFormatService()

    detected_formats = service.detect_formats(
        '[{"title": "Structured Warnings", "issued": {"date-parts": [["bad"]]}}]'
    )
    parsed = service.parse(
        '[{"title": "Structured Warnings", "issued": {"date-parts": [["bad"]]}}]',
        source_format=PaperImportSourceFormat.CSL_JSON,
    )

    assert detected_formats == [PaperImportSourceFormat.CSL_JSON]
    assert parsed.errors == []
    assert [problem.code for problem in parsed.records[0].warnings] == ["invalid_year"]


def test_validate_import_payload_is_safe_rejects_unsafe_field_names() -> None:
    problems = validate_import_payload_is_safe(
        {
            "records": [
                {"title": "Safe"},
                {"sourceFile": "/tmp/unsafe.pdf"},
            ]
        }
    )

    assert [problem.code for problem in problems] == ["unsafe_field_detected"]
