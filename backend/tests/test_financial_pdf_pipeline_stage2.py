"""验证四阶段 PDF 管道 Stage 2 的视觉转录集成。"""

from unittest.mock import MagicMock, patch

import pytest

from app.engines.rebecca.parsers.financial_pdf_pipeline import FinancialPdfPipeline


@pytest.fixture
def sample_pdf_bytes():
    return b"fake-pdf-bytes"


@pytest.fixture
def mineru_result_with_tables():
    return {
        "success": True,
        "text": "## 合并资产负债表\n一些说明\n## 合并利润表\n一些说明",
        "tables": [
            [
                ["合并资产负债表", "2024年", "2023年"],
                ["资产总计", "1000", "900"],
                ["负债合计", "400", "350"],
                ["所有者权益合计", "600", "550"],
            ],
        ],
        "content_list": [],
        "metadata": {"page_count": 80},
        "error": "",
    }


def _make_transcriber_mock(rows=None, source="vision_minicpmv"):
    """构造一个总是返回指定 rows 的视觉转录器 mock。"""
    transcriber = MagicMock()
    transcribed = MagicMock()
    transcribed.rows = rows
    transcribed.source = source
    transcribed.pages = [10]
    transcribed.notes = []
    transcriber.transcribe_table.return_value = transcribed
    return transcriber


@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.MinerUParser")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.get_vision_transcriber")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.settings")
def test_stage2_uses_vision_transcription_when_enabled(
    mock_settings, mock_get_transcriber, mock_mineru_class, sample_pdf_bytes, mineru_result_with_tables
):
    mock_settings.ENABLE_VISION_STAGE2 = True
    mock_settings.ACCOUNTING_VALIDATION_TOLERANCE = 0.005
    mock_mineru_class.return_value.parse.return_value = mineru_result_with_tables

    vision_rows = [
        ["合并资产负债表", "2024年", "2023年"],
        ["资产总计", "1100", "950"],
        ["负债合计", "420", "360"],
        ["所有者权益合计", "680", "590"],
    ]
    mock_get_transcriber.return_value = _make_transcriber_mock(rows=vision_rows)

    pipeline = FinancialPdfPipeline()
    result = pipeline.parse_annual_report(sample_pdf_bytes, report_year=2024)

    assert result.success is True
    assert result.statements.balance_sheet is not None
    # 视觉转录后的资产总计应被采用
    assert result.statements.balance_sheet.set_index("field").loc["total_assets", "2024"] == 1100.0
    # 转录器应被调用
    pipeline.transcriber.transcribe_table.assert_called_once()


@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.MinerUParser")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.get_vision_transcriber")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.settings")
def test_stage2_falls_back_to_mineru_when_vision_fails(
    mock_settings, mock_get_transcriber, mock_mineru_class, sample_pdf_bytes, mineru_result_with_tables
):
    mock_settings.ENABLE_VISION_STAGE2 = True
    mock_settings.ACCOUNTING_VALIDATION_TOLERANCE = 0.005
    mock_mineru_class.return_value.parse.return_value = mineru_result_with_tables

    # 视觉转录返回空表格 -> 应回退到 MinerU 结果
    mock_get_transcriber.return_value = _make_transcriber_mock(rows=[], source="vision_minicpmv")

    pipeline = FinancialPdfPipeline()
    result = pipeline.parse_annual_report(sample_pdf_bytes, report_year=2024)

    assert result.success is True
    assert result.statements.balance_sheet is not None
    # 应使用 MinerU 原始结果
    assert result.statements.balance_sheet.set_index("field").loc["total_assets", "2024"] == 1000.0


@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.MinerUParser")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.get_vision_transcriber")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.settings")
def test_stage2_skips_vision_when_disabled(
    mock_settings, mock_get_transcriber, mock_mineru_class, sample_pdf_bytes, mineru_result_with_tables
):
    mock_settings.ENABLE_VISION_STAGE2 = False
    mock_settings.ACCOUNTING_VALIDATION_TOLERANCE = 0.005
    mock_mineru_class.return_value.parse.return_value = mineru_result_with_tables
    mock_get_transcriber.return_value = _make_transcriber_mock(rows=[])

    pipeline = FinancialPdfPipeline()
    result = pipeline.parse_annual_report(sample_pdf_bytes, report_year=2024)

    assert result.success is True
    # 视觉转录器不应被调用
    pipeline.transcriber.transcribe_table.assert_not_called()
