"""财务分析 Agent —— 财务数据波动 & 归因分析深度评测。

用途：让用户直接观察财务 Agent 在「财务数据波动（同比/较上年变动）」与
「归因分析（LLM 抽取的经营讨论深度归因）」两块上的输出深度。

包含三类测试：
  1. test_fluctuation_hints_depth_*        —— 离线、确定性，评测 8 类波动信号覆盖度
  2. test_attribution_depth_via_build_*   —— 离线（mock LLM/网络），评测归因结构深度与 500 字阈值闸门
  3. test_live_financial_*_depth           —— 实测（需联网+LLM，env RUN_LIVE_FINANCIAL=1 开启）

运行：
  pytest tests/test_financial_fluctuation_attribution_depth.py -s
  RUN_LIVE_FINANCIAL=1 pytest tests/test_financial_fluctuation_attribution_depth.py -s
"""
import os
import json

import pandas as pd
import pytest

from app.agents.sub_agents import financial_agent


# 8 类波动信号的关键词标记，用于检测输出深度
FLUCTUATION_MARKERS = [
    "收入利润背离",
    "毛利率下滑",
    "短期借款大增",
    "存货高位",
    "重资产投入",
    "经营现金流下降",
    "政府补助依赖",
    "资本回报下降",
]


def _make_3y_rebecca_data() -> dict:
    """构造一份刻意触发多类波动信号的三年三大表（单位：元）。"""
    income_statement = pd.DataFrame([
        {"项目": "营业收入", "2023": 10_000_000_000, "2024": 12_000_000_000, "2025": 15_000_000_000},
        {"项目": "净利润", "2023": 1_000_000_000, "2024": 900_000_000, "2025": 500_000_000},
        {"项目": "毛利润", "2023": 4_000_000_000, "2024": 4_200_000_000, "2025": 4_500_000_000},
        {"项目": "其他收益", "2023": 200_000_000, "2024": 300_000_000, "2025": 400_000_000},
        {"项目": "研发费用", "2023": 800_000_000, "2024": 950_000_000, "2025": 1_200_000_000},
    ])
    balance_sheet = pd.DataFrame([
        {"项目": "资产总计", "2023": 30_000_000_000, "2024": 35_000_000_000, "2025": 40_000_000_000},
        {"项目": "负债合计", "2023": 12_000_000_000, "2024": 14_000_000_000, "2025": 16_000_000_000},
        {"项目": "短期借款", "2023": 2_000_000_000, "2024": 2_500_000_000, "2025": 5_000_000_000},
        {"项目": "存货", "2023": 3_000_000_000, "2024": 3_500_000_000, "2025": 6_000_000_000},
        {"项目": "固定资产", "2023": 15_000_000_000, "2024": 17_000_000_000, "2025": 20_000_000_000},
        {"项目": "在建工程", "2023": 2_000_000_000, "2024": 3_000_000_000, "2025": 5_000_000_000},
        {"项目": "所有者权益合计", "2023": 18_000_000_000, "2024": 21_000_000_000, "2025": 24_000_000_000},
    ])
    cash_flow = pd.DataFrame([
        {"项目": "经营活动产生的现金流量净额", "2023": 2_000_000_000, "2024": 1_800_000_000, "2025": 1_000_000_000},
    ])
    return {
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
    }


def _print_depth_banner(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ────────────────────────────────────────────────────────────────────────
# 1. 财务数据波动（确定性）深度评测
# ────────────────────────────────────────────────────────────────────────
def test_fluctuation_hints_depth_direct():
    """直接评测 _build_financial_business_hints 的波动信号覆盖度。"""
    rebecca_data = _make_3y_rebecca_data()
    hints = financial_agent._build_financial_business_hints(rebecca_data, None)

    triggered = [m for m in FLUCTUATION_MARKERS if any(m in h for h in hints)]
    _print_depth_banner("【财务数据波动】_build_financial_business_hints 输出")
    print(f"触发信号数：{len(triggered)}/{len(FLUCTUATION_MARKERS)}")
    for h in hints:
        print(f"  • {h}")

    # 深度断言：至少覆盖 6 类波动信号，证明同比/较上年分析具备实质性深度
    assert len(hints) >= 6, f"波动信号过少（{len(hints)}），深度不足"
    assert len(triggered) >= 6, f"波动信号覆盖类别不足：{triggered}"


def test_fluctuation_hints_reach_report():
    """验证主线拼装契约：_run_rebecca_analysis 把波动 hints 透传给报告 builder（run_financial_agent 在 907→972 行即如此）。

    对 build_financial_analysis_report 打桩，完全避开 LLM/CodeAct 副作用，仅验证「hints → report」承载链路。
    """
    from app.agents.sub_agents import financial_report_builder

    rebecca_data = _make_3y_rebecca_data()
    hints = financial_agent._build_financial_business_hints(rebecca_data, None)
    assert len(hints) >= 6

    captured = {}

    def _fake_builder(*args, **kwargs):
        captured["hints"] = kwargs.get("financial_business_hints") or []
        return {"financial_business_hints": captured["hints"]}

    with pytest.MonkeyPatch().context() as mp:
        # financial_agent 顶部以 `from ... import build_financial_analysis_report` 绑定，
        # 必须在 financial_agent 命名空间上打桩才能拦截。
        mp.setattr(financial_agent, "build_financial_analysis_report", _fake_builder)
        result = financial_agent._run_rebecca_analysis(
            "评测公司",
            rebecca_data,
            include_structured_report=True,
            financial_business_hints=hints,
        )

    got = (result.get("financial_analysis_report") or {}).get("financial_business_hints") or []
    hit_markers = [m for m in FLUCTUATION_MARKERS if any(m in h for h in got)]
    _print_depth_banner("【财务数据波动】hints → 报告 承载链路（主线契约）")
    print(f"注入报告的 financial_business_hints 条数：{len(got)}")
    print(f"命中的波动关键词：{hit_markers}")

    assert got, "报告未承载财务波动 hints"
    assert len(hit_markers) >= 2, f"报告未体现波动分析：{hit_markers}"


# ────────────────────────────────────────────────────────────────────────
# 2. 归因分析（mock LLM/网络）结构深度评测
# ────────────────────────────────────────────────────────────────────────
_LONG_REVIEW = (
    "2025年公司集成电路业务仍处产能爬坡期，固定成本摊销较高，毛利率承压。"
    "受LED芯片行业阶段性产能过剩、产品价格持续下行影响，公司整体盈利同比下滑。"
    "公司加快SiC功率器件与半导体零部件的客户端验证，部分新产品已实现量产交付，"
    "第三代半导体产线逐步进入量产阶段，但折旧与摊销对短期利润形成压制。"
    "为应对行业周期波动，公司适度增加短期借款以满足营运资金与产线备货需求，"
    "存货规模随产能扩张同步上升，需关注后续去化节奏与跌价风险。"
    "公司持续获得政府补助支持研发与产线建设，其他收益占净利润比重较高，"
    "扣除非经常性损益后的真实盈利能力仍需观察。"
    "经营活动现金流受应收账款增加及存货占用影响同比下降，利润质量有待改善。"
    "展望后市，行业去库存接近尾声，但产品价格修复仍需时间；"
    "公司将控制资本开支节奏，聚焦高毛利产品结构优化与客户结构升级，"
    "推进车规级功率器件与光伏逆变器的客户导入，以降低周期波动对盈利的冲击。"
    "同时公司通过可转债与银行授信优化融资结构，缓解重资产投入带来的资金压力。"
    "在封装与模组环节，公司围绕功率半导体推进系统级封装能力建设，"
    "努力提升单位晶圆产出的附加值。研发方面，公司保持高强度投入，"
    "研发费用率维持较高水平，重点布局车规级IGBT、SiC MOSFET与MCU等产品。"
    "海外业务受贸易摩擦与汇率波动影响，公司通过本地化客户认证降低单一市场风险。"
    "总体而言，公司正处于战略投入期，短期盈利受产能爬坡与行业下行双重压制，"
    "待行业景气回升与高毛利产品占比提升后，盈利弹性有望逐步释放。"
)

_MOCK_SEGMENTS = [
    {"item_name": "集成电路", "income": "92.30亿元", "income_ratio": "61.50%", "gross_margin": "18.20%"},
    {"item_name": "LED产品", "income": "35.10亿元", "income_ratio": "23.40%", "gross_margin": "6.80%"},
    {"item_name": "SiC功率器件", "income": "12.40亿元", "income_ratio": "8.30%", "gross_margin": "22.10%"},
    {"item_name": "其他", "income": "10.20亿元", "income_ratio": "6.80%", "gross_margin": "15.00%"},
]

_MOCK_ATTRIBUTION = {
    "revenue_drivers": [
        {"factor": "集成电路业务放量带动营收增长", "evidence": "集成电路业务仍处产能爬坡期，固定成本摊销较高", "direction": "positive"},
        {"factor": "SiC功率器件新客户验证量产交付", "evidence": "部分新产品已实现量产交付", "direction": "positive"},
    ],
    "margin_drivers": [
        {"factor": "LED芯片行业产能过剩致产品价格下行", "evidence": "受LED芯片行业阶段性产能过剩、产品价格持续下行影响", "direction": "negative"},
        {"factor": "集成电路产能爬坡期固定成本摊销高", "evidence": "集成电路业务仍处产能爬坡期，固定成本摊销较高", "direction": "negative"},
    ],
    "profit_drivers": [
        {"factor": "毛利下滑与费用摊销叠加压低净利", "evidence": "公司整体盈利同比下滑", "direction": "negative"},
    ],
    "capacity_status": "集成电路与SiC产线处于产能爬坡期，折旧与摊销压力较大",
    "industry_context": "LED芯片行业阶段性产能过剩，价格下行；半导体国产替代持续推进",
    "company_strategy": "聚焦高毛利产品结构优化与客户结构升级，控制资本开支节奏",
    "forward_risks": [
        {"factor": "行业价格修复慢于预期", "evidence": "价格修复仍需时间", "direction": "negative"},
        {"factor": "存货与应收占用现金流", "evidence": "存货规模随产能扩张上升", "direction": "negative"},
    ],
    "data_boundary": "基于年报经营情况讨论与分析章节",
    "source": "llm",
}


def test_attribution_threshold_gate_short_review():
    """无实质经营讨论正文（<500字）时，归因应回退空结构，绝不调 LLM。"""
    from app.agents.sub_agents.annual_report_attribution_extractor import (
        extract_annual_report_attribution,
    )
    attr = extract_annual_report_attribution("评测公司", "过短摘要", key_metrics={})
    _print_depth_banner("【归因分析】500字阈值闸门（短正文）")
    print(f"source={attr.get('source')}, drivers总数="
          f"{len(attr.get('revenue_drivers') or []) + len(attr.get('margin_drivers') or []) + len(attr.get('profit_drivers') or [])}")
    assert attr.get("source") != "llm"
    assert not (attr.get("revenue_drivers") or attr.get("margin_drivers") or attr.get("profit_drivers"))


def test_attribution_depth_via_build_notes():
    """mock 东方财富F10 + mock LLM，评测 _build_annual_report_notes 的归因与主营构成深度。"""
    rebecca_data = _make_3y_rebecca_data()

    from app.agents.tools import eastmoney_structured_tool
    from app.agents.sub_agents import annual_report_attribution_extractor

    with (
        pytest.MonkeyPatch().context() as mp,
    ):
        mp.setattr(
            eastmoney_structured_tool,
            "eastmoney_fetch_business_narrative",
            lambda stock_code: {
                "success": True,
                "stock_code": stock_code,
                "business_segments": _MOCK_SEGMENTS,
                "business_review": _LONG_REVIEW,
                "error": "",
            },
        )
        mp.setattr(
            annual_report_attribution_extractor,
            "extract_annual_report_attribution",
            lambda *a, **k: dict(_MOCK_ATTRIBUTION),
        )

        notes = financial_agent._build_annual_report_notes(
            rebecca_data,
            cninfo_result={},  # 无 PDF，应回退 F10
            enterprise_name="评测公司",
            stock_code="600460",
        )

    segments = notes.get("business_segments") or []
    review = notes.get("business_review") or ""
    attr = notes.get("attribution") or {}

    n_drivers = (
        len(attr.get("revenue_drivers") or [])
        + len(attr.get("margin_drivers") or [])
        + len(attr.get("profit_drivers") or [])
    )
    n_evidence = sum(
        1 for f in ("revenue_drivers", "margin_drivers", "profit_drivers")
        for d in (attr.get(f) or [])
        if d.get("evidence")
    )

    _print_depth_banner("【归因分析】_build_annual_report_notes 输出")
    print(f"主营构成条目数：{len(segments)}")
    print(f"经营讨论正文字数：{len(review)}")
    print(f"归因 driver 总数：{n_drivers}（含 evidence：{n_evidence}）")
    print(f"capacity_status：{bool(attr.get('capacity_status'))}")
    print(f"industry_context：{bool(attr.get('industry_context'))}")
    print(f"company_strategy：{bool(attr.get('company_strategy'))}")
    print(f"forward_risks：{len(attr.get('forward_risks') or [])}")
    print(f"attribution.source：{attr.get('source')}")

    # 深度断言
    assert len(segments) >= 3, "主营构成深度不足"
    assert len(review) >= 500, "经营讨论正文字数不足，无法支撑深度归因"
    assert attr.get("source") == "llm", "归因未命中 LLM 路径"
    assert n_drivers >= 4, f"归因 driver 过少（{n_drivers}）"
    assert n_evidence >= 4, "归因缺少年报原文引用（evidence）"
    assert attr.get("capacity_status") and attr.get("industry_context") and attr.get("company_strategy")
    assert len(attr.get("forward_risks") or []) >= 1


def test_attribution_completeness_gate():
    """回归：profit_drivers / capacity_status / forward_risks 任一缺失应触发 [soft] 完整性告警；完整则无。"""
    from app.agents.sub_agents.annual_report_attribution_extractor import _quality_warnings

    # 单薄候选：只有 revenue/margin，profit/capacity/forward 缺失 → 应触发软告警
    thin = {
        "revenue_drivers": [{"factor": "x", "evidence": "y", "direction": "positive"}],
        "margin_drivers": [{"factor": "x", "evidence": "y", "direction": "negative"}],
        "profit_drivers": [],
        "capacity_status": "",
        "industry_context": "景气平稳",
        "company_strategy": "优化结构",
        "forward_risks": [],
    }
    thin_w = _quality_warnings(thin)
    soft = [w for w in thin_w if w.startswith("[soft]")]
    assert soft, "缺失 profit/capacity/forward 却未触发完整性软告警"
    assert "profit_drivers" in soft[0] and "capacity_status" in soft[0] and "forward_risks" in soft[0]

    # 完整候选：五类齐全 → 不应有软告警
    complete = {
        "revenue_drivers": [{"factor": "x", "evidence": "y", "direction": "positive"}],
        "margin_drivers": [{"factor": "x", "evidence": "y", "direction": "negative"}],
        "profit_drivers": [{"factor": "减值", "evidence": "资产减值", "direction": "negative"}],
        "capacity_status": "产能爬坡期",
        "industry_context": "景气平稳",
        "company_strategy": "优化结构",
        "forward_risks": [{"factor": "价格下行", "evidence": "风险提示", "direction": "negative"}],
    }
    assert not [w for w in _quality_warnings(complete) if w.startswith("[soft]")], "完整候选不应触发软告警"


def test_attribution_prompt_requires_all_three():
    """回归：prompt 模板已把 profit_drivers / capacity_status / forward_risks 列为强制项。"""
    from app.config.prompt_loader import load_prompt_template

    tpl = load_prompt_template("annual_report_attribution")
    for must in ("profit_drivers", "capacity_status", "forward_risks", "同等重要"):
        assert must in tpl, f"prompt 模板缺少强制项：{must}"


def test_build_prompt_includes_risk_section():
    """回归：_build_prompt 必须注入风险章节，且 forward_risks 优先从风险章节抽取。"""
    from app.agents.sub_agents.annual_report_attribution_extractor import _build_prompt

    # 有风险章节时，prompt 同时包含经营讨论与风险章节原文及使用指引。
    prompt = _build_prompt(
        enterprise_name="测试企业",
        business_review="经营讨论正文。",
        key_metrics=None,
        key_metric_series=None,
        business_segments=None,
        risk_section="可能面对的风险：行业价格下行。",
    )
    assert "公司面临的风险和应对措施" in prompt, "prompt 未注入风险章节区块"
    assert "行业价格下行" in prompt, "风险章节原文未进入 prompt"

    # 无风险章节时，prompt 仍应正常渲染（变量为空），不抛异常。
    prompt_none = _build_prompt("测试企业", "经营讨论正文。", None, None, None, risk_section=None)
    assert "公司面临的风险和应对措施" in prompt_none


def test_section_extractor_captures_major_risk_warnings():
    """回归：标准年报「公司面临的风险和应对措施/可能面对的风险」章节应能被抽取。"""
    from app.agents.tools.annual_report_section_extractor import extract_all_sections

    text = (
        "第四节 经营情况讨论与分析\n"
        "十二、公司面临的风险和应对措施\n"
        "可能面对的风险 √适用 □不适用 1、规模扩张引发的管理风险 公司业务规模快速扩张。\n"
        "十三、报告期内接待调研 本节约略。\n"
        "第五节 重要事项 本节略。\n"
    )
    sections = extract_all_sections({"text": text, "success": True}, context_chars=2000)
    risk = sections.get("major_risk_warnings") or ""
    assert "规模扩张引发的管理风险" in risk, "风险章节未被抽取"


# ────────────────────────────────────────────────────────────────────────
# 3. 实测（需联网 + LLM，默认跳过）
# ────────────────────────────────────────────────────────────────────────
_LIVE = os.environ.get("RUN_LIVE_FINANCIAL") == "1"


@pytest.mark.skipif(not _LIVE, reason="需设置 RUN_LIVE_FINANCIAL=1 并配置联网/LLM 环境")
@pytest.mark.asyncio
async def test_live_financial_fluctuation_attribution_depth():
    """实测真实上市公司：跑通 Agent 并单独评测 F10+LLM 归因深度。"""
    import asyncio

    enterprise_name = os.environ.get("FINANCIAL_TEST_ENTERPRISE", "士兰微")
    from app.agents.sub_agents.financial_agent import run_financial_agent
    from app.agents.tools.eastmoney_structured_tool import eastmoney_fetch_business_narrative
    from app.agents.sub_agents.annual_report_attribution_extractor import (
        extract_annual_report_attribution,
    )
    from app.agents.sub_agents.financial_agent import resolve_listed_company

    result = await run_financial_agent(enterprise_name=enterprise_name, session_id=None, task_id=None)
    assert result.get("success") is True, result.get("error")

    serialized = json.dumps(result, ensure_ascii=False)
    hit_markers = [m for m in FLUCTUATION_MARKERS if m in serialized]
    _print_depth_banner(f"【实测·波动】{enterprise_name}")
    print(f"报告中命中波动关键词：{hit_markers}")

    listed = resolve_listed_company(enterprise_name) or {}
    stock_code = listed.get("stock_code") or ""
    assert stock_code, "无法解析股票代码"

    narrative = eastmoney_fetch_business_narrative(stock_code)
    _print_depth_banner(f"【实测·归因】{enterprise_name}（F10 + LLM）")
    print(f"stock_code={stock_code}")
    print(f"F10 主营构成条目数：{len(narrative.get('business_segments') or [])}")
    print(f"F10 经营讨论正文字数：{len(narrative.get('business_review') or '')}")

    attr = extract_annual_report_attribution(
        enterprise_name=enterprise_name,
        business_review=narrative.get("business_review") or "",
        business_segments=narrative.get("business_segments") or [],
    )
    n_drivers = (
        len(attr.get("revenue_drivers") or [])
        + len(attr.get("margin_drivers") or [])
        + len(attr.get("profit_drivers") or [])
    )
    print(f"归因 source={attr.get('source')}, model={attr.get('model_id')}, "
          f"driver总数={n_drivers}, 质量告警={attr.get('quality_warnings')}")
    print(f"capacity_status：{attr.get('capacity_status')}")
    print(f"industry_context：{attr.get('industry_context')}")
    print(f"company_strategy：{attr.get('company_strategy')}")

    assert narrative.get("business_review"), "F10 未返回经营讨论正文"
    assert attr.get("source") == "llm", "实测归因未走 LLM 路径"
    assert n_drivers >= 1, "实测归因未抽取到任何 driver"
