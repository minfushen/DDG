"""Tool routing and execution for research tasks."""

from __future__ import annotations

from typing import Any, Dict, List

from app.agents.evidence import normalize_evidence, normalize_evidence_list
from app.agents.tools.bocha_search_tool import search_with_bocha
from app.agents.tools.cninfo_announcement_tool import search_cninfo_announcements
from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.listed_company_public_info_tool import fetch_listed_company_public_info_data
from app.agents.tools.searxng_search_tool import search_with_searxng
from app.config import settings
from app.rag.knowledge_retrieval_service import knowledge_hits_to_evidence, retrieve_knowledge

from .public_search_pipeline import process_public_search_results
from .state import ResearchTask
from .tool_trace import annotate_evidence, finish_tool_trace, start_tool_trace


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


def _cninfo_keyword(category: str) -> str:
    if category == "financial":
        return "年报 业绩快报 审计意见"
    if category == "legal":
        return "诉讼 仲裁 处罚 监管函"
    if category == "industry":
        return "年报 主营业务 问询函"
    return "公告"


def execute_research_task(enterprise_name: str, task: ResearchTask) -> Dict[str, Any]:
    """Execute a task with lightweight tools and return normalized evidence."""
    category = task.get("category") or "general"
    evidence: List[Dict[str, Any]] = []
    raw_outputs: Dict[str, Any] = {}
    errors: List[str] = []
    tool_traces: List[Dict[str, Any]] = []
    research_task_id = str(task.get("id") or "unknown_task")

    if "listed_company" in task.get("tool_hints", []):
        trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="listed_company",
            query=enterprise_name,
            query_summary="识别企业是否存在上市主体映射",
            category=category,
        )
        listed = resolve_listed_company(enterprise_name)
        raw_outputs["listed_company"] = {"matched": bool(listed)}
        before_count = len(evidence)
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
        new_evidence = evidence[before_count:]
        annotate_evidence(new_evidence, trace)
        tool_traces.append(finish_tool_trace(trace, status="success" if listed else "empty", result_count=1 if listed else 0))

    if category == "financial":
        trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="financial_agent",
            query=enterprise_name,
            query_summary="抽取近三年财务指标并生成财务诊断",
            category=category,
        )
        before_count = len(evidence)
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
            new_evidence = evidence[before_count:]
            annotate_evidence(new_evidence, trace)
            tool_traces.append(finish_tool_trace(
                trace,
                status="success" if financial_result.get("success") else "failed",
                result_count=len(new_evidence),
            ))
        except Exception as exc:
            errors.append(f"上市公司财务结构化分析失败：{type(exc).__name__}: {exc}")
            tool_traces.append(finish_tool_trace(trace, status="failed", error=f"{type(exc).__name__}: {exc}"))

    if category in {"financial", "industry", "legal"}:
        trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="cninfo_announcements",
            query=f"{enterprise_name} {_cninfo_keyword(category)}",
            query_summary="检索巨潮资讯公告和年报原文证据",
            category=category,
        )
        before_count = len(evidence)
        cninfo_result = search_cninfo_announcements(
            enterprise_name=enterprise_name,
            keyword=_cninfo_keyword(category),
            max_results=6,
        )
        raw_outputs["cninfo_announcements"] = {
            "success": cninfo_result.get("success"),
            "count": len(cninfo_result.get("results", [])),
            "error": cninfo_result.get("error"),
        }
        if cninfo_result.get("success"):
            for item in cninfo_result.get("evidence", []):
                evidence.append(normalize_evidence(item, agent=category, domain=category))
            new_evidence = evidence[before_count:]
            annotate_evidence(new_evidence, trace)
            tool_traces.append(finish_tool_trace(trace, status="success", result_count=len(new_evidence)))
        else:
            tool_traces.append(finish_tool_trace(trace, status="empty" if not cninfo_result.get("error") else "failed", error=cninfo_result.get("error")))

    if category == "industry":
        public_info_trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="listed_company_public_info",
            query=enterprise_name,
            query_summary="采集上市公司主营业务、主营构成和公告线索",
            category=category,
        )
        before_public_count = len(evidence)
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
            public_new_evidence = evidence[before_public_count:]
            annotate_evidence(public_new_evidence, public_info_trace)
            tool_traces.append(finish_tool_trace(
                public_info_trace,
                status="success" if public_info.get("success") else "failed",
                result_count=len(public_new_evidence),
                error=public_info.get("error"),
            ))
            industry_trace = start_tool_trace(
                research_task_id=research_task_id,
                internal_tool_name="industry_agent",
                query=enterprise_name,
                query_summary="识别行业子赛道并生成行业诊断",
                category=category,
            )
            before_industry_count = len(evidence)
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
                industry_new_evidence = evidence[before_industry_count:]
                annotate_evidence(industry_new_evidence, industry_trace)
                tool_traces.append(finish_tool_trace(
                    industry_trace,
                    status="success" if industry_result.get("success") else "failed",
                    result_count=len(industry_new_evidence),
                    error=industry_result.get("error"),
                ))
            except Exception as exc:
                errors.append(f"行业专项诊断失败：{type(exc).__name__}: {exc}")
                tool_traces.append(finish_tool_trace(industry_trace, status="failed", error=f"{type(exc).__name__}: {exc}"))
        except Exception as exc:
            errors.append(f"上市公司公开资料包获取失败：{type(exc).__name__}: {exc}")
            tool_traces.append(finish_tool_trace(public_info_trace, status="failed", error=f"{type(exc).__name__}: {exc}"))

    if "rag" in task.get("tool_hints", []) or category in {"industry", "credit"}:
        domain = "industry" if category == "industry" else "credit" if category == "credit" else "all"
        query = " ".join([enterprise_name, task.get("question", ""), " ".join(task.get("required_evidence", []))])
        trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="rag",
            query=query,
            query_summary="检索内部授信知识库和行业/财务审查规则",
            category=category,
        )
        before_count = len(evidence)
        try:
            rag_result = retrieve_knowledge(query=query, domain=domain, top_k=5, company_name=enterprise_name)
            raw_outputs["rag"] = {"mode": rag_result.get("mode"), "count": len(rag_result.get("results", []))}
            evidence.extend(knowledge_hits_to_evidence(rag_result.get("results", []), agent=category, domain=category))
            new_evidence = evidence[before_count:]
            annotate_evidence(new_evidence, trace)
            tool_traces.append(finish_tool_trace(trace, status="success", result_count=len(new_evidence)))
        except Exception as exc:
            errors.append(f"RAG检索失败：{type(exc).__name__}")
            tool_traces.append(finish_tool_trace(trace, status="failed", error=f"{type(exc).__name__}: {exc}"))

    if "bocha_search" in task.get("tool_hints", []) or category in {"business", "legal", "industry", "financial"}:
        query, freshness, include = _bocha_query(enterprise_name, task)
        trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="bocha",
            query=query,
            query_summary="检索公开资料、公告、财报、司法和行业线索",
            category=category,
        )
        before_count = len(evidence)
        bocha_result = search_with_bocha(query=query, max_results=5, freshness=freshness, include=include, summary=True)
        raw_outputs["bocha"] = {
            "success": bocha_result.get("success"),
            "count": len(bocha_result.get("results", [])),
            "log_id": bocha_result.get("log_id"),
            "error": bocha_result.get("error"),
        }
        if bocha_result.get("success"):
            pipeline_result = process_public_search_results(
                provider_results=bocha_result.get("results", []),
                category=category,
                query=query,
                agent=category,
                max_results=5,
            )
            raw_outputs["bocha_pipeline"] = {
                "stats": pipeline_result.get("stats"),
                "filtered_count": len(pipeline_result.get("filtered_results", [])),
                "crawl_attempts": pipeline_result.get("crawl_attempts", []),
            }
            search_evidence_start = len(evidence)
            evidence.extend(pipeline_result.get("evidence", []))
            new_evidence = evidence[search_evidence_start:]
            annotate_evidence(new_evidence, trace)
            tool_traces.append(finish_tool_trace(trace, status="success", result_count=len(new_evidence)))
        elif bocha_result.get("error"):
            errors.append(f"博查搜索失败：{bocha_result.get('error')}")
            tool_traces.append(finish_tool_trace(trace, status="failed", error=bocha_result.get("error")))

        if settings.ENABLE_SEARXNG_SEARCH:
            searx_trace = start_tool_trace(
                research_task_id=research_task_id,
                internal_tool_name="searxng",
                query=query,
                query_summary="通过公开资料聚合检索补充候选证据",
                category=category,
            )
            before_searx_count = len(evidence)
            searx_result = search_with_searxng(query=query, max_results=settings.SEARXNG_MAX_RESULTS)
            raw_outputs["searxng"] = {
                "success": searx_result.get("success"),
                "count": len(searx_result.get("results", [])),
                "error": searx_result.get("error"),
                "unresponsive_engines": searx_result.get("unresponsive_engines", []),
            }
            if searx_result.get("success"):
                searx_pipeline_result = process_public_search_results(
                    provider_results=searx_result.get("results", []),
                    category=category,
                    query=query,
                    agent=category,
                    max_results=settings.SEARXNG_MAX_RESULTS,
                )
                raw_outputs["searxng_pipeline"] = {
                    "stats": searx_pipeline_result.get("stats"),
                    "filtered_count": len(searx_pipeline_result.get("filtered_results", [])),
                    "crawl_attempts": searx_pipeline_result.get("crawl_attempts", []),
                }
                evidence.extend(searx_pipeline_result.get("evidence", []))
                searx_new_evidence = evidence[before_searx_count:]
                annotate_evidence(searx_new_evidence, searx_trace)
                tool_traces.append(finish_tool_trace(searx_trace, status="success", result_count=len(searx_new_evidence)))
            else:
                if searx_result.get("error"):
                    errors.append(f"聚合搜索失败：{searx_result.get('error')}")
                tool_traces.append(finish_tool_trace(searx_trace, status="failed" if searx_result.get("error") else "empty", error=searx_result.get("error")))

    normalized = normalize_evidence_list(evidence, agent=category, domain=category)
    by_id = {item.get("id"): item for item in normalized if item.get("id")}
    for trace in tool_traces:
        ids = [item_id for item_id, item in by_id.items() if item.get("tool_call_id") == trace.get("tool_call_id")]
        trace["evidence_ids"] = ids
    return {
        "success": bool(normalized),
        "task_id": task.get("id"),
        "category": category,
        "evidence": normalized,
        "raw_outputs": raw_outputs,
        "tool_traces": tool_traces,
        "errors": errors,
    }
