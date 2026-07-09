# backend/tests/test_financial_narrative_writer_business_penetration.py
"""财务叙事 writer 经营穿透相关辅助函数单元测试（不调用 LLM）。"""

import pytest

from app.agents.sub_agents.financial_narrative_writer import (
    _business_penetration_warnings,
    _normalize_sections,
)


def test_business_penetration_warnings_passes_with_causal_text():
    text = (
        "3.1 收入与利润分析。核心判断：营收增长但利润承压。"
        "公司营业收入增长，主因是集成电路业务放量；"
        "受 LED 芯片产能过剩影响，毛利率持续下滑；"
        "这表明主营业务盈利承压。"
        "3.2 资产负债分析。核心判断：重资产投入加大。"
        "资产结构反映公司重资本投入。"
        "3.3 盈利质量与营运效率。核心判断：盈利依赖非经常性损益。"
        "扣非亏损源于折旧及补贴依赖。"
        "3.4 偿债能力与财务信号异常。核心判断：短期偿债压力上升。"
        "短期借款大增导致流动性压力。"
    )
    hints = ["LED 产能过剩", "短期借款压力", "政府补助依赖"]
    warnings = _business_penetration_warnings(text, hints)
    assert not warnings, warnings


def test_business_penetration_warnings_fails_without_causal_text():
    text = "3.1 收入与利润分析：公司营业收入为 100 亿元，净利润为 5 亿元。"
    hints = ["LED 产能过剩", "短期借款压力"]
    warnings = _business_penetration_warnings(text, hints)
    assert warnings
    assert any("业务动因" in w for w in warnings)
    assert any("业务归因提示" in w for w in warnings)
    assert any("四大板块" in w for w in warnings)


def test_business_penetration_warnings_ignores_hint_check_when_no_hints():
    text = (
        "3.1 收入与利润分析。核心判断：收入增长。营业收入增长。"
        "3.2 资产负债分析。核心判断：资产扩张。总资产增加。"
        "3.3 盈利质量与营运效率。核心判断：周转放缓。周转天数上升。"
        "3.4 偿债能力与财务信号异常。核心判断：偿债承压。流动比率下降。"
        "主因是、受、影响、反映、表明、导致、源于"
    )
    warnings = _business_penetration_warnings(text, None)
    # 因果词足够（>=3），无 hints 时不检查 hints 和行业上下文，四大板块齐全且有核心判断
    assert not warnings, warnings


def test_normalize_sections_uses_llm_sections():
    llm_sections = [
        {"section_title": "收入与利润分析", "narrative": "收入增长主因..."},
        {"section_title": "资产负债分析", "narrative": "重资本投入..."},
        {"section_title": "盈利质量与营运效率", "narrative": "周转放缓..."},
        {"section_title": "偿债能力与财务信号异常", "narrative": "短债压力..."},
    ]
    fallback = [
        {"section_title": "收入与利润分析", "narrative": "fallback income"},
    ]
    sections = _normalize_sections(llm_sections, fallback)
    assert len(sections) == 4
    assert sections[0]["section_title"] == "收入与利润分析"
    assert sections[0]["narrative"] == "收入增长主因..."


def test_normalize_sections_falls_back_when_llm_empty():
    fallback = [
        {"section_title": "收入与利润分析", "narrative": "fallback income"},
        {"section_title": "资产负债分析", "narrative": "fallback balance"},
    ]
    sections = _normalize_sections(None, fallback)
    assert len(sections) == 2
    assert sections[0]["narrative"] == "fallback income"


def test_normalize_sections_filters_invalid_items():
    llm_sections = [
        {"section_title": "收入与利润分析", "narrative": "ok"},
        {"section_title": "资产负债分析", "narrative": "ok2"},
        {"section_title": "盈利质量与营运效率", "narrative": "ok3"},
        {"section_title": "偿债能力与财务信号异常", "narrative": "ok4"},
        {"narrative": "missing title"},
        "not a dict",
    ]
    sections = _normalize_sections(llm_sections, [])
    assert len(sections) == 4
    assert sections[0]["section_title"] == "收入与利润分析"
