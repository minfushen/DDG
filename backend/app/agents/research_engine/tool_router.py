"""Tool routing and execution for research tasks."""

from __future__ import annotations

from typing import Any, Dict, List

from app.agents.evidence import normalize_evidence, normalize_evidence_list
from app.agents.tools.bocha_search_tool import search_with_bocha
from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.listed_company_public_info_tool import fetch_listed_company_public_info_data
from app.rag.knowledge_retrieval_service import knowledge_hits_to_evidence, retrieve_knowledge

from .state import ResearchTask


def _bocha_query(enterprise_name: str, task: ResearchTask) -> tuple[str, str, str]:
    category = task.get("category")
    if task.get("search_query"):
        include = ""
        if category == "financial":
            include = "cninfo.com.cn|sse.com.cn|szse.cn|eastmoney.com|finance.eastmoney.com|data.eastmoney.com"
        elif category == "legal":
            include = "cninfo.com.cn|sse.com.cn|szse.cn|creditchina.gov.cn|court.gov.cn"
        return str(task.get("search_query")), "noLimit", include
    if category == "business":
        return f"{enterprise_name} 工商信息 统一社会信用代码 法定代表人 注册资本 经营状态", "noLimit", ""
    if category == "legal":
        return f"{enterprise_name} 重大诉讼 被执行 失信 行政处罚 公告", "oneYear", "cninfo.com.cn|sse.com.cn|szse.cn|creditchina.gov.cn|court.gov.cn"
    if category == "industry":
        return f"{enterprise_name} 主营业务 行业地位 研报 年报 竞争格局", "noLimit", ""
    if category == "financial":
        return f"{enterprise_name} 2024 2023 2022 年报 财务报表 营业收入 净利润 经营现金流 东方财富 巨潮资讯", "noLimit", "cninfo.com.cn|sse.com.cn|szse.cn|eastmoney.com|finance.eastmoney.com|data.eastmoney.com"
    return f"{enterprise_name} 授信 尽调 风险 审查", "noLimit", ""


def execute_research_task(enterprise_name: str, task: ResearchTask) -> Dict[str, Any]:
    """Execute a task with lightweight tools and return normalized evidence."""
    category = task.get("category") or "general"
    evidence: List[Dict[str, Any]] = []
    raw_outputs: Dict[str, Any] = {}
    errors: List[str] = []

    if "listed_company" in task.get("tool_hints", []):
        listed = resolve_listed_company(enterprise_name)
        raw_outputs["listed_company"] = {"matched": bool(listed)}
        if listed:
            evidence.append(normalize_evidence({
                "label": "上市公司主体识别",
                "value": f"{listed.get('company_name')} / {listed.get('stock_code')} / {listed.get('stock_exchange')}",
                "claim": f"{enterprise_name}匹配到上市主体{listed.get('company_name')}，证券代码{listed.get('stock_code')}。",
                "source": "本地上市公司映射表",
                "source_type": "listed_company_registry_hint",
                "confidence": 0.82,
                "trust_level": "medium",
                "requires_manual_review": True,
                "metadata": listed,
            }, agent=category, domain=category))

    if category == "financial":
        try:
            import asyncio
            from app.agents.sub_agents.financial_agent import run_financial_agent

            financial_result = asyncio.run(run_financial_agent(enterprise_name))
            raw_outputs["financial_agent"] = {
                "success": financial_result.get("success"),
                "error": financial_result.get("error"),
                "evidence_count": len(financial_result.get("evidence", [])),
                "has_report": bool(financial_result.get("financial_analysis_report")),
            }
            for item in financial_result.get("evidence", []):
                evidence.append(normalize_evidence(item, agent=category, domain=category))
            report = financial_result.get("financial_analysis_report") or {}
            if report:
                metrics = report.get("key_metrics") or {}
                years = report.get("years") or []
                evidence.append(normalize_evidence({
                    "label": "上市公司结构化财务分析",
                    "value": f"{report.get('risk_rating', '风险待定')} / {report.get('risk_score', '评分待定')}分 / 年度{', '.join(years)}",
                    "claim": f"已基于{report.get('generated_from', '公开财报')}形成近三年财务分析，核心指标包括营收{metrics.get('revenue', '不可用')}、净利润{metrics.get('net_profit', '不可用')}、资产负债率{metrics.get('debt_ratio', '不可用')}、经营现金流{metrics.get('operating_cash_flow', '不可用')}。",
                    "source": report.get("generated_from") or "东方财富公开财报",
                    "source_name": "上市公司近三年结构化财务数据",
                    "source_type": "financial_statement",
                    "confidence": 0.9,
                    "trust_level": "high",
                    "requires_manual_review": False,
                    "metadata": {"financial_analysis_report": report},
                }, agent=category, domain=category))
        except Exception as exc:
            errors.append(f"上市公司财务结构化分析失败：{type(exc).__name__}: {exc}")

    if category == "industry":
        try:
            public_info = fetch_listed_company_public_info_data(enterprise_name)
            raw_outputs["listed_company_public_info"] = {
                "success": public_info.get("success"),
                "error": public_info.get("error"),
                "main_business_count": len(public_info.get("main_business_composition", [])),
            }
            if public_info.get("success"):
                basic = public_info.get("basic_info") or {}
                main_business = public_info.get("main_business_composition") or []
                top_items = "；".join(
                    f"{item.get('item_name')}收入占比{item.get('income_ratio')}、毛利率{item.get('gross_margin')}"
                    for item in main_business[:3]
                    if item.get("item_name")
                )
                evidence.append(normalize_evidence({
                    "label": "上市公司行业与主营构成",
                    "value": top_items or basic.get("main_business") or basic.get("industry") or "已获取上市公司公开资料包",
                    "claim": f"公开资料显示主营业务为{basic.get('main_business') or '待复核'}，主营构成包括{top_items or '待进一步拆分'}。",
                    "source": public_info.get("data_source") or "东方财富F10 + 公开搜索",
                    "source_name": "上市公司公开资料包",
                    "source_type": "listed_company_public_info",
                    "confidence": 0.84,
                    "trust_level": "high",
                    "requires_manual_review": False,
                    "metadata": {"public_info": public_info},
                }, agent=category, domain=category))
                for item in public_info.get("evidence", []):
                    evidence.append(normalize_evidence({
                        **item,
                        "source_type": "listed_company_public_info",
                        "confidence": 0.82,
                        "trust_level": "high",
                        "requires_manual_review": False,
                    }, agent=category, domain=category))
            try:
                import asyncio
                from app.agents.sub_agents.industry_agent import run_industry_agent

                industry_result = asyncio.run(run_industry_agent(enterprise_name, public_info=public_info if public_info.get("success") else None))
                report = industry_result.get("industry_analysis_report") or {}
                raw_outputs["industry_agent"] = {
                    "success": industry_result.get("success"),
                    "error": industry_result.get("error"),
                    "evidence_count": len(industry_result.get("evidence", [])),
                    "has_report": bool(report),
                    "diagnostic_source": report.get("industry_diagnostic_source"),
                    "diagnostic_provider": report.get("industry_diagnostic_provider"),
                }
                for item in industry_result.get("evidence", []):
                    evidence.append(normalize_evidence(item, agent=category, domain=category))
                if report:
                    industry = report.get("industry") or {}
                    summary = report.get("industry_diagnostic_summary") or report.get("risk_summary") or []
                    evidence.append(normalize_evidence({
                        "label": "行业专项诊断报告",
                        "value": f"{industry.get('semantic_industry_name') or industry.get('name')} / {report.get('industry_diagnostic_source') or '诊断来源待定'}",
                        "claim": summary[0] if summary else f"已形成{industry.get('semantic_industry_name') or industry.get('name')}行业诊断。",
                        "source": report.get("generated_from") or "行业代码库 + RAG知识库 + 公开资料包",
                        "source_name": "行业专项诊断报告",
                        "source_type": "industry_diagnostic_report",
                        "confidence": 0.86 if report.get("industry_diagnostic_source") == "llm" else 0.78,
                        "trust_level": "high",
                        "requires_manual_review": False,
                        "metadata": {"industry_analysis_report": report},
                    }, agent=category, domain=category))
            except Exception as exc:
                errors.append(f"行业专项诊断失败：{type(exc).__name__}: {exc}")
        except Exception as exc:
            errors.append(f"上市公司公开资料包获取失败：{type(exc).__name__}: {exc}")

    if "rag" in task.get("tool_hints", []) or category in {"industry", "credit"}:
        domain = "industry" if category == "industry" else "credit" if category == "credit" else "all"
        query = " ".join([enterprise_name, task.get("question", ""), " ".join(task.get("required_evidence", []))])
        try:
            rag_result = retrieve_knowledge(query=query, domain=domain, top_k=5)
            raw_outputs["rag"] = {"mode": rag_result.get("mode"), "count": len(rag_result.get("results", []))}
            evidence.extend(knowledge_hits_to_evidence(rag_result.get("results", []), agent=category, domain=category))
        except Exception as exc:
            errors.append(f"RAG检索失败：{type(exc).__name__}")

    if "bocha_search" in task.get("tool_hints", []) or category in {"business", "legal", "industry", "financial"}:
        query, freshness, include = _bocha_query(enterprise_name, task)
        bocha_result = search_with_bocha(query=query, max_results=5, freshness=freshness, include=include, summary=True)
        raw_outputs["bocha"] = {
            "success": bocha_result.get("success"),
            "count": len(bocha_result.get("results", [])),
            "log_id": bocha_result.get("log_id"),
            "error": bocha_result.get("error"),
        }
        if bocha_result.get("success"):
            for item in bocha_result.get("results", []):
                label = "财报/业绩公开资料" if category == "financial" else "公开搜索线索"
                evidence.append(normalize_evidence({
                    "label": label,
                    "value": item.get("title") or item.get("content", "")[:80],
                    "claim": f"公开搜索命中：{item.get('title') or item.get('url')}",
                    "source": item.get("source") or item.get("url") or "Bocha Web Search",
                    "source_name": item.get("site_name") or "Bocha Web Search",
                    "source_url": item.get("url"),
                    "source_type": item.get("source_type") or "public_web_search_clue",
                    "confidence": item.get("confidence"),
                    "trust_level": item.get("trust_level"),
                    "requires_manual_review": item.get("requires_manual_review", True),
                    "metadata": item,
                }, agent=category, domain=category))
        elif bocha_result.get("error"):
            errors.append(f"博查搜索失败：{bocha_result.get('error')}")

    normalized = normalize_evidence_list(evidence, agent=category, domain=category)
    return {
        "success": bool(normalized),
        "task_id": task.get("id"),
        "category": category,
        "evidence": normalized,
        "raw_outputs": raw_outputs,
        "errors": errors,
    }
