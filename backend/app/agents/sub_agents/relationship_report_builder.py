"""关联网络分析报告生成器。

把 ``relationship_network_tool.build_relationship_network`` 的标准化输出，
整理为可供报告装配层消费的 ``relationship_analysis_report`` 结构（与 legal/business
报告一致：``risk_rating`` / ``risk_score`` / ``recommendation`` / ``sections`` /
``risk_summary`` / ``evidence``）。
"""

from __future__ import annotations

from typing import Any, Dict, List


_RATING_SCORE = {"low": 85, "medium": 65, "high": 45}

_RECOMMENDATION = {
    "low": "关联结构清晰，未发现重大股权质押、冻结或关联担保信号，可按常规授信条件推进。",
    "medium": "存在一定关联风险信号（股权质押/对外担保/股权分散等），建议核验担保明细、实控人稳定性与反担保措施后推进。",
    "high": "检测到高风险关联信号（关联担保圈/股权冻结/高比例质押等），建议暂缓授信或落实强担保与实控人连带责任后再议。",
}


def _shareholder_rows(shareholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for s in shareholders[:10]:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        rows.append({
            "股东名称": s.get("name"),
            "股东性质": s.get("holder_type") or "—",
            "持股比例": f"{s['stake_ratio']:.2f}%" if s.get("stake_ratio") is not None else "—",
            "是否实控人": "是" if s.get("is_actual_controller") else "否",
            "质押/冻结": s.get("pledge_freeze") or "无",
        })
    return rows


def build_relationship_report(
    enterprise_name: str,
    network: Dict[str, Any],
) -> Dict[str, Any]:
    """基于关联网络数据生成结构化报告。"""
    enterprise_name = network.get("enterprise_name") or enterprise_name
    risk_rating = network.get("risk_rating", "medium")
    risk_score = _RATING_SCORE.get(risk_rating, 65)
    shareholders = network.get("shareholders") or []
    actual_controller = network.get("actual_controller")
    guarantees = network.get("guarantees") or []
    pledges = network.get("pledges") or []
    equity_freeze = network.get("equity_freeze") or []
    supply_chain = network.get("supply_chain") or {}
    related_parties = network.get("related_parties") or []
    risk_tags = network.get("risk_tags") or []

    shareholder_rows = _shareholder_rows(shareholders)

    # ── 概览数字 ──
    summary = {
        "股东数量": len(shareholders),
        "实际控制人": actual_controller.get("name") if actual_controller else "未识别",
        "对外担保笔数": len(guarantees),
        "股权冻结项": len(equity_freeze),
        "股权质押线索": len(pledges),
        "关联方数量": len(related_parties),
    }

    # ── 章节 ──
    sections = [
        {
            "title": "一、股权结构与穿透",
            "summary": [
                {"label": "实际控制人", "value": actual_controller.get("name") if actual_controller else "未识别"},
                {"label": "认定路径", "value": actual_controller.get("control_path") if actual_controller else "—"},
                {"label": "股东数量", "value": len(shareholders)},
            ],
            "analysis": [
                f"基于{network.get('data_source', '关联数据源')}构建股权结构，"
                f"第一大股东为{shareholder_rows[0]['股东名称'] if shareholder_rows else '未获取'}"
                f"（持股{shareholder_rows[0]['持股比例'] if shareholder_rows else '—'}）。",
                "股权穿透重点识别实际控制人及其一致行动人，判断治理稳定性与利益输送风险。",
            ],
            "table": shareholder_rows,
        },
        {
            "title": "二、对外担保与股权质押",
            "summary": [
                {"label": "对外担保", "value": f"{len(guarantees)}笔"},
                {"label": "股权冻结", "value": f"{len(equity_freeze)}项"},
                {"label": "质押线索", "value": f"{len(pledges)}处"},
            ],
            "analysis": [
                (f"检测到{len(guarantees)}笔对外担保" + ("，存在关联担保圈风险" if any(g.get('related_party') for g in guarantees) else "，需核验被担保方偿债能力") + "。")
                if guarantees else "未发现结构化对外担保记录（非上市企业以工商披露为准）。",
                (f"{len(equity_freeze)}项股权冻结线索，需核实冻结原因与执行状态。" if equity_freeze else "未检测到股权冻结线索。"),
            ],
            "items": (
                [
                    {
                        "关联方": g.get("related_party") or "—",
                        "金额": (f"{g['amount']:.2f}万" if isinstance(g.get("amount"), (int, float)) else "未披露"),
                        "类型": g.get("guarantee_type") or "对外担保",
                    }
                    for g in guarantees[:12]
                ]
                if guarantees else []
            ),
        },
        {
            "title": "三、上下游供应链位置",
            "summary": [
                {"label": "上游", "value": "、".join(supply_chain.get("upstream", [])[:3]) or "待补充"},
                {"label": "下游", "value": "、".join(supply_chain.get("downstream", [])[:3]) or "待补充"},
                {"label": "主营产品", "value": "、".join((supply_chain.get("main_products") or [])[:3]) or "待补充"},
            ],
            "analysis": [
                "结合行业知识库与主营构成定位企业在产业链中的环节与上下游议价能力。",
                "上下游集中度过高或存在关联交易的，需关注收入真实性与资金闭环。",
            ],
        },
        {
            "title": "四、关联风险标签与评级",
            "summary": [
                {"label": "风险评级", "value": risk_rating},
                {"label": "风险评分", "value": risk_score},
            ],
            "tags": risk_tags,
        },
    ]

    risk_summary = [t.get("detail", "") for t in risk_tags if t.get("detail")]

    evidence = [
        {"label": "关联风险评级", "value": f"{risk_rating}/{risk_score}", "source": network.get("data_source", "关联网络工具")},
        {"label": "关联信号", "value": f"{len(risk_tags)}项", "source": "关联网络工具"},
        {"label": "关联方", "value": f"{len(related_parties)}个", "source": "关联网络工具"},
    ]

    return {
        "report_type": "relationship_analysis",
        "enterprise_name": enterprise_name,
        "generated_from": network.get("data_source", "关联数据源"),
        "is_listed": network.get("is_listed", False),
        "stock_code": network.get("stock_code"),
        "risk_rating": risk_rating,
        "risk_score": risk_score,
        "recommendation": _RECOMMENDATION.get(risk_rating, _RECOMMENDATION["medium"]),
        "summary": summary,
        "shareholders": shareholder_rows,
        "actual_controller": actual_controller,
        "guarantees": guarantees,
        "pledges": pledges,
        "equity_freeze": equity_freeze,
        "supply_chain": supply_chain,
        "related_parties": related_parties,
        "sections": sections,
        "risk_tags": risk_tags,
        "risk_summary": risk_summary,
        "evidence": evidence,
    }
