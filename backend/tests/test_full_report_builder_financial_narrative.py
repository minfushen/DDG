# backend/tests/test_full_report_builder_financial_narrative.py
"""验证 full_report_builder 优先使用经营穿透叙事生成财务 highlights。"""

import pytest

from app.agents.sub_agents.full_report_builder import _financial_highlights


def test_financial_highlights_uses_narrative_sections():
    report = {
        "narrative_source": "llm",
        "narrative_quality_warnings": [],
        "narrative_sections": [
            {
                "section_title": "3.1 收入与利润分析",
                "narrative": "营业收入增长主因是 SiC 业务放量，但 LED 芯片价格下行导致毛利率承压，扣非净利润连续为负反映主业盈利尚未实质修复。",
            },
            {
                "section_title": "3.2 资产负债分析",
                "narrative": "固定资产与在建工程占比较高，反映碳化硅和 Mini/Micro LED 重资本投入；短期借款大幅增加，需关注流动性安排。",
            },
            {
                "section_title": "3.3 盈利质量与营运效率",
                "narrative": "盈利高度依赖政府补助，研发投入略低于行业中位数；存货维持高位，去库存周期中周转压力仍存。",
            },
            {
                "section_title": "3.4 偿债能力与财务信号异常",
                "narrative": "经营现金流同比下降，但仍可覆盖利息支出；流动比率尚可，但短债增幅较大需跟踪未来 12 个月偿债安排。",
            },
        ],
        "recommendation": "审慎准入，建议补充订单、客户集中度及产能利用率材料后复核。",
    }

    highlights = _financial_highlights(report)
    assert any("SiC" in h for h in highlights)
    assert any("LED" in h for h in highlights)
    assert any("短期借款" in h for h in highlights)
    assert any("政府补助" in h for h in highlights)


def test_financial_highlights_falls_back_when_narrative_has_warnings():
    report = {
        "narrative_source": "llm",
        "narrative_quality_warnings": ["财务叙事缺乏业务动因解释"],
        "narrative_sections": [
            {"section_title": "3.1 收入与利润分析", "narrative": "收入增长了。"},
        ],
        "narrative_summary": ["fallback summary"],
    }

    highlights = _financial_highlights(report)
    assert highlights == ["fallback summary"]


def test_financial_highlights_falls_back_when_no_sections():
    report = {
        "narrative_summary": ["old narrative line 1", "old narrative line 2"],
    }

    highlights = _financial_highlights(report)
    assert highlights == ["old narrative line 1", "old narrative line 2"]
