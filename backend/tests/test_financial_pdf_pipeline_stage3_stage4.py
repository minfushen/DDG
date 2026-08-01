"""验证四阶段 PDF 管道 Stage 3（勾稽引擎）与 Stage 4（视觉兜底）。"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.engines.rebecca.parsers.financial_pdf_pipeline import (
    AccountingValidator,
    FinancialPdfPipeline,
    FinancialStatementData,
)


def make_statements(**kwargs):
    """构造三大表 DataFrame，未传入的表为 None。"""
    def _df(records):
        if not records:
            return None
        return pd.DataFrame(records)

    return FinancialStatementData(
        income_statement=_df(kwargs.get("income", [])),
        balance_sheet=_df(kwargs.get("balance", [])),
        cash_flow=_df(kwargs.get("cash", [])),
    )


def test_validator_has_23_rules():
    validator = AccountingValidator()
    assert len(validator.rules) == 23


def test_validator_red_green_yellow_status():
    """资产负债表不平衡应标红，数据缺失应标记为 uncertain。"""
    statements = make_statements(
        balance=[
            {"field": "total_assets", "label": "资产总计", "2024": 1000.0},
            {"field": "total_liabilities", "label": "负债合计", "2024": 400.0},
            {"field": "total_equity", "label": "所有者权益合计", "2024": 500.0},  # 不平衡
        ],
    )
    validator = AccountingValidator(tolerance=0.005)
    result = validator.validate(statements)

    assert result["total"] == 23
    assert result["failed"] >= 1
    assert any("资产负债表平衡" in r["name"] and r["status"] == "failed" for r in result["rule_results"])
    assert any(r["status"] == "uncertain" for r in result["rule_results"])
    assert 0.0 <= result["auto_judgment_rate"] <= 1.0


def test_validator_balance_sheet_passes():
    statements = make_statements(
        balance=[
            {"field": "current_assets", "label": "流动资产合计", "2024": 600.0},
            {"field": "non_current_assets", "label": "非流动资产合计", "2024": 400.0},
            {"field": "total_assets", "label": "资产总计", "2024": 1000.0},
            {"field": "current_liabilities", "label": "流动负债合计", "2024": 300.0},
            {"field": "non_current_liabilities", "label": "非流动负债合计", "2024": 100.0},
            {"field": "total_liabilities", "label": "负债合计", "2024": 400.0},
            {"field": "total_equity", "label": "所有者权益合计", "2024": 600.0},
            {"field": "cash_and_equivalents", "label": "货币资金", "2024": 100.0},
            {"field": "accounts_receivable", "label": "应收账款", "2024": 80.0},
            {"field": "inventory", "label": "存货", "2024": 120.0},
        ],
        income=[
            {"field": "revenue", "label": "营业收入", "2024": 1000.0},
            {"field": "operating_cost", "label": "营业成本", "2024": 600.0},
            {"field": "operating_profit", "label": "营业利润", "2024": 200.0},
            {"field": "total_profit", "label": "利润总额", "2024": 210.0},
            {"field": "net_profit", "label": "净利润", "2024": 180.0},
            {"field": "net_profit_attributable_to_parent", "label": "归母净利润", "2024": 170.0},
        ],
        cash=[
            {"field": "operating_cash_inflow", "label": "经营流入", "2024": 500.0},
            {"field": "operating_cash_outflow", "label": "经营流出", "2024": 400.0},
            {"field": "net_operating_cash_flow", "label": "经营净额", "2024": 100.0},
            {"field": "net_investing_cash_flow", "label": "投资净额", "2024": -50.0},
            {"field": "net_financing_cash_flow", "label": "筹资净额", "2024": -30.0},
            {"field": "net_increase_in_cash", "label": "现金净增", "2024": 20.0},
        ],
    )
    validator = AccountingValidator(tolerance=0.02)
    result = validator.validate(statements)

    assert result["passed"] > result["failed"]
    balance_rule = next(r for r in result["rule_results"] if r["name"] == "资产负债表平衡")
    assert balance_rule["status"] == "passed"
    cash_rule = next(r for r in result["rule_results"] if r["name"] == "现金净增加额 = 经营 + 投资 + 筹资")
    assert cash_rule["status"] == "passed"


@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.MinerUParser")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.get_vision_transcriber")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.settings")
def test_stage4_vision_fallback_triggers_on_failed_validation(
    mock_settings, mock_get_transcriber, mock_mineru_class
):
    """Stage 3 勾稽失败且 ENABLE_VISION_STAGE4=True 时，应触发 Stage 4 视觉兜底。"""
    mock_settings.ENABLE_VISION_STAGE2 = False
    mock_settings.ENABLE_VISION_STAGE4 = True
    mock_settings.ACCOUNTING_VALIDATION_TOLERANCE = 0.005

    mineru_result = {
        "success": True,
        "text": "## 合并资产负债表\n",
        "tables": [
            [
                ["合并资产负债表", "2024年"],
                ["资产总计", "1000"],
                ["负债合计", "400"],
                ["所有者权益合计", "500"],  # 不平衡
            ],
        ],
        "content_list": [],
        "metadata": {"page_count": 80},
        "error": "",
    }
    mock_mineru_class.return_value.parse.return_value = mineru_result

    # Stage 4 视觉兜底返回正确表格
    fallback_rows = [
        ["合并资产负债表", "2024年"],
        ["资产总计", "1000"],
        ["负债合计", "400"],
        ["所有者权益合计", "600"],  # 修正后平衡
    ]
    transcribed = MagicMock()
    transcribed.rows = fallback_rows
    transcribed.source = "vision_minicpmv"
    transcribed.pages = [10]
    transcribed.notes = []
    def _fake_transcribe(pdf_bytes, table, statement_type):
        return transcribed

    mock_get_transcriber.return_value.transcribe_table.side_effect = _fake_transcribe

    pipeline = FinancialPdfPipeline()
    result = pipeline.parse_annual_report(b"fake", report_year=2024)

    assert result.success is True
    assert result.statements.balance_sheet is not None
    # Stage 4 修正后权益应为 600，资产负债平衡
    bs = result.statements.balance_sheet.set_index("field")
    assert bs.loc["total_equity", "2024"] == 600.0
    assert not any("资产负债表平衡" in issue for issue in result.issues)
    # 转录器应被 Stage 2 和 Stage 4 共调用（Stage2 关闭，所以只 Stage4 一次）
    assert pipeline.transcriber.transcribe_table.call_count >= 1


@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.MinerUParser")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.get_vision_transcriber")
@patch("app.engines.rebecca.parsers.financial_pdf_pipeline.settings")
def test_stage4_keeps_original_when_fallback_fails(
    mock_settings, mock_get_transcriber, mock_mineru_class
):
    """Stage 4 视觉兜底失败时，应保持原结果不崩溃。"""
    mock_settings.ENABLE_VISION_STAGE2 = False
    mock_settings.ENABLE_VISION_STAGE4 = True
    mock_settings.ACCOUNTING_VALIDATION_TOLERANCE = 0.005

    mineru_result = {
        "success": True,
        "text": "## 合并资产负债表\n",
        "tables": [
            [
                ["合并资产负债表", "2024年"],
                ["资产总计", "1000"],
                ["负债合计", "400"],
                ["所有者权益合计", "500"],
            ],
        ],
        "content_list": [],
        "metadata": {"page_count": 80},
        "error": "",
    }
    mock_mineru_class.return_value.parse.return_value = mineru_result

    # 视觉兜底返回空表格
    transcribed = MagicMock()
    transcribed.rows = []
    transcribed.source = "vision_minicpmv"
    transcribed.pages = [10]
    transcribed.notes = []
    mock_get_transcriber.return_value.transcribe_table.return_value = transcribed

    pipeline = FinancialPdfPipeline()
    result = pipeline.parse_annual_report(b"fake", report_year=2024)

    assert result.success is True
    assert result.statements.balance_sheet is not None
    # 应保持 MinerU 原始结果
    assert result.statements.balance_sheet.set_index("field").loc["total_assets", "2024"] == 1000.0
