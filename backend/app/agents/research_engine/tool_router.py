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
from app.config.rag_loader import get_knowledge_retrieval_top_k
from app.rag.knowledge_retrieval_service import knowledge_hits_to_evidence, retrieve_knowledge

from .public_search_pipeline import process_public_search_results
from .state import ResearchTask
from .tool_middleware import run_tool
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


def _listed_stock_code(raw_outputs: Dict[str, Any]) -> str | None:
    """Extract stock_code from listed_company identification result."""
    listed = raw_outputs.get("listed_company") or {}
    if not listed.get("matched"):
        return None
    # listed_company raw output stores the full dict in metadata,
    # but we also store matched=True; the actual stock_code comes from
    # the evidence metadata.  We re-resolve here for simplicity.
    return listed.get("stock_code")


def execute_research_task(
    enterprise_name: str,
    task: ResearchTask,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a task with lightweight tools and return normalized evidence."""
    category = task.get("category") or "general"
    evidence: List[Dict[str, Any]] = []
    raw_outputs: Dict[str, Any] = {}
    errors: List[str] = []
    tool_traces: List[Dict[str, Any]] = []
    research_task_id = str(task.get("id") or "unknown_task")

    # ── Step 0: Listed company identification ──────────────────────
    # This step has special logic (sets stock_code in raw_outputs for
    # downstream tools), so it stays outside the middleware.
    if "listed_company" in task.get("tool_hints", []):
        trace = start_tool_trace(
            research_task_id=research_task_id,
            internal_tool_name="listed_company",
            query=enterprise_name,
            query_summary="识别企业是否存在上市主体映射",
            category=category,
        )
        listed = resolve_listed_company(enterprise_name)
        before_count = len(evidence)
        if listed:
            raw_outputs["listed_company"] = {
                "matched": True,
                "stock_code": listed.get("stock_code"),
                "company_name": listed.get("company_name"),
            }
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
        else:
            raw_outputs["listed_company"] = {"matched": False}
        new_evidence = evidence[before_count:]
        annotate_evidence(new_evidence, trace)
        tool_traces.append(finish_tool_trace(trace, status="success" if listed else "empty", result_count=1 if listed else 0))

    # ── Step 1: Financial analysis ─────────────────────────────────
    if category == "financial":
        import asyncio
        from app.agents.sub_agents.financial_agent import run_financial_agent

        def _extract_financial(result):
            for item in result.get("evidence", []):
                evidence.append(normalize_evidence(item, agent=category, domain=category))
            report = result.get("financial_analysis_report") or {}
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

        fin_result = run_tool(
            tool_name="financial_agent",
            tool_fn=lambda: asyncio.run(run_financial_agent(enterprise_name, session_id=session_id, task_id=research_task_id)),
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=enterprise_name,
            query_summary="抽取近三年财务指标并生成财务诊断",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_financial,
            result_key="financial_agent",
        )

        # ── structured financial data: Eastmoney (primary) → cninfo (fallback) ──
        stock_code = _listed_stock_code(raw_outputs)
        if stock_code:

            def _fetch_structured_financial():
                """Eastmoney first; cninfo as fallback."""
                from app.agents.tools.eastmoney_structured_tool import eastmoney_build_financial_summary
                result = eastmoney_build_financial_summary(stock_code)
                if result.get("success"):
                    result["_provider"] = "eastmoney"
                    return result
                # Eastmoney failed; try cninfo as fallback.
                from app.agents.tools.cninfo_webapi_tool import build_financial_summary
                cninfo_result = build_financial_summary(stock_code)
                if cninfo_result.get("success"):
                    cninfo_result["_provider"] = "cninfo"
                else:
                    cninfo_result["_provider"] = "none"
                    cninfo_result["_eastmoney_error"] = result.get("error")
                return cninfo_result

            def _extract_structured_financial(result):
                provider = result.get("_provider", "none")
                if not result.get("success"):
                    eastmoney_err = result.get("_eastmoney_error")
                    cninfo_err = result.get("error")
                    detail = []
                    if eastmoney_err:
                        detail.append(f"东方财富：{eastmoney_err}")
                    if cninfo_err:
                        detail.append(f"巨潮：{cninfo_err}")
                    evidence.append(normalize_evidence({
                        "label": "结构化财务数据（不可用）",
                        "value": "东方财富和巨潮均未返回数据，已降级",
                        "claim": f"结构化财务数据获取失败：{'；'.join(detail)}；本次财务结论以AKShare/东方财富公开财报为准。",
                        "source": "东方财富F10 + 巨潮资讯WebAPI",
                        "source_name": "结构化财务报表（不可用）",
                        "source_type": "structured_financial_unavailable",
                        "confidence": 0.3,
                        "trust_level": "low",
                        "requires_manual_review": True,
                        "metadata": result,
                    }, agent=category, domain=category))
                    return
                bs = result.get("balance_sheet") or {}
                cf = result.get("cash_flow") or {}
                ind = result.get("indicators") or {}
                ta = bs.get("total_assets")
                if not ta:
                    evidence.append(normalize_evidence({
                        "label": "结构化财务数据（无有效数据）",
                        "value": "接口返回但无有效财务记录",
                        "claim": f"结构化接口未返回{stock_code}有效财务记录，本次财务结论以AKShare/东方财富公开财报为准。",
                        "source": "东方财富F10" if provider == "eastmoney" else "巨潮资讯WebAPI",
                        "source_name": "结构化财务报表（无有效数据）",
                        "source_type": "structured_financial_no_data",
                        "confidence": 0.3,
                        "trust_level": "low",
                        "requires_manual_review": True,
                        "metadata": result,
                    }, agent=category, domain=category))
                    return

                source_name = "东方财富F10结构化财务报表" if provider == "eastmoney" else "巨潮官方结构化财务报表"
                source_url = (
                    f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={stock_code}"
                    if provider == "eastmoney"
                    else "巨潮资讯WebAPI (webapi.cninfo.com.cn)"
                )
                # 东方财富 MAINFINADATA 的比率字段已经是百分比（如 91.18 = 91.18%），
                # cninfo 也是百分比格式，统一按百分比展示。
                roe = ind.get("roe", 0) or 0
                gm = ind.get("gross_margin", 0) or 0
                evidence.append(normalize_evidence({
                    "label": "结构化财务数据",
                    "value": f"总资产{ta / 1e8:.0f}亿 / ROE{roe:.1f}% / 毛利率{gm:.1f}%",
                    "claim": (
                        f"{'东方财富F10' if provider == 'eastmoney' else '巨潮官方API'}获取{stock_code}（报告期{result.get('report_date')}）资产负债表：总资产{ta / 1e8:.0f}亿、"
                        f"总负债{(bs.get('total_liabilities') or 0) / 1e8:.0f}亿；"
                        f"现金流：经营{(cf.get('operating') or 0) / 1e8:.0f}亿；"
                        f"指标：ROE{roe:.1f}%、毛利率{gm:.1f}%。"
                    ),
                    "source": source_url,
                    "source_name": source_name,
                    "source_type": "eastmoney_structured_financial" if provider == "eastmoney" else "cninfo_webapi_financial",
                    "confidence": 0.92,
                    "trust_level": "high",
                    "requires_manual_review": False,
                    "metadata": result,
                }, agent=category, domain=category))

            run_tool(
                tool_name="structured_financial",
                tool_fn=_fetch_structured_financial,
                research_task_id=research_task_id,
            session_id=session_id,
                category=category,
                query=stock_code,
                query_summary="东方财富/巨潮结构化财务三表+指标",
                evidence=evidence,
                raw_outputs=raw_outputs,
                errors=errors,
                tool_traces=tool_traces,
                extract_evidence=_extract_structured_financial,
                result_key="structured_financial",
            )

    # ── Step 2: Cninfo announcements (financial / industry / legal) ─
    if category in {"financial", "industry", "legal"}:
        def _fetch_cninfo_announcements():
            return search_cninfo_announcements(
                enterprise_name=enterprise_name,
                keyword=_cninfo_keyword(category),
                max_results=6,
            )

        def _extract_cninfo_announcements(result):
            if result.get("success"):
                for item in result.get("evidence", []):
                    evidence.append(normalize_evidence(item, agent=category, domain=category))

        cninfo_result = run_tool(
            tool_name="cninfo_announcements",
            tool_fn=_fetch_cninfo_announcements,
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=f"{enterprise_name} {_cninfo_keyword(category)}",
            query_summary="检索巨潮资讯公告和年报原文证据",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_cninfo_announcements,
            result_key="cninfo_announcements",
        )
        # Store raw_outputs detail manually (middleware only stores keys)
        if cninfo_result:
            raw_outputs["cninfo_announcements"] = {
                "success": cninfo_result.get("success"),
                "count": len(cninfo_result.get("results", [])),
                "error": cninfo_result.get("error"),
            }

    # ── Step 3: Industry analysis ──────────────────────────────────
    if category == "industry":
        def _fetch_public_info():
            return fetch_listed_company_public_info_data(enterprise_name)

        def _extract_public_info(public_info):
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

        public_info = run_tool(
            tool_name="listed_company_public_info",
            tool_fn=_fetch_public_info,
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=enterprise_name,
            query_summary="采集上市公司主营业务、主营构成和公告线索",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_public_info,
            result_key="listed_company_public_info",
        )

        if public_info:
            import asyncio
            from app.agents.sub_agents.industry_agent import run_industry_agent
            from app.api.cache_store import tool_cache_key, get_tool_cache

            # 尝试复用财务 Agent 已抽取的年报注释（含深度归因）。
            annual_report_notes = None
            try:
                cache_key = tool_cache_key("annual_report_notes", {"enterprise_name": enterprise_name})
                cached = get_tool_cache(cache_key)
                if cached:
                    annual_report_notes = cached.get("result")
            except Exception:
                annual_report_notes = None

            def _extract_industry(result):
                report = result.get("industry_analysis_report") or {}
                raw_outputs["industry_agent"] = {
                    "success": result.get("success"),
                    "error": result.get("error"),
                    "evidence_count": len(result.get("evidence", [])),
                    "has_report": bool(report),
                    "diagnostic_source": report.get("industry_diagnostic_source"),
                    "diagnostic_provider": report.get("industry_diagnostic_provider"),
                }
                for item in result.get("evidence", []):
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

            run_tool(
                tool_name="industry_agent",
                tool_fn=lambda: asyncio.run(run_industry_agent(
                    enterprise_name,
                    public_info=public_info if public_info.get("success") else None,
                    annual_report_notes=annual_report_notes,
                    session_id=session_id,
                    task_id=research_task_id,
                )),
                research_task_id=research_task_id,
                session_id=session_id,
                category=category,
                query=enterprise_name,
                query_summary="识别行业子赛道并生成行业诊断",
                evidence=evidence,
                raw_outputs=raw_outputs,
                errors=errors,
                tool_traces=tool_traces,
                extract_evidence=_extract_industry,
                result_key="industry_agent",
            )

    # ── Step 4: Legal / risk analysis ──────────────────────────────
    if category == "legal":
        stock_code = _listed_stock_code(raw_outputs)

        # cninfo_webapi: structured risk data (litigation, penalties, etc.)
        if stock_code:
            def _fetch_cninfo_risk():
                from app.agents.tools.cninfo_webapi_tool import build_risk_profile
                return build_risk_profile(stock_code)

            def _extract_cninfo_risk(result):
                # 接口失败时降级，不伪装成"0条风险"。
                if not result.get("success"):
                    evidence.append(normalize_evidence({
                        "label": "巨潮WebAPI司法风险数据（不可用）",
                        "value": "巨潮官方司法接口未返回数据，已降级",
                        "claim": f"巨潮WebAPI司法风险数据获取失败：{result.get('error') or '接口调用失败'}；如已配置 CNINFO_ACCESS_KEY/SECRET，系统会自动刷新 token，请检查配置；司法结论以公开搜索线索为准，正式授信前需人工复核裁判文书网、执行信息公开网等权威源。",
                        "source": "巨潮资讯WebAPI (webapi.cninfo.com.cn)",
                        "source_name": "巨潮官方司法风险数据",
                        "source_type": "cninfo_webapi_risk_unavailable",
                        "confidence": 0.3,
                        "trust_level": "low",
                        "requires_manual_review": True,
                        "metadata": result,
                    }, agent=category, domain=category))
                    return
                total_events = sum(
                    v.get("count", 0)
                    for v in result.values()
                    if isinstance(v, dict) and "count" in v
                )
                details = []
                for key, label in [("litigation", "诉讼"), ("guarantees", "担保"), ("penalties", "处罚"), ("asset_freezes", "资产冻结"), ("arbitration", "仲裁")]:
                    section = result.get(key) or {}
                    if section.get("count", 0) > 0:
                        details.append(f"{label}{section['count']}条")
                evidence.append(normalize_evidence({
                    "label": "巨潮WebAPI司法风险数据",
                    "value": f"共{total_events}条风险记录" + (f"（{'、'.join(details)}）" if details else ""),
                    "claim": f"巨潮官方API获取{stock_code}司法风险数据：诉讼{result.get('litigation', {}).get('count', 0)}条、对外担保{result.get('guarantees', {}).get('count', 0)}条、处罚{result.get('penalties', {}).get('count', 0)}条、资产冻结{result.get('asset_freezes', {}).get('count', 0)}条、仲裁{result.get('arbitration', {}).get('count', 0)}条。",
                    "source": "巨潮资讯WebAPI (webapi.cninfo.com.cn)",
                    "source_name": "巨潮官方司法风险数据",
                    "source_type": "cninfo_webapi_risk",
                    "confidence": 0.95,
                    "trust_level": "authoritative",
                    "requires_manual_review": total_events > 0,
                    "metadata": result,
                }, agent=category, domain=category))

            run_tool(
                tool_name="cninfo_webapi_risk",
                tool_fn=_fetch_cninfo_risk,
                research_task_id=research_task_id,
            session_id=session_id,
                category=category,
                query=stock_code,
                query_summary="巨潮WebAPI诉讼/担保/处罚/冻结/仲裁",
                evidence=evidence,
                raw_outputs=raw_outputs,
                errors=errors,
                tool_traces=tool_traces,
                extract_evidence=_extract_cninfo_risk,
                result_key="cninfo_webapi_risk",
            )

        # yuandian legal: case semantic search by enterprise name (works with or without stock code)
        def _fetch_yuandian_legal():
            from app.agents.tools.yuandian_legal_tool import build_legal_risk_profile
            return build_legal_risk_profile(enterprise_name)

        def _extract_yuandian_legal(result):
            if not result.get("success"):
                evidence.append(normalize_evidence({
                    "label": "元典司法风险数据（不可用）",
                    "value": "元典案例接口未返回数据，已降级",
                    "claim": f"元典司法风险数据获取失败：{result.get('error') or '接口调用失败'}；司法结论以公开搜索线索为准，正式授信前需人工复核裁判文书网、执行信息公开网等权威源。",
                    "source": "元典开放平台 (open.chineselaw.com)",
                    "source_name": "元典案例/司法风险数据",
                    "source_type": "yuandian_legal_risk_unavailable",
                    "confidence": 0.3,
                    "trust_level": "low",
                    "requires_manual_review": True,
                    "metadata": result,
                }, agent=category, domain=category))
                return
            summary = result.get("summary") or {}
            total = summary.get("total", result.get("total", 0))
            court_levels = summary.get("court_level_distribution") or {}
            categories = summary.get("case_category_distribution") or {}
            causes = summary.get("case_cause_distribution") or {}
            procedures = summary.get("trial_procedure_distribution") or {}

            detail_parts = []
            if causes:
                detail_parts.append("主要案由：" + "、".join(f"{k}({v})" for k, v in sorted(causes.items(), key=lambda x: -x[1])[:3]))
            if court_levels:
                detail_parts.append("审理法院层级：" + "、".join(f"{k}{v}条" for k, v in court_levels.items()))
            if procedures:
                detail_parts.append("审理程序：" + "、".join(f"{k}{v}条" for k, v in procedures.items()))

            top_summaries = (result.get("case_summaries") or [])[:3]
            sample_claims = []
            for s in top_summaries:
                role_parts = []
                if s.get("plaintiffs"):
                    role_parts.append(f"原告{'、'.join(s['plaintiffs'])}")
                if s.get("defendants"):
                    role_parts.append(f"被告{'、'.join(s['defendants'])}")
                if not role_parts and s.get("parties"):
                    role_parts.append(f"当事人{'、'.join(s['parties'])}")
                parts = [p for p in [
                    s.get("case_cause"),
                    " | ".join(role_parts) if role_parts else None,
                    s.get("court"),
                    s.get("judgment_date"),
                ] if p]
                if parts:
                    sample_claims.append("；".join(parts))

            claim = f"元典案例库检索{enterprise_name}司法风险：共{total}条记录"
            if detail_parts:
                claim += "。" + "。".join(detail_parts)
            if sample_claims:
                claim += "。典型案件：" + "；".join(sample_claims) + "。"
            else:
                claim += "，暂未发现明显风险记录。"

            evidence.append(normalize_evidence({
                "label": "元典司法风险数据",
                "value": f"共{total}条风险记录" + (f"（{'、'.join(detail_parts[:2])}）" if detail_parts else ""),
                "claim": claim,
                "source": "元典开放平台 (open.chineselaw.com)",
                "source_name": "元典案例/司法风险数据",
                "source_type": "yuandian_legal_risk",
                "confidence": 0.85 if total > 0 else 0.7,
                "trust_level": "high" if total > 0 else "medium",
                "requires_manual_review": total > 0,
                "metadata": result,
            }, agent=category, domain=category))

        run_tool(
            tool_name="yuandian_legal_risk",
            tool_fn=_fetch_yuandian_legal,
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=enterprise_name,
            query_summary="元典案例库司法风险语义检索",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_yuandian_legal,
            result_key="yuandian_legal_risk",
        )

    # ── Step 5: Business / shareholder analysis ────────────────────
    if category == "business":
        stock_code = _listed_stock_code(raw_outputs)

        # structured business data: Eastmoney (primary) → cninfo (fallback)
        if stock_code:

            def _fetch_structured_business():
                from app.agents.tools.eastmoney_structured_tool import eastmoney_fetch_business_data
                result = eastmoney_fetch_business_data(stock_code)
                if result.get("basic", {}).get("success"):
                    result["_provider"] = "eastmoney"
                    return result
                # Eastmoney failed; try cninfo as fallback.
                from app.agents.tools.cninfo_webapi_tool import fetch_company_basic_info, build_shareholder_profile, build_shareholder_table
                basic = fetch_company_basic_info(stock_code)
                shareholders = build_shareholder_profile(stock_code)
                shareholder_table = build_shareholder_table(stock_code)
                cninfo_result = {"basic": basic, "shareholders": shareholders, "shareholder_table": shareholder_table}
                cninfo_result["_provider"] = "cninfo" if basic.get("success") else "none"
                cninfo_result["_eastmoney_error"] = result.get("basic", {}).get("error")
                return cninfo_result

            def _extract_structured_business(result):
                basic = result.get("basic") or {}
                shareholders = result.get("shareholders") or {}
                shareholder_table = result.get("shareholder_table") or {}
                provider = result.get("_provider", "none")

                # 任一上游失败都按降级处理，避免用空记录贴 high/authoritative 标签。
                basic_failed = not basic.get("success")
                shareholder_table_failed = not shareholder_table.get("success")
                if basic_failed:
                    detail_parts = []
                    if result.get("_eastmoney_error"):
                        detail_parts.append(f"东方财富：{result['_eastmoney_error']}")
                    if basic.get("error"):
                        detail_parts.append(f"巨潮：{basic.get('error')}")
                    evidence.append(normalize_evidence({
                        "label": "工商与股东数据（不可用）",
                        "value": "结构化工商接口未返回数据，已降级",
                        "claim": f"工商与股东数据获取失败：{'；'.join(detail_parts) if detail_parts else '接口调用失败'}；工商结论以公开搜索和上市公司映射表为准，正式授信前需人工复核权威工商登记。",
                        "source": "东方财富F10 + 巨潮资讯WebAPI",
                        "source_name": "结构化工商与股东数据",
                        "source_type": "official_business_registry_unavailable",
                        "confidence": 0.3,
                        "trust_level": "low",
                        "requires_manual_review": True,
                        "metadata": result,
                    }, agent=category, domain=category))
                    return

                basic_record = (basic.get("records") or [{}])[0]
                top = shareholders.get("top_shareholders") or {}
                ctrl = shareholders.get("actual_controller") or {}
                ctrl_records = ctrl.get("records", [])
                # F004V compatibility: cninfo tool_router reads records[-1].F004V.
                # eastmoney_structured_tool stores the controller name at F004V too.
                latest_ctrl = ctrl_records[-1].get("F004V") if ctrl_records else None

                # Build structured fields for claim_builder (unchanged downstream contract).
                biz_fields = {}
                if basic_record.get("company_name"):
                    biz_fields["企业名称"] = basic_record["company_name"]
                if basic_record.get("stock_code"):
                    biz_fields["证券代码"] = basic_record["stock_code"]
                if latest_ctrl:
                    biz_fields["实际控制人"] = latest_ctrl
                if basic_record.get("controller_type"):
                    biz_fields["控制方式"] = basic_record["controller_type"]

                # Build human-readable claim with actual values
                field_parts = []
                for k, v in biz_fields.items():
                    if v:
                        field_parts.append(f"{k}：{v}")

                if not field_parts:
                    evidence.append(normalize_evidence({
                        "label": "工商与股东数据（部分字段缺失）",
                        "value": "结构化工商接口返回字段不完整",
                        "claim": f"结构化接口返回{stock_code}工商基础数据，但企业名称、实际控制人等核心字段缺失，建议以权威工商登记和公开搜索为准。",
                        "source": "东方财富F10" if provider == "eastmoney" else "巨潮资讯WebAPI",
                        "source_name": "结构化工商与股东数据",
                        "source_type": "official_business_registry_partial",
                        "confidence": 0.5,
                        "trust_level": "medium",
                        "requires_manual_review": True,
                        "metadata": result,
                    }, agent=category, domain=category))
                    return

                source_label = "东方财富F10" if provider == "eastmoney" else "巨潮官方API"
                evidence.append(normalize_evidence({
                    "label": "工商与股东数据",
                    "value": "；".join(field_parts[:6]),
                    "claim": (
                        f"{source_label}获取{basic_record.get('company_name', stock_code)}工商与股东数据："
                        f"{'；'.join(field_parts)}；"
                        f"十大股东{top.get('count', 0)}条记录。"
                    ),
                    "source": (
                        f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={stock_code}"
                        if provider == "eastmoney"
                        else "巨潮资讯WebAPI (webapi.cninfo.com.cn)"
                    ),
                    "source_name": source_label + "工商与股东数据",
                    "source_type": "official_business_registry",
                    "confidence": 0.92,
                    "trust_level": "high",
                    "requires_manual_review": False,
                    "metadata": {
                        **result,
                        "extracted_fields": {"business_fields": biz_fields},
                        "shareholder_table": shareholder_table,
                    },
                }, agent=category, domain=category))

            run_tool(
                tool_name="structured_business",
                tool_fn=_fetch_structured_business,
                research_task_id=research_task_id,
            session_id=session_id,
                category=category,
                query=stock_code,
                query_summary="东方财富/巨潮公司基础信息+股东画像",
                evidence=evidence,
                raw_outputs=raw_outputs,
                errors=errors,
                tool_traces=tool_traces,
                extract_evidence=_extract_structured_business,
                result_key="structured_business",
            )

        # yuandian company: business registry + judicial risk by enterprise name
        def _fetch_yuandian_company():
            from app.agents.tools.yuandian_company_tool import build_business_profile
            return build_business_profile(enterprise_name)

        def _extract_yuandian_company(result):
            if not result.get("success"):
                evidence.append(normalize_evidence({
                    "label": "元典企业工商与风险数据（不可用）",
                    "value": "元典企业接口未返回数据，已降级",
                    "claim": f"元典企业工商与风险数据获取失败：{result.get('error') or '接口调用失败'}；工商结论以结构化接口和公开搜索为准，正式授信前需人工复核权威工商登记。",
                    "source": "元典开放平台 (open.chineselaw.com)",
                    "source_name": "元典企业工商与风险数据",
                    "source_type": "yuandian_business_unavailable",
                    "confidence": 0.3,
                    "trust_level": "low",
                    "requires_manual_review": True,
                    "metadata": result,
                }, agent=category, domain=category))
                return
            basic = result.get("basic_info") or {}
            basic_records = basic.get("records") or []
            basic_record = basic_records[0] if basic_records else {}
            risk = result.get("risk_summary") or {}
            risk_records = risk.get("records") or []
            risk_record = risk_records[0] if risk_records else {}

            biz_fields = {}
            name = basic_record.get("company_name") or basic_record.get("enterpriseName") or basic_record.get("qymc")
            if name:
                biz_fields["企业名称"] = name
            legal = basic_record.get("legalPerson") or basic_record.get("frdb") or basic_record.get("fddbr")
            if legal:
                biz_fields["法定代表人"] = legal
            capital = basic_record.get("registeredCapital") or basic_record.get("zczb") or basic_record.get("zczb金額")
            if capital:
                biz_fields["注册资本"] = capital
            status = basic_record.get("registrationStatus") or basic_record.get("enterpriseStatus") or basic_record.get("jyzt")
            if status:
                biz_fields["经营状态"] = status

            total_writs = risk_record.get("total") or risk_record.get("writTotal") or risk_record.get("writCount") or 0
            value_parts = [f"{k}：{v}" for k, v in list(biz_fields.items())[:4]]
            if total_writs:
                value_parts.append(f"涉诉{total_writs}条")
            evidence.append(normalize_evidence({
                "label": "元典企业工商与风险数据",
                "value": " / ".join(value_parts) if value_parts else "元典企业库已返回数据",
                "claim": f"元典企业库获取{biz_fields.get('企业名称', enterprise_name)}工商信息：" + "；".join([f"{k}：{v}" for k, v in biz_fields.items()]) + f"。涉诉案件{total_writs}条。",
                "source": "元典开放平台 (open.chineselaw.com)",
                "source_name": "元典企业工商与风险数据",
                "source_type": "yuandian_business",
                "confidence": 0.85,
                "trust_level": "high",
                "requires_manual_review": total_writs > 0,
                "metadata": result,
            }, agent=category, domain=category))

        run_tool(
            tool_name="yuandian_business",
            tool_fn=_fetch_yuandian_company,
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=enterprise_name,
            query_summary="元典企业工商信息+涉诉风险",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_yuandian_company,
            result_key="yuandian_business",
        )

        # Business agent (Tavily-based public search + structured extraction)
        if "business_agent" in task.get("tool_hints", []):
            import asyncio
            from app.agents.sub_agents.business_agent import run_business_agent

            def _extract_business_agent(result):
                raw_outputs["business_agent"] = {
                    "success": result.get("success"),
                    "error": result.get("error"),
                    "evidence_count": len(result.get("evidence", [])),
                }
                for item in result.get("evidence", []):
                    # Skip evidence items with empty values
                    value = str(item.get("value", "")).strip()
                    if not value or value == "None":
                        continue
                    evidence.append(normalize_evidence(item, agent=category, domain=category))
                report = result.get("business_analysis_report") or {}
                if report:
                    biz_fields = {}
                    reg = report.get("registration_info") or {}
                    for field in ["法定代表人", "注册资本", "成立日期", "注册地址", "统一社会信用代码", "经营状态", "经营范围"]:
                        if reg.get(field):
                            biz_fields[field] = reg[field]
                    field_parts = [f"{k}：{v}" for k, v in biz_fields.items()]
                    evidence.append(normalize_evidence({
                        "label": "工商登记结构化信息",
                        "value": "；".join(field_parts[:6]) if field_parts else "工商登记信息待核验",
                        "claim": f"工商专项获取到以下登记信息：{'；'.join(field_parts[:6])}。" if field_parts else "工商专项未获取到结构化登记信息。",
                        "source": report.get("data_source") or "公开工商数据",
                        "source_name": "工商登记结构化信息",
                        "source_type": "commercial_business_data",
                        "confidence": 0.8,
                        "trust_level": "medium",
                        "requires_manual_review": True,
                        "metadata": {
                            "business_analysis_report": report,
                            "extracted_fields": {"business_fields": biz_fields},
                        },
                    }, agent=category, domain=category))

            run_tool(
                tool_name="business_agent",
                tool_fn=lambda: asyncio.run(run_business_agent(enterprise_name)),
                research_task_id=research_task_id,
            session_id=session_id,
                category=category,
                query=enterprise_name,
                query_summary="工商登记信息抽取与结构化分析",
                evidence=evidence,
                raw_outputs=raw_outputs,
                errors=errors,
                tool_traces=tool_traces,
                extract_evidence=_extract_business_agent,
                result_key="business_agent",
            )

    # ── Step 6: RAG knowledge retrieval ────────────────────────────
    if "rag" in task.get("tool_hints", []) or category in {"industry", "credit"}:
        domain = "industry" if category == "industry" else "credit" if category == "credit" else "all"
        rag_query = " ".join([enterprise_name, task.get("question", ""), " ".join(task.get("required_evidence", []))])

        def _fetch_rag():
            return retrieve_knowledge(query=rag_query, domain=domain, top_k=get_knowledge_retrieval_top_k("research"), company_name=enterprise_name)

        def _extract_rag(result):
            raw_outputs["rag"] = {"mode": result.get("mode"), "count": len(result.get("results", []))}
            evidence.extend(knowledge_hits_to_evidence(result.get("results", []), agent=category, domain=category))

        run_tool(
            tool_name="rag",
            tool_fn=_fetch_rag,
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=rag_query,
            query_summary="检索内部授信知识库和行业/财务审查规则",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_rag,
            result_key="rag",
        )

    # ── Step 7: Public search (bocha + optional searxng) ───────────
    if "bocha_search" in task.get("tool_hints", []) or category in {"business", "legal", "industry", "financial"}:
        query, freshness, include = _bocha_query(enterprise_name, task)

        def _fetch_bocha():
            return search_with_bocha(query=query, max_results=5, freshness=freshness, include=include, summary=True)

        def _extract_bocha(bocha_result):
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
                evidence.extend(pipeline_result.get("evidence", []))

        bocha_result = run_tool(
            tool_name="bocha",
            tool_fn=_fetch_bocha,
            research_task_id=research_task_id,
            session_id=session_id,
            category=category,
            query=query,
            query_summary="检索公开资料、公告、财报、司法和行业线索",
            evidence=evidence,
            raw_outputs=raw_outputs,
            errors=errors,
            tool_traces=tool_traces,
            extract_evidence=_extract_bocha,
        )

        # SearXNG supplement
        if settings.ENABLE_SEARXNG_SEARCH:
            def _fetch_searxng():
                return search_with_searxng(query=query, max_results=settings.SEARXNG_MAX_RESULTS)

            def _extract_searxng(searx_result):
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

            run_tool(
                tool_name="searxng",
                tool_fn=_fetch_searxng,
                research_task_id=research_task_id,
            session_id=session_id,
                category=category,
                query=query,
                query_summary="通过公开资料聚合检索补充候选证据",
                evidence=evidence,
                raw_outputs=raw_outputs,
                errors=errors,
                tool_traces=tool_traces,
                extract_evidence=_extract_searxng,
            )

    # ── Finalize: dedup, normalize and return ──────────────────────
    # Remove exact duplicates (same label + same value)
    seen_keys: set = set()
    deduped: List[Dict[str, Any]] = []
    for item in evidence:
        key = (item.get("label", ""), item.get("value", "")[:80])
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(item)
    evidence = deduped

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
