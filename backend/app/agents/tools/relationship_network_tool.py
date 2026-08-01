"""关联网络工具：整合股权、担保/质押、上下游供应链等关联数据，构建企业关联网络。

设计原则（与项目红线一致）：
- 复用现有数据源，不重复造轮子：上市公司走 cninfo（股东表/风险档案）+ 东方财富公开资料包；
  非上市/未匹配企业走元典企业工商库。
- 失败安全：任一数据源异常都不抛出，只降级并在 ``risk_tags`` 标注“关联数据暂不可得”，
  绝不伪造或回退占位数值。
- 输出统一结构，供 ``relationship_report_builder`` 与 ``relationship_agent`` 直接使用。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _to_float(value: Any) -> Optional[float]:
    """把 '40.00%' / '40.0' / 40 这类值解析为 float；失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("%", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _resolve_stock_code(enterprise_name: str, stock_code: Optional[str]) -> Tuple[Optional[str], bool]:
    """解析上市公司证券代码；命中返回 (code, True)，否则 (None, False)。"""
    if stock_code:
        return stock_code, True
    try:
        from app.agents.tools.listed_company_tool import resolve_listed_company

        info = resolve_listed_company(enterprise_name)
        if info and info.get("stock_code"):
            return info["stock_code"], True
    except Exception as exc:  # 网络/配置问题不应阻断主流程
        logger.warning("resolve_listed_company failed for %s: %s", enterprise_name, exc)
    return None, False


def _gather_listed(stock_code: str, enterprise_name: str) -> Dict[str, Any]:
    """上市公司：cninfo 股东表 + 风险档案 + 东方财富公开资料包。"""
    shareholders: List[Dict[str, Any]] = []
    actual_controller: Optional[Dict[str, Any]] = None
    guarantees: List[Dict[str, Any]] = []
    pledges: List[Dict[str, Any]] = []
    equity_freeze: List[Dict[str, Any]] = []
    supply_chain: Dict[str, List[str]] = {"upstream": [], "downstream": []}

    # 1) 股东表（含十大股东、持股比例、质押/冻结列）
    try:
        from app.agents.tools.cninfo_webapi_tool import build_shareholder_table

        tbl = build_shareholder_table(stock_code)
        if tbl.get("success"):
            for row in tbl.get("rows", []):
                ratio = _to_float(row.get("持股比例"))
                shareholders.append({
                    "name": row.get("股东名称"),
                    "stake_ratio": ratio,
                    "holder_type": row.get("股东性质"),
                    "is_top10": True,
                    "is_actual_controller": False,
                    "pledge_freeze": row.get("质押/冻结"),
                })
    except Exception as exc:
        logger.warning("listed shareholder_table gather failed: %s", exc)

    # 2) 实际控制人
    try:
        from app.agents.tools.cninfo_webapi_tool import build_shareholder_profile

        prof = build_shareholder_profile(stock_code)
        ctrl_records = (prof.get("actual_controller") or {}).get("records") or []
        if ctrl_records:
            actual_controller = {
                "name": ctrl_records[-1].get("F004V") or ctrl_records[-1].get("name"),
                "control_path": "信息披露认定实际控制人",
                "control_ratio": None,
            }
            if actual_controller.get("name") and shareholders:
                for s in shareholders:
                    if s.get("name") and actual_controller["name"] in s["name"]:
                        s["is_actual_controller"] = True
    except Exception as exc:
        logger.warning("listed actual_controller gather failed: %s", exc)

    # 3) 风险档案：对外担保 + 资产冻结
    try:
        from app.agents.tools.cninfo_webapi_tool import build_risk_profile

        rp = build_risk_profile(stock_code)
        for rec in (rp.get("guarantees") or {}).get("records", []):
            guarantees.append({
                "related_party": rec.get("F001V") or rec.get("party") or rec.get("关联方"),
                "amount": _to_float(rec.get("F002N") or rec.get("amount")),
                "guarantee_type": rec.get("F003V") or rec.get("type") or "对外担保",
                "counterparty": rec.get("F004V") or rec.get("counterparty"),
            })
        for rec in (rp.get("asset_freezes") or {}).get("records", []):
            equity_freeze.append({
                "party": rec.get("F001V") or rec.get("party"),
                "amount": _to_float(rec.get("F002N") or rec.get("amount")),
                "detail": rec.get("F003V") or rec.get("detail"),
            })
    except Exception as exc:
        logger.warning("listed risk_profile gather failed: %s", exc)

    # 4) 东方财富公开资料包：质押/担保线索 + 主营构成（供应链线索）
    try:
        from app.agents.tools.listed_company_public_info_tool import fetch_listed_company_public_info_data

        pi = fetch_listed_company_public_info_data(enterprise_name, stock_code=stock_code)
        if pi.get("success"):
            main_business = pi.get("main_business_composition") or []
            supply_chain = _supply_chain_from_main_business(main_business)
            for key, items in (pi.get("search_clues") or {}).items():
                if items and ("质押" in key or "担保" in key):
                    pledges.append({"source": key, "clue_count": len(items)})
    except Exception as exc:
        logger.warning("listed public_info gather failed: %s", exc)

    return {
        "shareholders": shareholders,
        "actual_controller": actual_controller,
        "guarantees": guarantees,
        "pledges": pledges,
        "equity_freeze": equity_freeze,
        "supply_chain": supply_chain,
    }


def _gather_nonlisted(enterprise_name: str) -> Dict[str, Any]:
    """非上市/未匹配：元典企业工商库（股东、法人、股权冻结线索）。"""
    shareholders: List[Dict[str, Any]] = []
    actual_controller: Optional[Dict[str, Any]] = None
    equity_freeze: List[Dict[str, Any]] = []
    try:
        from app.agents.tools.yuandian_company_tool import build_business_profile

        prof = build_business_profile(enterprise_name)
        if not prof.get("success"):
            return {"shareholders": [], "actual_controller": None, "equity_freeze": []}
        basic_records = (prof.get("basic_info") or {}).get("records") or []
        for rec in basic_records:
            if not isinstance(rec, dict):
                continue
            name = (
                rec.get("company_name") or rec.get("enterpriseName")
                or rec.get("qymc") or rec.get("股东名称") or rec.get("股东")
            )
            if not name:
                continue
            # 元典 baseInfo 字段名不固定，宽容提取持股比例/法人
            ratio = _to_float(rec.get("proportion") or rec.get("持股比例") or rec.get("出资比例"))
            is_ctrl = bool(rec.get("isActualController") or rec.get("实际控制人") or rec.get("actualController"))
            shareholders.append({
                "name": name,
                "stake_ratio": ratio,
                "holder_type": rec.get("shareholderType") or rec.get("股东性质") or "未知",
                "is_top10": False,
                "is_actual_controller": is_ctrl,
                "pledge_freeze": None,
            })
            if is_ctrl:
                actual_controller = {"name": name, "control_path": "元典工商登记认定", "control_ratio": ratio}
    except Exception as exc:
        logger.warning("nonlisted yuandian gather failed: %s", exc)
    return {
        "shareholders": shareholders,
        "actual_controller": actual_controller,
        "equity_freeze": equity_freeze,
    }


def _supply_chain_from_main_business(main_business: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """从主营构成抽取企业自身产品（作为供应链分析的起点）。"""
    products: List[str] = []
    for item in main_business[:8]:
        if not isinstance(item, dict):
            continue
        name = item.get("item_name") or item.get("MAIN_BUSINESS") or item.get("product")
        if name:
            products.append(str(name))
    return {"upstream": [], "downstream": [], "main_products": products}


def _derive_supply_chain(industry_name: Optional[str]) -> Dict[str, List[str]]:
    """用行业知识库 RAG 补充上下游产业链信息（可选，失败安全）。"""
    if not industry_name:
        return {"upstream": [], "downstream": []}
    try:
        from app.rag.knowledge_retrieval_service import retrieve_knowledge

        res = retrieve_knowledge(
            query=f"{industry_name} 产业链 上游 下游 供应商 客户 集中度",
            domain="industry",
            top_k=6,
        )
        upstream: List[str] = []
        downstream: List[str] = []
        for r in res.get("results", []):
            text = str(r.get("content") or r.get("text") or "")
            if "上游" in text:
                upstream.append(text[:80])
            elif "下游" in text:
                downstream.append(text[:80])
        return {"upstream": upstream[:5], "downstream": downstream[:5]}
    except Exception as exc:
        logger.warning("supply_chain RAG derive failed: %s", exc)
        return {"upstream": [], "downstream": []}


def _collect_related_parties(
    shareholders: List[Dict[str, Any]],
    actual_controller: Optional[Dict[str, Any]],
    guarantees: List[Dict[str, Any]],
) -> List[str]:
    parties: List[str] = []
    for s in shareholders:
        if s.get("name"):
            parties.append(s["name"])
    if actual_controller and actual_controller.get("name"):
        parties.append(actual_controller["name"])
    for g in guarantees:
        if g.get("related_party"):
            parties.append(g["related_party"])
    # 去重保序
    seen = set()
    out = []
    for p in parties:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _compute_risk_tags(
    shareholders: List[Dict[str, Any]],
    actual_controller: Optional[Dict[str, Any]],
    guarantees: List[Dict[str, Any]],
    pledges: List[Dict[str, Any]],
    equity_freeze: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    tags: List[Dict[str, str]] = []

    # 对外担保 / 关联担保
    if guarantees:
        related = [g for g in guarantees if g.get("related_party")]
        if related:
            tags.append({
                "tag": "关联担保/担保圈",
                "level": "high",
                "detail": f"存在{len(guarantees)}笔对外担保，其中{len(related)}笔涉及关联方，需关注担保圈连锁风险。",
            })
        else:
            tags.append({
                "tag": "对外担保",
                "level": "medium",
                "detail": f"存在{len(guarantees)}笔对外担保，需核验被担保方偿债能力与反担保措施。",
            })

    # 股权冻结
    if equity_freeze:
        tags.append({
            "tag": "股权冻结",
            "level": "high",
            "detail": f"检测到{len(equity_freeze)}项股权冻结线索，需核实冻结原因、金额与执行状态。",
        })

    # 股权质押
    pledged = [s for s in shareholders if s.get("pledge_freeze") and s["pledge_freeze"] != "无"]
    if pledged:
        tags.append({
            "tag": "股权质押",
            "level": "medium" if len(pledged) < 3 else "high",
            "detail": f"{len(pledged)}名股东存在质押/冻结，需关注平仓线与实控人稳定性。",
        })
    elif pledges:
        tags.append({
            "tag": "股权质押线索",
            "level": "medium",
            "detail": f"公开线索提示存在股权质押/担保公告（{len(pledges)}处），需核实质押比例。",
        })

    # 股权分散 / 无实控人
    top_ratio = max([s["stake_ratio"] for s in shareholders if s.get("stake_ratio") is not None], default=None)
    if top_ratio is not None and top_ratio < 20 and not actual_controller:
        tags.append({
            "tag": "股权分散",
            "level": "medium",
            "detail": f"第一大股东持股比例仅{top_ratio:.1f}%且无认定实际控制人，治理结构稳定性偏弱。",
        })

    if not tags:
        tags.append({
            "tag": "关联结构清晰",
            "level": "low",
            "detail": "未检测到重大股权质押、冻结或关联担保信号。",
        })
    return tags


def _aggregate_rating(risk_tags: List[Dict[str, str]]) -> str:
    levels = [t.get("level") for t in risk_tags]
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    return "low"


def build_relationship_network(
    enterprise_name: str,
    stock_code: Optional[str] = None,
    industry_name: Optional[str] = None,
) -> Dict[str, Any]:
    """构建企业关联网络。

    Returns:
        标准化结构（始终成功返回，异常时 ``success=False`` 且 ``risk_tags`` 标注降级）。
    """
    try:
        resolved_code, is_listed = _resolve_stock_code(enterprise_name, stock_code)
        shareholders: List[Dict[str, Any]] = []
        actual_controller: Optional[Dict[str, Any]] = None
        guarantees: List[Dict[str, Any]] = []
        pledges: List[Dict[str, Any]] = []
        equity_freeze: List[Dict[str, Any]] = []
        supply_chain: Dict[str, List[str]] = {"upstream": [], "downstream": []}
        sources: List[str] = []

        if is_listed and resolved_code:
            listed = _gather_listed(resolved_code, enterprise_name)
            shareholders = listed["shareholders"]
            actual_controller = listed["actual_controller"]
            guarantees = listed["guarantees"]
            pledges = listed["pledges"]
            equity_freeze = listed["equity_freeze"]
            supply_chain = listed["supply_chain"]
            sources.append("巨潮/东方财富结构化")
        else:
            nr = _gather_nonlisted(enterprise_name)
            shareholders = nr["shareholders"]
            actual_controller = nr["actual_controller"]
            equity_freeze = nr["equity_freeze"]
            sources.append("元典企业工商")

        # 行业知识库补充上下游（若主营构成未覆盖）
        if not supply_chain.get("upstream") and not supply_chain.get("downstream") and industry_name:
            derived = _derive_supply_chain(industry_name)
            if derived.get("upstream") or derived.get("downstream"):
                supply_chain = derived
                sources.append("行业知识库")

        risk_tags = _compute_risk_tags(shareholders, actual_controller, guarantees, pledges, equity_freeze)
        success = bool(shareholders or guarantees or pledges or equity_freeze or actual_controller)
        if not success:
            risk_tags = [{
                "tag": "关联数据暂不可得",
                "level": "medium",
                "detail": "未从工商/财报/股权数据源获取到可用的关联信息，需人工核验股权、担保与关联关系。",
            }]

        return {
            "success": success,
            "enterprise_name": enterprise_name,
            "is_listed": is_listed,
            "stock_code": resolved_code,
            "data_source": " + ".join(sources) if sources else "未获取到关联数据",
            "shareholders": shareholders,
            "actual_controller": actual_controller,
            "guarantees": guarantees,
            "pledges": pledges,
            "equity_freeze": equity_freeze,
            "supply_chain": supply_chain,
            "related_parties": _collect_related_parties(shareholders, actual_controller, guarantees),
            "risk_tags": risk_tags,
            "risk_rating": _aggregate_rating(risk_tags),
        }
    except Exception as exc:
        logger.warning("relationship network build failed: %s", exc)
        return {
            "success": False,
            "error": str(exc),
            "enterprise_name": enterprise_name,
            "shareholders": [],
            "actual_controller": None,
            "guarantees": [],
            "pledges": [],
            "equity_freeze": [],
            "supply_chain": {"upstream": [], "downstream": []},
            "related_parties": [],
            "risk_tags": [{
                "tag": "关联数据暂不可得",
                "level": "medium",
                "detail": f"关联网络构建失败：{exc}；需人工核验股权、担保与关联关系。",
            }],
            "risk_rating": "medium",
        }
