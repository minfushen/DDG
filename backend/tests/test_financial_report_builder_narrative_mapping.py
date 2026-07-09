# backend/tests/test_financial_report_builder_narrative_mapping.py
"""验证 financial_report_builder 将 LLM 经营穿透叙事映射到四大板块 analysis。"""

import pandas as pd
import pytest

from app.agents.sub_agents import financial_report_builder
from app.agents.sub_agents.financial_report_builder import build_financial_analysis_report


def fake_build_financial_narrative(*args, **kwargs):
    return {
        "source": "llm",
        "summary": ["summary line"],
        "diagnostics": {},
        "sections": [
            {
                "section_title": "收入与利润分析",
                "metrics_table": [],
                "narrative": "收入增长主因是 SiC 放量，但 LED 降价拖累毛利率。",
                "anomalies": ["扣非连续为负"],
            },
            {
                "section_title": "资产负债分析",
                "metrics_table": [],
                "narrative": "重资产投入较大，短期借款增加。",
                "anomalies": [],
            },
            {
                "section_title": "盈利质量与营运效率",
                "metrics_table": [],
                "narrative": "盈利依赖政府补助，存货周转慢。",
                "anomalies": [],
            },
            {
                "section_title": "偿债能力与财务信号异常",
                "metrics_table": [],
                "narrative": "经营现金流下降，但利息保障仍充足。",
                "anomalies": [],
            },
        ],
        "quality_warnings": [],
    }


def fake_run_codeact_tool(*args, **kwargs):
    return {"success": True, "result": {}}


def test_narrative_sections_map_to_analysis(monkeypatch):
    monkeypatch.setattr(
        financial_report_builder,
        "build_financial_narrative",
        fake_build_financial_narrative,
    )
    monkeypatch.setattr(
        financial_report_builder,
        "run_codeact_tool",
        fake_run_codeact_tool,
    )

    financial_data = {
        "income_statement": pd.DataFrame({
            "项目": ["营业收入", "营业成本", "净利润"],
            "2022": [100.0, 80.0, 10.0],
            "2023": [110.0, 90.0, 8.0],
            "2024": [120.0, 100.0, 5.0],
        }),
        "balance_sheet": pd.DataFrame({
            "项目": ["资产总计", "负债合计", "短期借款"],
            "2022": [200.0, 80.0, 10.0],
            "2023": [220.0, 90.0, 15.0],
            "2024": [250.0, 100.0, 25.0],
        }),
        "cash_flow": pd.DataFrame({
            "项目": ["经营活动产生的现金流量净额"],
            "2022": [20.0],
            "2023": [18.0],
            "2024": [12.0],
        }),
    }

    result = build_financial_analysis_report(
        enterprise_name="测试公司",
        financial_data=financial_data,
    )

    sections = result.get("sections") or []
    subsections = []
    for sec in sections:
        subsections.extend(sec.get("subsections") or [])

    income_sub = next(s for s in subsections if "收入" in s.get("title", "") and "利润" in s.get("title", ""))
    balance_sub = next(s for s in subsections if "资产负债" in s.get("title", ""))
    quality_sub = next(s for s in subsections if "盈利质量" in s.get("title", ""))
    solvency_sub = next(s for s in subsections if "偿债能力" in s.get("title", ""))

    assert any("SiC" in line for line in income_sub["analysis"])
    assert any("重资产" in line for line in balance_sub["analysis"])
    assert any("政府补助" in line for line in quality_sub["analysis"])
    assert any("经营现金流" in line for line in solvency_sub["analysis"])

    assert income_sub.get("narrative_source") == "llm"
    assert result.get("narrative_sections")


def test_rule_analysis_preserved_when_narrative_has_warnings(monkeypatch):
    def fake_narrative_with_warning(*args, **kwargs):
        return {
            "source": "llm",
            "summary": ["summary"],
            "diagnostics": {},
            "sections": [
                {"section_title": "收入与利润分析", "narrative": "太简单"},
                {"section_title": "资产负债分析", "narrative": "太简单"},
                {"section_title": "盈利质量与营运效率", "narrative": "太简单"},
                {"section_title": "偿债能力与财务信号异常", "narrative": "太简单"},
            ],
            "quality_warnings": ["财务叙事缺乏业务动因解释"],
        }

    monkeypatch.setattr(
        financial_report_builder,
        "build_financial_narrative",
        fake_narrative_with_warning,
    )
    monkeypatch.setattr(
        financial_report_builder,
        "run_codeact_tool",
        fake_run_codeact_tool,
    )

    financial_data = {
        "income_statement": pd.DataFrame({
            "项目": ["营业收入", "营业成本", "净利润"],
            "2022": [100.0, 80.0, 10.0],
            "2023": [110.0, 90.0, 8.0],
            "2024": [120.0, 100.0, 5.0],
        }),
        "balance_sheet": pd.DataFrame({
            "项目": ["资产总计", "负债合计"],
            "2022": [200.0, 80.0],
            "2023": [220.0, 90.0],
            "2024": [250.0, 100.0],
        }),
        "cash_flow": pd.DataFrame({
            "项目": ["经营活动产生的现金流量净额"],
            "2022": [20.0],
            "2023": [18.0],
            "2024": [12.0],
        }),
    }

    result = build_financial_analysis_report(
        enterprise_name="测试公司",
        financial_data=financial_data,
    )

    sections = result.get("sections") or []
    subsections = [s for sec in sections for s in sec.get("subsections", [])]
    income_sub = next(s for s in subsections if "收入" in s.get("title", "") and "利润" in s.get("title", ""))
    # 由于有 quality_warnings，不应覆盖 analysis 为太简单
    assert income_sub.get("narrative_source") != "llm"
    analysis_text = "\n".join(income_sub["analysis"]) if isinstance(income_sub["analysis"], list) else income_sub["analysis"]
    assert "太简单" not in analysis_text
