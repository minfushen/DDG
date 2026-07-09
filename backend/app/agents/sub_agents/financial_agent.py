# ========================================
# 财务分析Agent
# 使用 Rebecca 引擎进行10维度财务分析
# ========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json

from app.agents.tools.search_tool import search_financial_data
from app.agents.tools.listed_company_tool import fetch_listed_company_financial, resolve_listed_company
from app.agents.tools.akshare_financial_tool import fetch_akshare_financial_data
from app.agents.tools.financial_provider_reconciliation import reconcile_financial_providers, reconciliation_to_evidence, reconciliation_to_gaps
from app.agents.tools.bocha_search_tool import search_with_bocha
from app.agents.tools.cninfo_announcement_tool import search_cninfo_announcements
from app.engines.rebecca.analyzers import FinancialDDAnalyzer
from app.engines.rebecca.adapter import AnalyzerAdapter
from app.agents.sub_agents.financial_report_builder import build_financial_analysis_report
from app.api.cache_store import tool_cache_key, set_tool_cache


def _frame_to_records(df):
    if df is None:
        return []
    return df.fillna(0).to_dict(orient="records")


def _latest_year_columns(df) -> List[str]:
    if df is None:
        return []
    years = []
    for col in df.columns:
        value = str(col)
        if value.isdigit() and len(value) == 4:
            years.append(value)
    return sorted(years, reverse=True)


def _column_for_year(df, year: str):
    for col in df.columns:
        if str(col) == str(year):
            return col
    return None


def _label_column(df):
    for col in df.columns:
        if any(keyword in str(col) for keyword in ["项目", "科目", "指标", "名称"]):
            return col
    for col in df.columns:
        if not (str(col).isdigit() and len(str(col)) == 4):
            return col
    return df.columns[0]


def _value_by_item(df, item_keywords: List[str], year: str) -> Optional[float]:
    if df is None:
        return None

    year_col = _column_for_year(df, year)
    if year_col is None:
        return None

    label_col = _label_column(df)
    for _, row in df.iterrows():
        label = str(row.get(label_col, ""))
        if any(keyword in label for keyword in item_keywords):
            try:
                return float(row.get(year_col, 0) or 0)
            except (TypeError, ValueError):
                return None
    return None


def _run_rebecca_analysis(
    enterprise_name: str,
    rebecca_data: Dict[str, Any],
    include_structured_report: bool = False,
    data_source: str = "用户上传财报",
    public_context: Optional[List[Dict[str, Any]]] = None,
    stock_code: str = "",
    source_type: str = "financial_statement",
    cross_provider_reconciliation: Optional[Dict[str, Any]] = None,
    session_id: str | None = None,
    task_id: str | None = None,
    annual_report_notes: Optional[Dict[str, Any]] = None,
    financial_business_hints: Optional[List[str]] = None,
    industry_context: Optional[Dict[str, Any]] = None,
    business_segments: Optional[List[Dict[str, Any]]] = None,
    annual_business_review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    timeline = []
    evidence = []

    years = _latest_year_columns(rebecca_data.get("income_statement"))
    latest_year = years[0] if years else "最新年度"

    income = rebecca_data.get("income_statement")
    balance = rebecca_data.get("balance_sheet")
    cash_flow = rebecca_data.get("cash_flow")

    revenue = _value_by_item(income, ["营业收入", "主营业务收入", "收入"], latest_year)
    net_profit = _value_by_item(income, ["净利润"], latest_year)
    total_assets = _value_by_item(balance, ["资产总计", "资产合计", "总资产"], latest_year)
    total_liabilities = _value_by_item(balance, ["负债合计", "负债总计", "总负债"], latest_year)
    receivable = _value_by_item(balance, ["应收账款"], latest_year)
    operating_cash_flow = _value_by_item(cash_flow, ["经营活动产生的现金流量净额", "经营活动现金流"], latest_year)

    findings = []
    if revenue is not None:
        findings.append(f"{latest_year}年营收{revenue / 100000000:.1f}亿")
        evidence.append({"label": "营业收入", "value": f"{revenue / 100000000:.1f}亿", "source": data_source})
    if revenue and net_profit is not None:
        findings.append(f"净利润率{net_profit / revenue * 100:.1f}%")
        evidence.append({"label": "净利润率", "value": f"{net_profit / revenue * 100:.1f}%", "source": data_source})
    if total_assets and total_liabilities is not None:
        findings.append(f"资产负债率{total_liabilities / total_assets * 100:.0f}%")
        evidence.append({"label": "资产负债率", "value": f"{total_liabilities / total_assets * 100:.0f}%", "source": data_source})

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": f"读取{data_source}近三年财务报表",
        "detail": "资产负债表、利润表、现金流量表",
        "status": "completed",
        "type": "discovery",
        "findings": findings or ["已读取上传财报，部分关键科目缺失"],
    })

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "分析应收账款结构",
        "detail": "基于上传资产负债表识别应收账款余额",
        "status": "completed",
        "type": "analysis",
        "findings": [f"应收账款余额{receivable / 100000000:.1f}亿"] if receivable is not None else ["未识别到应收账款科目"],
        "conclusion": "应收账款需结合账龄和客户集中度进一步核实" if receivable is not None else None,
    })
    if receivable is not None:
        evidence.append({"label": "应收账款", "value": f"{receivable / 100000000:.1f}亿", "source": data_source})

    analyzer = FinancialDDAnalyzer(rebecca_data)
    analysis_result = analyzer.generate_full_analysis()
    risks = analyzer.identify_risks()
    analysis_json = AnalyzerAdapter.analysis_to_json(analysis_result)
    risks_json = AnalyzerAdapter.risks_to_dict(risks)

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "Rebecca引擎深度分析",
        "detail": "10维度财务分析、风险识别",
        "status": "completed",
        "type": "analysis",
        "findings": [
            f"毛利率：{analysis_json.get('profitability', {}).get('gross_profit_margin', {}).get('data', [['', '']])[0][1] if 'profitability' in analysis_json else 'N/A'}",
            f"流动比率：{analysis_json.get('solvency', {}).get('current_ratio', {}).get('data', [['', '']])[0][1] if 'solvency' in analysis_json else 'N/A'}",
        ],
    })

    for level, items in risks_json.items():
        for item in items:
            evidence.append({"label": f"风险-{level}", "value": item, "source": "Rebecca引擎分析"})

    timeline.append({
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": "分析现金流覆盖率",
        "detail": "经营活动现金流/负债合计",
        "status": "completed",
        "type": "analysis",
        "findings": [f"经营活动现金流{operating_cash_flow / 100000000:.1f}亿"] if operating_cash_flow is not None else ["未识别到经营活动现金流净额"],
        "conclusion": "需结合负债规模判断现金流覆盖情况",
    })
    if operating_cash_flow is not None:
        evidence.append({"label": "经营活动现金流", "value": f"{operating_cash_flow / 100000000:.1f}亿", "source": data_source})

    result = {"success": True, "timeline": timeline, "evidence": evidence}
    if include_structured_report:
        result["financial_analysis_report"] = build_financial_analysis_report(
            enterprise_name,
            rebecca_data,
            public_context=public_context,
            generated_from=data_source,
            stock_code=stock_code,
            source_type=source_type,
            cross_provider_reconciliation=cross_provider_reconciliation,
            session_id=session_id,
            task_id=task_id,
            annual_report_notes=annual_report_notes,
            financial_business_hints=financial_business_hints,
            industry_context=industry_context,
            business_segments=business_segments,
            annual_business_review=annual_business_review,
        )
        for item in result["financial_analysis_report"].get("codeact_evidence") or []:
            evidence.append(item)
    return result

def _build_industry_context_for_narrative(industry_report: dict) -> dict:
    """从行业报告中提取对财务叙事最有用的信息。"""

    def _truncate(text: str, max_len: int = 600) -> str:
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    diagnosis = industry_report.get("industry_diagnostic_summary") or industry_report.get("summary")
    if isinstance(diagnosis, list):
        diagnosis = "\n".join(str(x) for x in diagnosis)
    diagnosis_summary = _truncate(str(diagnosis) if diagnosis else "")

    data_anchors = industry_report.get("data_anchors") or {}
    anchor_parts = []
    for key in ["index_data", "market_size", "concentration", "policy", "chain", "research_reports"]:
        val = data_anchors.get(key)
        if val:
            if isinstance(val, dict):
                summary = val.get("summary") or val.get("description") or str(val)
            elif isinstance(val, list):
                summary = "; ".join(str(x) for x in val[:3])
            else:
                summary = str(val)
            if summary:
                anchor_parts.append(f"{key}: {summary}")
    data_anchors_summary = _truncate("\n".join(anchor_parts))

    industry_name = (
        (industry_report.get("industry") or {}).get("semantic_industry_name")
        or "industry_name"
    )

    triggered_rules = (
        (industry_report.get("industry_knowledge_context") or {}).get("triggered_rules")
        or []
    )[:3]

    return {
        "diagnosis_summary": diagnosis_summary,
        "data_anchors_summary": data_anchors_summary,
        "industry_name": industry_name,
        "triggered_rules": triggered_rules,
    }


def _fetch_financial_public_context(enterprise_name: str, listed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    security_name = listed_data.get("security_name") or enterprise_name
    stock_code = listed_data.get("stock_code") or ""
    query = f"{enterprise_name} {security_name} {stock_code} 年报 业绩预告 财务报表 营业收入 净利润 经营现金流 巨潮资讯 东方财富"
    result = search_with_bocha(
        query=query,
        max_results=6,
        freshness="noLimit",
        include="cninfo.com.cn|sse.com.cn|szse.cn|eastmoney.com|finance.eastmoney.com|data.eastmoney.com",
        summary=True,
    )
    if not result.get("success"):
        return []
    return result.get("results", [])[:6]


def _fetch_cninfo_annual_report_evidence(
    enterprise_name: str,
    listed_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Fetch and extract the latest annual report PDF from CNINFO.

    Returns the full CNINFO result including extracted evidence and ingestion status.
    """
    try:
        return search_cninfo_announcements(
            enterprise_name=enterprise_name,
            stock_code=listed_data.get("stock_code") or "",
            stock_exchange=listed_data.get("stock_exchange") or "",
            keyword="年度报告",
            max_results=6,
            extract_pdf_content=True,
            max_pdf_extract=1,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc), "extracted_evidence": [], "ingestion_results": [], "ingestion_gaps": [], "pdf_extraction_results": []}


def _value_by_item_from_df(df, item_keywords: List[str], year: str) -> Optional[float]:
    """Extract a numeric value from a financial DataFrame by item keywords."""
    if df is None or df.empty:
        return None
    label_col = None
    for col in df.columns:
        if any(keyword in str(col) for keyword in ["项目", "科目", "指标", "名称"]):
            label_col = col
            break
    if label_col is None:
        label_col = df.columns[0]
    year_col = None
    for col in df.columns:
        if str(col) == str(year):
            year_col = col
            break
    if year_col is None:
        return None
    for _, row in df.iterrows():
        label = str(row.get(label_col, ""))
        if any(keyword in label for keyword in item_keywords):
            try:
                return float(row.get(year_col, 0) or 0)
            except (TypeError, ValueError):
                return None
    return None


def _build_annual_report_notes(
    rebecca_data: Dict[str, Any],
    cninfo_result: Dict[str, Any],
    enterprise_name: str = "",
    key_metrics: Optional[Dict[str, Any]] = None,
    key_metric_series: Optional[Dict[str, Dict[str, str]]] = None,
    session_id: str | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    """Build structured annual-report note fields for deeper financial analysis.

    Fields:
      - business_segments: 主营业务分产品/分行业/分地区构成
      - rd_expenses: 研发费用序列
      - government_subsidies: 其他收益序列（主要为政府补助）
      - intangible_assets: 无形资产序列
      - development_expenses: 开发支出序列
      - interest_bearing_debt: 有息负债分项序列
      - business_review: 年报经营情况讨论与分析原文
      - attribution: LLM 深度归因（仅年报有正文时抽取）
    """
    income = rebecca_data.get("income_statement")
    balance = rebecca_data.get("balance_sheet")

    years = []
    if income is not None and not income.empty:
        years = sorted(
            [str(col) for col in income.columns if str(col).isdigit() and len(str(col)) == 4]
        )

    def series(keywords: List[str], df):
        return {year: _value_by_item_from_df(df, keywords, year) for year in years}

    rd_expenses = series(["研发费用"], income)
    government_subsidies = series(["其他收益"], income)
    intangible_assets = series(["无形资产"], balance)
    development_expenses = series(["开发支出"], balance)

    short_loan = series(["短期借款"], balance)
    long_loan = series(["长期借款"], balance)
    bonds_payable = series(["应付债券"], balance)
    lease_liability = series(["租赁负债"], balance)
    noncurrent_due_within_year = series(["一年内到期非流动负债"], balance)

    interest_bearing_debt = {}
    for year in years:
        components = [
            short_loan.get(year),
            long_loan.get(year),
            bonds_payable.get(year),
            lease_liability.get(year),
            noncurrent_due_within_year.get(year),
        ]
        present = [v for v in components if v is not None]
        interest_bearing_debt[year] = {
            "short_term_loan": short_loan.get(year),
            "long_term_loan": long_loan.get(year),
            "bonds_payable": bonds_payable.get(year),
            "lease_liability": lease_liability.get(year),
            "noncurrent_due_within_year": noncurrent_due_within_year.get(year),
            "total": sum(present) if present else None,
        }

    business_segments: List[Dict[str, Any]] = []
    business_review = ""
    for pdf_result in cninfo_result.get("pdf_extraction_results") or []:
        rows = pdf_result.get("main_business_rows") or []
        if rows:
            business_segments.extend(rows)
        sections = pdf_result.get("sections") or {}
        review_text = sections.get("business_review") or ""
        if review_text and len(review_text) > len(business_review):
            business_review = review_text

    # 仅当年报经营讨论正文达到阈值才触发 LLM 深度归因抽取（用户确认的策略）。
    attribution: Dict[str, Any] = {}
    if business_review and enterprise_name:
        try:
            from app.agents.sub_agents.annual_report_attribution_extractor import (
                extract_annual_report_attribution,
            )
            attribution = extract_annual_report_attribution(
                enterprise_name=enterprise_name,
                business_review=business_review,
                key_metrics=key_metrics,
                key_metric_series=key_metric_series,
                business_segments=business_segments,
                session_id=session_id,
                task_id=task_id,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("年报归因抽取失败：%s", exc)
            attribution = {"source": "error", "error": str(exc)}

    annual_report_notes = {
        "business_segments": business_segments,
        "business_review": business_review,
        "attribution": attribution,
        "rd_expenses": rd_expenses,
        "government_subsidies": government_subsidies,
        "intangible_assets": intangible_assets,
        "development_expenses": development_expenses,
        "interest_bearing_debt": interest_bearing_debt,
        "years": years,
    }

    # 把年报注释缓存，供行业 Agent 等后续环节复用，避免重复抽取归因。
    if enterprise_name:
        try:
            cache_key = tool_cache_key("annual_report_notes", {"enterprise_name": enterprise_name})
            set_tool_cache(
                cache_key=cache_key,
                tool_name="annual_report_notes",
                args={"enterprise_name": enterprise_name},
                result=annual_report_notes,
                ttl_seconds=7200,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("缓存 annual_report_notes 失败：%s", exc)

    return annual_report_notes


def _fetch_listed_financial_data(enterprise_name: str, listed_info: Dict[str, str]) -> Dict[str, Any]:
    """Fetch Eastmoney and AKShare, then cross-check overlapping fields."""
    akshare_result = fetch_akshare_financial_data(
        enterprise_name=enterprise_name,
        stock_code=listed_info["stock_code"],
        stock_exchange=listed_info["stock_exchange"],
    )
    result_json = fetch_listed_company_financial._run(
        enterprise_name=enterprise_name,
        stock_code=listed_info["stock_code"],
        stock_exchange=listed_info["stock_exchange"],
    )
    eastmoney_result = json.loads(result_json)
    eastmoney_result.setdefault("provider_fallbacks", [])
    if akshare_result.get("success"):
        if eastmoney_result.get("success"):
            reconciliation = reconcile_financial_providers(
                primary_provider=eastmoney_result.get("data_source") or "东方财富公开财报",
                primary_statements=eastmoney_result.get("financial_statements") or {},
                secondary_provider=akshare_result.get("data_source") or "AKShare",
                secondary_statements=akshare_result.get("financial_statements") or {},
            )
            eastmoney_result["cross_provider_reconciliation"] = reconciliation
            eastmoney_result["secondary_provider"] = akshare_result
            eastmoney_result["provider_fallbacks"].append({"provider": "akshare", "success": True, "used_for": "cross_validation"})
            return eastmoney_result
        akshare_result.setdefault("provider_fallbacks", []).append({
            "provider": "eastmoney",
            "success": False,
            "error": eastmoney_result.get("error"),
        })
        return akshare_result

    if eastmoney_result.get("success"):
        eastmoney_result["provider_fallbacks"].append({
            "provider": "akshare",
            "success": False,
            "error": akshare_result.get("error"),
        })
    return eastmoney_result


async def run_financial_agent(
    enterprise_name: str,
    session_id: str | None = None,
    task_id: str | None = None,
    industry_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """运行财务分析Agent

    Args:
        enterprise_name: 企业名称

    Returns:
        Dict: 分析结果，包含 timeline、evidence、success
    """
    try:
        listed_info = resolve_listed_company(enterprise_name)
        if listed_info:
            listed_data = _fetch_listed_financial_data(enterprise_name, listed_info)
            if not listed_data.get("success"):
                return {
                    "success": False,
                    "error": listed_data.get("error", "上市公司公开财报获取失败"),
                    "fallback_to_upload": True,
                    "timeline": [{
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "财务Agent",
                        "content": "公开财报获取失败",
                        "detail": listed_data.get("error", "请上传近三年三大表继续分析"),
                        "status": "completed",
                        "type": "risk",
                    }],
                    "evidence": [],
                }

            import pandas as pd

            financial_statements = listed_data.get("financial_statements", {})
            rebecca_data = {
                "income_statement": pd.DataFrame(financial_statements.get("income_statement", [])),
                "balance_sheet": pd.DataFrame(financial_statements.get("balance_sheet", [])),
                "cash_flow": pd.DataFrame(financial_statements.get("cash_flow", [])),
            }
            data_source = listed_data.get("data_source") or "东方财富公开财报"
            public_context = _fetch_financial_public_context(enterprise_name, listed_data)
            cninfo_result = _fetch_cninfo_annual_report_evidence(enterprise_name, listed_data)
            cninfo_pdf_evidence = cninfo_result.get("extracted_evidence") or []
            annual_report_notes = _build_annual_report_notes(
                rebecca_data,
                cninfo_result,
                enterprise_name=enterprise_name,
                session_id=session_id,
                task_id=task_id,
            )
            if cninfo_pdf_evidence:
                public_context.extend([
                    {
                        "title": item.get("label"),
                        "source": item.get("source_name") or "巨潮资讯网",
                        "source_url": item.get("source_url"),
                        "content": (item.get("metadata") or {}).get("excerpt") or item.get("value") or "",
                    }
                    for item in cninfo_pdf_evidence
                ])
            financial_business_hints = _build_financial_business_hints(rebecca_data, annual_report_notes)
            if industry_report is None:
                try:
                    from app.agents.sub_agents.industry_agent import run_industry_agent

                    industry_report = await run_industry_agent(
                        enterprise_name=enterprise_name,
                        public_info=None,
                        annual_report_notes=annual_report_notes,
                        session_id=session_id,
                        task_id=task_id,
                    )
                except Exception:
                    industry_report = None
            industry_context = _build_industry_context_for_narrative(industry_report) if industry_report else None
            result = _run_rebecca_analysis(
                enterprise_name,
                rebecca_data,
                include_structured_report=True,
                data_source=data_source,
                public_context=public_context,
                stock_code=listed_data.get("secu_code") or listed_data.get("stock_code") or "",
                source_type=listed_data.get("source_type") or "investment_research_tool",
                cross_provider_reconciliation=listed_data.get("cross_provider_reconciliation") or None,
                session_id=session_id,
                task_id=task_id,
                annual_report_notes=annual_report_notes,
                financial_business_hints=financial_business_hints,
                industry_context=industry_context,
                business_segments=annual_report_notes.get("business_segments") or None,
                annual_business_review=annual_report_notes.get("business_review") or None,
            )
            result["timeline"] = [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "识别上市公司并获取公开财报",
                "detail": f"{listed_data.get('security_name')} {listed_data.get('secu_code')}，来源：{data_source}",
                "status": "completed",
                "type": "discovery",
                "findings": [f"已获取年度：{', '.join(listed_data.get('years', []))}"],
            }, {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "标准化上市公司三大表",
                "detail": f"已映射{data_source}字段到利润表、资产负债表、现金流量表标准科目",
                "status": "completed",
                "type": "analysis",
            }] + result.get("timeline", [])
            if public_context:
                result.setdefault("timeline", []).insert(2, {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "财务Agent",
                    "content": "检索公开财报与公告线索",
                    "detail": "通过博查检索巨潮资讯、交易所和东方财富等公开来源",
                    "status": "completed",
                    "type": "discovery",
                    "findings": [f"命中公开线索 {len(public_context)} 条"],
                })
                for item in public_context:
                    result.setdefault("evidence", []).append({
                        "label": item.get("title") or "财报公告公开线索",
                        "value": item.get("content", "")[:80],
                        "source": item.get("source") or item.get("source_url") or "Bocha Web Search",
                        "source_name": item.get("source") or item.get("source_name") or "Bocha Web Search",
                        "source_url": item.get("source_url") or item.get("url"),
                        "source_type": "public_financial_report",
                        "confidence": item.get("confidence", 0.72),
                        "trust_level": item.get("trust_level", "medium"),
                        "requires_manual_review": True,
                        "metadata": item,
                    })
                for item in cninfo_pdf_evidence:
                    result.setdefault("evidence", []).append(item)

                # Surface PDF knowledge-base ingestion status to the user.
                ingestion_results = cninfo_result.get("ingestion_results") or []
                ingestion_gaps = cninfo_result.get("ingestion_gaps") or []
                if ingestion_results:
                    total_chunks = sum(r.get("document_count", 0) for r in ingestion_results)
                    failed = [r for r in ingestion_results if not r.get("success")]
                    if failed:
                        result.setdefault("timeline", []).insert(3, {
                            "id": str(uuid.uuid4()),
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "agent": "财务Agent",
                            "content": "巨潮年报 PDF 解析成功但入库失败",
                            "detail": "；".join(r.get("error") or "unknown" for r in failed),
                            "status": "completed",
                            "type": "risk",
                        })
                    else:
                        result.setdefault("timeline", []).insert(3, {
                            "id": str(uuid.uuid4()),
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "agent": "财务Agent",
                            "content": "巨潮年报 PDF 已写入企业知识库",
                            "detail": f"共生成 {total_chunks} 个 RAG chunk，可用于后续问答检索",
                            "status": "completed",
                            "type": "discovery",
                        })
                if ingestion_gaps:
                    result.setdefault("gaps", []).extend(ingestion_gaps)
            if result.get("financial_analysis_report"):
                result["financial_analysis_report"]["stock_code"] = listed_data.get("secu_code")
                result["financial_analysis_report"]["provider_fallbacks"] = listed_data.get("provider_fallbacks", [])
                reconciliation = listed_data.get("cross_provider_reconciliation") or {}
                if reconciliation:
                    result["financial_analysis_report"]["cross_provider_reconciliation"] = reconciliation
                    result["financial_analysis_report"]["requires_manual_review"] = not reconciliation.get("passed", True)
                    result["financial_analysis_report"]["manual_review_items"] = [
                        f"跨源财务数据差异：{item.get('year')}年{item.get('label')}"
                        for item in (reconciliation.get("mismatches") or [])[:8]
                    ]
                    reconciliation_evidence = reconciliation_to_evidence(enterprise_name, reconciliation)
                    result.setdefault("evidence", []).extend(reconciliation_evidence)
                    result["financial_analysis_report"]["provider_reconciliation_evidence_refs"] = [item.get("id") for item in reconciliation_evidence if item.get("id")]
                    result["financial_analysis_report"]["provider_reconciliation_gaps"] = reconciliation_to_gaps("financial_provider_reconciliation", enterprise_name, reconciliation)
                    result.setdefault("timeline", []).insert(2, {
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "财务Agent",
                        "content": "交叉校验公开财报结构化数据",
                        "detail": f"东方财富与AKShare已校验{reconciliation.get('checked_count', 0)}项，差异{reconciliation.get('mismatch_count', 0)}项",
                        "status": "completed",
                        "type": "validation",
                        "findings": [
                            f"差异项：{item.get('year')}年{item.get('label')}"
                            for item in (reconciliation.get("mismatches") or [])[:5]
                        ] or ["核心指标跨源校验未发现超阈值差异"],
                    })
                for item in result["financial_analysis_report"].get("codeact_evidence") or []:
                    item.setdefault("source_url", listed_data.get("source_url"))
                    item.setdefault("metadata", {})["stock_code"] = listed_data.get("secu_code")
                metrics = result["financial_analysis_report"].get("key_metrics") or {}
                metric_labels = {
                    "revenue": "营业收入",
                    "net_profit": "净利润",
                    "gross_margin": "毛利率",
                    "net_margin": "净利率",
                    "debt_ratio": "资产负债率",
                    "operating_cash_flow": "经营活动现金流量净额",
                    "receivable": "应收账款",
                }
                for key, label in metric_labels.items():
                    value = metrics.get(key)
                    if value and value != "数据不可用":
                        result.setdefault("evidence", []).append({
                            "label": label,
                            "value": value,
                            "source": data_source,
                            "source_name": f"{listed_data.get('security_name')} {listed_data.get('secu_code')} 近三年年报财务数据",
                            "source_type": "public_financial_report",
                            "confidence": 0.88,
                            "requires_manual_review": False,
                        })
            return result

        result_json = search_financial_data._run(enterprise_name=enterprise_name)
        financial_data = json.loads(result_json)
        import pandas as pd

        rebecca_data = {
            "income_statement": pd.DataFrame({
                "项目": ["营业收入", "营业成本", "毛利润", "净利润"],
                "2024": [
                    financial_data["财务报表"]["2024"]["营业收入"],
                    financial_data["财务报表"]["2024"]["营业成本"],
                    financial_data["财务报表"]["2024"]["毛利润"],
                    financial_data["财务报表"]["2024"]["净利润"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["营业收入"],
                    financial_data["财务报表"]["2023"]["营业成本"],
                    financial_data["财务报表"]["2023"]["毛利润"],
                    financial_data["财务报表"]["2023"]["净利润"],
                ],
            }),
            "balance_sheet": pd.DataFrame({
                "项目": ["总资产", "总负债", "所有者权益"],
                "2024": [
                    financial_data["财务报表"]["2024"]["总资产"],
                    financial_data["财务报表"]["2024"]["总负债"],
                    financial_data["财务报表"]["2024"]["所有者权益"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["总资产"],
                    financial_data["财务报表"]["2023"]["总负债"],
                    financial_data["财务报表"]["2023"]["所有者权益"],
                ],
            }),
            "cash_flow": pd.DataFrame({
                "项目": ["经营活动现金流", "投资活动现金流", "筹资活动现金流"],
                "2024": [
                    financial_data["财务报表"]["2024"]["经营活动现金流"],
                    financial_data["财务报表"]["2024"]["投资活动现金流"],
                    financial_data["财务报表"]["2024"]["筹资活动现金流"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["经营活动现金流"],
                    financial_data["财务报表"]["2023"]["投资活动现金流"],
                    financial_data["财务报表"]["2023"]["筹资活动现金流"],
                ],
            }),
        }

        result = _run_rebecca_analysis(
            enterprise_name,
            rebecca_data,
            include_structured_report=True,
            session_id=session_id,
            task_id=task_id,
        )
        for item in result["evidence"]:
            if item.get("source") == "用户上传财报":
                item["source"] = "模拟财务数据"
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "财务分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }


def _build_financial_business_hints(
    rebecca_data: Dict[str, Any],
    annual_report_notes: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """根据财务指标变化生成业务动因提示，供 narrative writer 做经营穿透。

    覆盖场景：收入利润背离、毛利率下滑、短期借款大增、存货高位、
    重资产投入、经营现金流下降、政府补助依赖、资本回报下降等。
    最多返回 6-8 条提示，使用安全取值避免异常。
    """
    income = rebecca_data.get("income_statement")
    balance = rebecca_data.get("balance_sheet")
    cash_flow = rebecca_data.get("cash_flow")

    years = _latest_year_columns(income)
    if len(years) < 2:
        return []
    latest_year = years[0]
    prev_year = years[1]

    def _val(df, keywords, year):
        return _value_by_item(df, keywords, year)

    hints: List[str] = []

    # 1. 收入利润背离
    revenue_latest = _val(income, ["营业收入", "主营业务收入", "收入"], latest_year)
    revenue_prev = _val(income, ["营业收入", "主营业务收入", "收入"], prev_year)
    net_profit_latest = _val(income, ["净利润"], latest_year)
    net_profit_prev = _val(income, ["净利润"], prev_year)
    if (
        revenue_latest is not None
        and revenue_prev is not None
        and net_profit_latest is not None
        and net_profit_prev is not None
        and revenue_prev != 0
        and net_profit_prev != 0
    ):
        revenue_growth = (revenue_latest - revenue_prev) / abs(revenue_prev)
        profit_growth = (net_profit_latest - net_profit_prev) / abs(net_profit_prev)
        if revenue_growth > 0.05 and profit_growth < -0.10:
            hints.append(
                f"收入利润背离：{latest_year}年营收同比+{revenue_growth*100:.1f}%，"
                f"净利润同比{profit_growth*100:.1f}%，需分析是否因降价促销、"
                f"成本上涨或非经常性损益导致增收不增利。"
            )
        elif revenue_growth < -0.05 and profit_growth > 0.10:
            hints.append(
                f"收入利润背离：{latest_year}年营收同比{revenue_growth*100:.1f}%，"
                f"净利润同比+{profit_growth*100:.1f}%，需分析是否因资产处置、"
                f"政府补助或费用压缩导致减收却增利。"
            )

    # 2. 毛利率下滑
    gross_profit_latest = _val(income, ["毛利润", "毛利"], latest_year)
    gross_profit_prev = _val(income, ["毛利润", "毛利"], prev_year)
    if (
        gross_profit_latest is not None
        and gross_profit_prev is not None
        and revenue_latest is not None
        and revenue_prev is not None
        and revenue_latest != 0
        and revenue_prev != 0
    ):
        gm_latest = gross_profit_latest / revenue_latest
        gm_prev = gross_profit_prev / revenue_prev
        if gm_latest < gm_prev - 0.02:
            hints.append(
                f"毛利率下滑：{latest_year}年毛利率{gm_latest*100:.1f}%，"
                f"较上年{gm_prev*100:.1f}%下降{(gm_prev-gm_latest)*100:.1f}个百分点，"
                f"需分析是否因原材料涨价、产品结构变化或竞争加剧。"
            )

    # 3. 短期借款大增
    short_loan_latest = _val(balance, ["短期借款"], latest_year)
    short_loan_prev = _val(balance, ["短期借款"], prev_year)
    if (
        short_loan_latest is not None
        and short_loan_prev is not None
        and short_loan_prev != 0
    ):
        loan_growth = (short_loan_latest - short_loan_prev) / abs(short_loan_prev)
        if loan_growth > 0.30:
            hints.append(
                f"短期借款大增：{latest_year}年短期借款同比+{loan_growth*100:.1f}%，"
                f"需分析是否因营运资金紧张、季节性备货或债务滚动压力。"
            )

    # 4. 存货高位
    inventory_latest = _val(balance, ["存货"], latest_year)
    inventory_prev = _val(balance, ["存货"], prev_year)
    if (
        inventory_latest is not None
        and inventory_prev is not None
        and revenue_latest is not None
        and revenue_prev is not None
        and revenue_prev != 0
    ):
        inv_growth = (inventory_latest - inventory_prev) / abs(inventory_prev)
        rev_growth = (revenue_latest - revenue_prev) / abs(revenue_prev) if revenue_prev != 0 else 0
        if inv_growth > 0.20 and inv_growth > rev_growth + 0.10:
            hints.append(
                f"存货高位：{latest_year}年存货同比+{inv_growth*100:.1f}%，"
                f"高于营收增速{rev_growth*100:.1f}%，需分析是否因滞销、"
                f"备货策略调整或供应链中断。"
            )

    # 5. 重资产投入（在建工程+固定资产）
    fixed_assets_latest = _val(balance, ["固定资产"], latest_year)
    fixed_assets_prev = _val(balance, ["固定资产"], prev_year)
    construction_latest = _val(balance, ["在建工程"], latest_year)
    construction_prev = _val(balance, ["在建工程"], prev_year)
    total_assets_latest = _val(balance, ["资产总计", "资产合计", "总资产"], latest_year)
    if (
        fixed_assets_latest is not None
        and fixed_assets_prev is not None
        and construction_latest is not None
        and construction_prev is not None
        and total_assets_latest is not None
        and total_assets_latest != 0
    ):
        heavy_latest = (fixed_assets_latest + construction_latest) / total_assets_latest
        heavy_prev = (fixed_assets_prev + construction_prev) / total_assets_latest
        if heavy_latest > 0.40 and heavy_latest > heavy_prev + 0.05:
            hints.append(
                f"重资产投入：{latest_year}年固定资产+在建工程占比"
                f"{heavy_latest*100:.1f}%，较上年提升{(heavy_latest-heavy_prev)*100:.1f}个百分点，"
                f"需分析产能扩张进度、折旧压力及未来回报预期。"
            )

    # 6. 经营现金流下降
    ocf_latest = _val(cash_flow, ["经营活动产生的现金流量净额", "经营活动现金流"], latest_year)
    ocf_prev = _val(cash_flow, ["经营活动产生的现金流量净额", "经营活动现金流"], prev_year)
    if (
        ocf_latest is not None
        and ocf_prev is not None
        and ocf_prev != 0
    ):
        ocf_growth = (ocf_latest - ocf_prev) / abs(ocf_prev)
        if ocf_growth < -0.20:
            hints.append(
                f"经营现金流下降：{latest_year}年经营活动现金流净额"
                f"同比{ocf_growth*100:.1f}%，需分析是否因应收账款增加、"
                f"存货占用或利润质量下降。"
            )

    # 7. 政府补助依赖
    gov_subsidy_latest = _val(income, ["其他收益"], latest_year)
    gov_subsidy_prev = _val(income, ["其他收益"], prev_year)
    if (
        gov_subsidy_latest is not None
        and net_profit_latest is not None
        and net_profit_latest != 0
    ):
        subsidy_ratio = gov_subsidy_latest / abs(net_profit_latest)
        if subsidy_ratio > 0.30:
            hints.append(
                f"政府补助依赖：{latest_year}年其他收益（主要为政府补助）"
                f"占净利润{subsidy_ratio*100:.1f}%，需分析政策可持续性"
                f"及扣除补助后的真实盈利能力。"
            )

    # 8. 资本回报下降（ROE）
    total_equity_latest = _val(balance, ["所有者权益合计", "股东权益合计", "所有者权益"], latest_year)
    total_equity_prev = _val(balance, ["所有者权益合计", "股东权益合计", "所有者权益"], prev_year)
    if (
        net_profit_latest is not None
        and net_profit_prev is not None
        and total_equity_latest is not None
        and total_equity_prev is not None
        and total_equity_latest != 0
        and total_equity_prev != 0
    ):
        roe_latest = net_profit_latest / total_equity_latest
        roe_prev = net_profit_prev / total_equity_prev
        if roe_latest < roe_prev - 0.03:
            hints.append(
                f"资本回报下降：{latest_year}年ROE约{roe_latest*100:.1f}%，"
                f"较上年{roe_prev*100:.1f}%下降{(roe_prev-roe_latest)*100:.1f}个百分点，"
                f"需分析是否因资产周转放缓、杠杆降低或利润率收缩。"
            )

    # 限制最多 8 条
    return hints[:8]
