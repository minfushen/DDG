# ========================================
# 财务分析Agent
# 使用 Rebecca 引擎进行10维度财务分析
# ========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
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
from app.engines.rebecca.parsers.financial_pdf_pipeline import pipeline_statements_to_standard_dataframes
from app.agents.sub_agents.financial_report_builder import build_financial_analysis_report
from app.agents.sub_agents.five_see_analyzer import build_five_see_analysis
from app.agents.sub_agents.credit_approval_opinion import build_credit_approval_opinion
from app.api.cache_store import tool_cache_key, set_tool_cache
from app.agents.tools.bank_flow_tool import BankFlowData
from app.agents.tools.flow_reconciliation import reconcile_flow_with_annual_report
from app.config import settings


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
    bank_flow_data: Optional[BankFlowData] = None,
    industry_name: Optional[str] = None,
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

    analyzer = FinancialDDAnalyzer(rebecca_data, industry_name=industry_name)
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

    # 银行流水 × 年报三大表 多源交叉核验（差异化营收/资金穿透证据）。
    flow_reconciliation = None
    if bank_flow_data is not None and not bank_flow_data.is_empty():
        equity = _value_by_item(balance, ["所有者权益", "股东权益", "净资产"], latest_year)
        flow_reconciliation = reconcile_flow_with_annual_report(
            bank_flow_data,
            rebecca_data,
            annual_report_notes=annual_report_notes,
            net_assets=equity,
        )
        result["flow_reconciliation"] = flow_reconciliation
        if flow_reconciliation.get("success"):
            result.setdefault("timeline", []).append({
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "银行流水×年报交叉核验",
                "detail": flow_reconciliation.get("summary", ""),
                "status": "completed" if flow_reconciliation.get("status") != "mismatch" else "risk",
                "type": "validation",
                "findings": [
                    f"{item.get('label')}：{item.get('status')}"
                    for item in flow_reconciliation.get("check_items", [])[:4]
                ] or ["已完成流水交叉核验"],
            })
            for flag in flow_reconciliation.get("red_flags", [])[:5]:
                evidence.append({
                    "label": f"流水风险-{flag.get('type')}",
                    "value": flag.get("detail", ""),
                    "source": "银行流水交叉核验",
                })

    # 授信五看 + 审批意见（信审/风控经理决策支撑）。
    equity = _value_by_item(balance, ["所有者权益", "股东权益", "净资产"], latest_year)
    financial_metrics = {
        "revenue": revenue,
        "net_profit": net_profit,
        "net_margin": (net_profit / revenue) if (revenue and net_profit is not None) else None,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "debt_ratio": (total_liabilities / total_assets) if (total_liabilities is not None and total_assets) else None,
        "operating_cash_flow": operating_cash_flow,
        "receivable": receivable,
        "roe": (net_profit / equity) if (equity and net_profit is not None) else None,
        "equity_multiplier": (total_assets / equity) if (equity and total_assets) else None,
    }
    flow_net = None
    if flow_reconciliation and flow_reconciliation.get("success"):
        for c in flow_reconciliation.get("check_items", []):
            if c.get("key") == "ocf_vs_flow_net":
                flow_net = c.get("flow_value")
    repayment = {
        "operating_cash_flow": operating_cash_flow,
        "revenue": revenue,
        "flow_net": flow_net,
        "ocf_cover": None,
    }
    notes = annual_report_notes or {}
    five_see = build_five_see_analysis(
        enterprise_name,
        industry_context=industry_context,
        business_segments=business_segments,
        business_review=notes.get("business_review") or annual_business_review,
        financial_metrics=financial_metrics,
        repayment=repayment,
        guarantee=None,
        risk_section=notes.get("risk_section"),
    )
    approval_opinion = build_credit_approval_opinion(
        enterprise_name,
        financial_metrics=financial_metrics,
        flow_reconciliation=flow_reconciliation,
        five_see=five_see,
        industry_context=industry_context,
    )
    result["five_see_analysis"] = five_see
    result["approval_opinion"] = approval_opinion

    return result

def _extract_industry_name(industry_report: Optional[dict]) -> Optional[str]:
    """从行业报告中健壮地提取行业名称（用于 P2.1 同业对标）。

    兼容两种结构：
      - run_industry_agent 返回：{..., "industry_analysis_report": {"industry": {...}}}
      - 直接传入的 industry_analysis_report：{"industry": {...}}
    """
    if not industry_report:
        return None
    report = industry_report.get("industry_analysis_report") or industry_report
    name = (
        (report.get("industry") or {}).get("semantic_industry_name")
        or (report.get("industry") or {}).get("industry_name")
        or industry_report.get("industry_name")
        or (report.get("industry") or {}).get("name")
    )
    return name or None


def _build_industry_context_for_narrative(industry_report: dict) -> dict:
    """从行业报告中提取对财务叙事最有用的信息。"""

    def _truncate(text: str, max_len: int = 600) -> str:
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    # 兼容 run_industry_agent 返回（包了 industry_analysis_report）与直接 report 两种结构
    report = (industry_report or {}).get("industry_analysis_report") or (industry_report or {})

    diagnosis = report.get("industry_diagnostics") or report.get("industry_diagnostic_summary") or report.get("summary")
    if isinstance(diagnosis, list):
        diagnosis = "\n".join(str(x) for x in diagnosis)
    diagnosis_summary = _truncate(str(diagnosis) if diagnosis else "")

    data_anchors = report.get("data_anchors") or {}
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

    industry_name = _extract_industry_name(industry_report) or ""

    triggered_rules = (
        (report.get("industry_knowledge_context") or {}).get("triggered_rules")
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
    """Fetch and extract the latest 3 annual report PDFs from CNINFO.

    Returns the full CNINFO result including extracted evidence and ingestion status.
    """
    try:
        return search_cninfo_announcements(
            enterprise_name=enterprise_name,
            stock_code=listed_data.get("stock_code") or "",
            stock_exchange=listed_data.get("stock_exchange") or "",
            keyword="年度报告",
            max_results=10,
            extract_pdf_content=True,
            max_pdf_extract=3,
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
    stock_code: str = "",
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
    risk_section = ""
    for pdf_result in cninfo_result.get("pdf_extraction_results") or []:
        rows = pdf_result.get("main_business_rows") or []
        if rows:
            business_segments.extend(rows)
        sections = pdf_result.get("sections") or {}
        review_text = sections.get("business_review") or ""
        if review_text and len(review_text) > len(business_review):
            business_review = review_text
        # 巨潮年报 PDF「公司面临的风险和应对措施」章节——forward_risks 的权威来源。
        risk_text = sections.get("major_risk_warnings") or ""
        if risk_text and len(risk_text) > len(risk_section):
            risk_section = risk_text

    # 无年报 PDF 解析时（FINANCIAL_USE_PDF_PIPELINE=False 或 PDF 未产出），
    # 回退到东方财富 F10 结构化接口补齐主营构成与经营讨论原文，
    # 以保留财务深度叙述（主营分部 / 经营讨论 / LLM 归因），不依赖 PDF 解析。
    if not (business_segments or business_review):
        try:
            from app.agents.tools.eastmoney_structured_tool import eastmoney_fetch_business_narrative

            narrative = eastmoney_fetch_business_narrative(stock_code or "")
            if not business_segments and narrative.get("business_segments"):
                business_segments = narrative["business_segments"]
            if not business_review and narrative.get("business_review"):
                business_review = narrative["business_review"]
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("东方财富 F10 主营/经营分析获取失败：%s", exc)

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
                risk_section=risk_section or None,
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
        "risk_section": risk_section,
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


def _pipeline_result_to_rebecca_data(pipeline_result: Any) -> Dict[str, Any]:
    """把 PDF pipeline 结果转成 Rebecca 可用的 rebecca_data 字典。"""
    if pipeline_result is None:
        return {}
    # 兼容 dataclass 和 dict
    statements = pipeline_result.statements if hasattr(pipeline_result, "statements") else pipeline_result.get("statements")
    if statements is None:
        return {}
    return pipeline_statements_to_standard_dataframes(statements)


def _pipeline_statements_to_records(pipeline_result: Any) -> Dict[str, List[Dict[str, Any]]]:
    """把 PDF pipeline 结果转成与 reconcile_financial_providers 兼容的 records。"""
    rebecca_data = _pipeline_result_to_rebecca_data(pipeline_result)
    return {
        "income_statement": _frame_to_records(rebecca_data.get("income_statement")),
        "balance_sheet": _frame_to_records(rebecca_data.get("balance_sheet")),
        "cash_flow": _frame_to_records(rebecca_data.get("cash_flow")),
    }


def _extract_pipeline_statements(pdf_extraction_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从多个 PDF 提取结果中收集所有可用的 pipeline statements。"""
    statements_list: List[Dict[str, Any]] = []
    for result in pdf_extraction_results:
        pipeline_result = result.get("pipeline_result")
        if pipeline_result is None:
            continue
        success = getattr(pipeline_result, "success", False) if hasattr(pipeline_result, "success") else pipeline_result.get("success", False)
        if not success:
            continue
        report_year = getattr(pipeline_result, "report_year", None) if hasattr(pipeline_result, "report_year") else pipeline_result.get("report_year")
        pdf_url = getattr(pipeline_result, "pdf_url", "") if hasattr(pipeline_result, "pdf_url") else pipeline_result.get("pdf_url", "")
        rebecca_data = _pipeline_result_to_rebecca_data(pipeline_result)
        if any(df is not None and not df.empty for df in rebecca_data.values()):
            statements_list.append({
                "report_year": report_year,
                "pdf_url": pdf_url,
                "rebecca_data": rebecca_data,
            })
    # 按报告年份倒序，最新年报在前
    statements_list.sort(key=lambda x: x["report_year"] or 0, reverse=True)
    return statements_list


def _supplement_years_from_older_pdfs(
    base_rebecca_data: Dict[str, Any],
    pdf_extraction_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """用 older 年报 PDF 补充 base_rebecca_data 中缺失的历史年份。

    策略：以 base（通常是最新年报 PDF 或结构化接口）为主，当某张表缺少
    20xx 年份时，从 older PDF 的对应表中把该年份补进来。
    """
    import pandas as pd

    statements_list = _extract_pipeline_statements(pdf_extraction_results)
    if len(statements_list) <= 1:
        return base_rebecca_data

    result = dict(base_rebecca_data)
    table_names = ["income_statement", "balance_sheet", "cash_flow"]

    for table_name in table_names:
        base_df = result.get(table_name)
        if base_df is None or base_df.empty:
            # base 完全缺失该表时，尝试用最新 PDF 的结果替代
            for stmt in statements_list:
                candidate = stmt["rebecca_data"].get(table_name)
                if candidate is not None and not candidate.empty:
                    result[table_name] = candidate.copy()
                    base_df = result[table_name]
                    break
            if base_df is None or base_df.empty:
                continue

        label_col = _label_column(base_df)
        base_years = {str(c) for c in base_df.columns if str(c).isdigit() and len(str(c)) == 4}

        for stmt in statements_list[1:]:
            older_df = stmt["rebecca_data"].get(table_name)
            if older_df is None or older_df.empty:
                continue
            older_label_col = _label_column(older_df)
            older_years = [str(c) for c in older_df.columns if str(c).isdigit() and len(str(c)) == 4 and str(c) not in base_years]
            if not older_years:
                continue

            # 按 label 列合并，只取 base 中没有的年份
            merged = base_df.merge(
                older_df[[older_label_col] + older_years].rename(columns={older_label_col: label_col}),
                on=label_col,
                how="outer",
                suffixes=("", "_older"),
            )
            # 如果因 label 不同导致重复列，清理 _older 后缀列
            for col in list(merged.columns):
                if col.endswith("_older"):
                    original = col[:-6]
                    if original in merged.columns:
                        merged[original] = merged[original].combine_first(merged[col])
                    merged.drop(columns=[col], inplace=True)
            result[table_name] = merged
            base_df = merged
            base_years.update(older_years)

    return result


def _select_rebecca_data(
    listed_data: Optional[Dict[str, Any]],
    pipeline_result: Any,
) -> tuple[Dict[str, Any], str, List[Dict[str, Any]]]:
    """选择最终的 rebecca_data、data_source 和 provider_fallbacks。

    策略（PRD 1.8：PDF 年报解析优先，结构化接口降为交叉校验/补缺）：
      1. 当 PDF pipeline 成功且 auto_judgment_rate >= 0.85、主表覆盖完整时，
         优先使用 PDF 解析结果；
      2. 结构化接口用于：① 交叉校验差异；② 补齐 PDF 缺失的表或字段；
      3. 当 PDF 不可用或不满足质量阈值时，回退到结构化接口；
      4. 两者皆无时返回空字典。
    """
    import pandas as pd

    provider_fallbacks: List[Dict[str, Any]] = []

    structured_statements = {}
    structured_source = ""
    if listed_data and listed_data.get("success"):
        structured_statements = listed_data.get("financial_statements", {})
        structured_source = listed_data.get("data_source") or "东方财富公开财报"

    pipeline_data = _pipeline_result_to_rebecca_data(pipeline_result)
    pipeline_success = pipeline_result is not None and (
        getattr(pipeline_result, "success", False) if hasattr(pipeline_result, "success")
        else pipeline_result.get("success", False)
    )

    prefer_pdf = _should_prefer_pdf_pipeline(pipeline_result)

    # 任一可用即继续
    if not structured_statements and not pipeline_success:
        return {}, "", provider_fallbacks

    selected: Dict[str, Any] = {}
    table_names = ["income_statement", "balance_sheet", "cash_flow"]

    if prefer_pdf:
        # PDF 优先：以 pipeline 为主，结构化接口补缺
        for table_name in table_names:
            df = pipeline_data.get(table_name)
            if df is not None and not df.empty:
                selected[table_name] = df
            else:
                records = structured_statements.get(table_name, [])
                if records:
                    selected[table_name] = pd.DataFrame(records)
                    provider_fallbacks.append({
                        "provider": structured_source or "structured_public",
                        "success": True,
                        "used_for": f"fallback_{table_name}",
                        "reason": "pdf_pipeline_missing_table",
                    })
        data_source = "巨潮资讯网年报PDF解析"
    else:
        # 结构化接口优先（PDF 质量不足时），pipeline 用于补缺
        if structured_statements:
            for table_name in table_names:
                records = structured_statements.get(table_name, [])
                if records:
                    selected[table_name] = pd.DataFrame(records)
            if not structured_source:
                structured_source = "结构化公开财报"

        if pipeline_success:
            for table_name in table_names:
                if selected.get(table_name) is None or selected[table_name].empty:
                    df = pipeline_data.get(table_name)
                    if df is not None and not df.empty:
                        selected[table_name] = df
                        provider_fallbacks.append({
                            "provider": "cninfo_pdf_pipeline",
                            "success": True,
                            "used_for": f"fallback_{table_name}",
                            "reason": "structured_data_missing_table",
                        })

        data_source = structured_source or "巨潮资讯网年报PDF解析"

    # 补齐缺失的表为 None
    for table_name in table_names:
        if table_name not in selected:
            selected[table_name] = None

    return selected, data_source, provider_fallbacks


def _should_prefer_pdf_pipeline(pipeline_result: Any) -> bool:
    """判断 PDF pipeline 结果是否足够优质，可优先于结构化接口。"""
    if pipeline_result is None:
        return False
    success = getattr(pipeline_result, "success", False) if hasattr(pipeline_result, "success") else pipeline_result.get("success", False)
    if not success:
        return False
    auto_judgment_rate = getattr(pipeline_result, "auto_judgment_rate", 0.0) if hasattr(pipeline_result, "auto_judgment_rate") else pipeline_result.get("auto_judgment_rate", 0.0)
    main_table_coverage = getattr(pipeline_result, "main_table_coverage", "0/3") if hasattr(pipeline_result, "main_table_coverage") else pipeline_result.get("main_table_coverage", "0/3")
    try:
        covered, total = main_table_coverage.split("/")
        coverage_ok = int(covered) >= 3 and int(total) >= 3
    except Exception:
        coverage_ok = False
    return auto_judgment_rate >= 0.85 and coverage_ok


def _resolve_industry_name_for_upload(enterprise_name: str) -> Optional[str]:
    """上传路径兜底：若企业是上市公司，则识别其行业名用于同业对标。

    仅对已识别为上市公司的上传企业触发，避免对未上市企业做无谓的归类调用；
    任何一步失败都安全返回 None，由 analyzers 降级为"行业基准暂不可得"。
    """
    try:
        listed_info = resolve_listed_company(enterprise_name)
        if not listed_info:
            return None
        from app.agents.tools.classify_industry_tool import classify_industry_tool

        classification = json.loads(classify_industry_tool._run(
            enterprise_name=enterprise_name,
            business_scope=listed_info.get("business_scope") or "",
            extra_context="",
        ))
        if classification.get("success"):
            return classification.get("semantic_industry_name") or classification.get("industry_name")
    except Exception:
        return None
    return None


async def run_financial_agent_with_uploaded_data(
    enterprise_name: str,
    parsed_financial_data: Dict[str, Any],
    session_id: str | None = None,
    task_id: str | None = None,
    bank_flow_data: Optional[BankFlowData] = None,
    industry_name: Optional[str] = None,
) -> Dict[str, Any]:
    """基于用户上传的三大表运行财务分析 Agent。

    Args:
        enterprise_name: 企业名称
        parsed_financial_data: {"income_statement": [...], "balance_sheet": [...], "cash_flow": [...]}
        industry_name: 行业名称（可选，用于 P2.1 同业中位数对标；省略时仅对上市公司自动识别）
    """
    try:
        import pandas as pd

        # P2.1：上传路径尽量拿到行业名用于同业对标（上市公司自动识别，未上市则降级）
        if industry_name is None:
            industry_name = await asyncio.to_thread(_resolve_industry_name_for_upload, enterprise_name)

        statements = parsed_financial_data or {}
        rebecca_data = {
            "income_statement": pd.DataFrame(statements.get("income_statement") or []),
            "balance_sheet": pd.DataFrame(statements.get("balance_sheet") or []),
            "cash_flow": pd.DataFrame(statements.get("cash_flow") or []),
        }
        if all(df.empty for df in rebecca_data.values()):
            return {
                "success": False,
                "error": "上传财报数据为空，请提供利润表、资产负债表、现金流量表",
                "fallback_to_upload": True,
                "timeline": [{
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "财务Agent",
                    "content": "上传财报数据为空",
                    "detail": "未解析到利润表、资产负债表、现金流量表",
                    "status": "completed",
                    "type": "risk",
                }],
                "evidence": [],
            }

        return _run_rebecca_analysis(
            enterprise_name,
            rebecca_data,
            include_structured_report=True,
            data_source="用户上传财报",
            source_type="financial_statement",
            session_id=session_id,
            task_id=task_id,
            bank_flow_data=bank_flow_data,
            industry_name=industry_name,
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(exc),
            "fallback_to_upload": True,
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "上传财报分析失败",
                "detail": str(exc),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }


async def run_financial_agent(
    enterprise_name: str,
    session_id: str | None = None,
    task_id: str | None = None,
    industry_report: Optional[Dict[str, Any]] = None,
    bank_flow_data: Optional[BankFlowData] = None,
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
            # 以东方财富/AKShare 结构化 API 为主数据源。
            # 年报 PDF 三大表解析属数据治理团队职责，默认不在本 Agent 内进行；
            # 私有化交付时由客户直接提供三大表结构化数据。
            # 如需启用年报 PDF 交叉校验，可将 settings.FINANCIAL_USE_PDF_PIPELINE 置为 True。
            listed_data_task = asyncio.to_thread(_fetch_listed_financial_data, enterprise_name, listed_info)
            if settings.FINANCIAL_USE_PDF_PIPELINE:
                cninfo_task = asyncio.to_thread(_fetch_cninfo_annual_report_evidence, enterprise_name, listed_info)
                listed_data, cninfo_result = await asyncio.gather(listed_data_task, cninfo_task)
            else:
                listed_data = await listed_data_task
                cninfo_result = {}

            structured_success = bool(listed_data and listed_data.get("success"))
            cninfo_success = bool(cninfo_result and cninfo_result.get("success"))

            # 提取四阶段 PDF 管道结果（可能包含近 3 年年报）
            pipeline_result = None
            pdf_extraction_results = cninfo_result.get("pdf_extraction_results") or []
            if pdf_extraction_results:
                pipeline_result = pdf_extraction_results[0].get("pipeline_result")

            # 选择最终 rebecca_data、data_source 与 provider_fallbacks
            rebecca_data, data_source, pdf_provider_fallbacks = _select_rebecca_data(listed_data, pipeline_result)

            # 用 older 年报 PDF 补充缺失年份，形成近 3 年完整序列
            rebecca_data = _supplement_years_from_older_pdfs(rebecca_data, pdf_extraction_results)

            if not rebecca_data or all(df is None or df.empty for df in rebecca_data.values()):
                error_msg = (listed_data or {}).get("error") or "上市公司公开财报与年报PDF均未能解析出三大表"
                return {
                    "success": False,
                    "error": error_msg,
                    "fallback_to_upload": True,
                    "timeline": [{
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "财务Agent",
                        "content": "公开财报获取失败",
                        "detail": error_msg,
                        "status": "completed",
                        "type": "risk",
                    }],
                    "evidence": [],
                }

            import pandas as pd

            public_context = _fetch_financial_public_context(
                enterprise_name,
                listed_data if structured_success else listed_info,
            )
            cninfo_pdf_evidence = cninfo_result.get("extracted_evidence") or []
            annual_report_notes = _build_annual_report_notes(
                rebecca_data,
                cninfo_result,
                enterprise_name=enterprise_name,
                session_id=session_id,
                task_id=task_id,
                stock_code=(
                    listed_info.get("stock_code")
                    or listed_data.get("stock_code")
                    or listed_data.get("secu_code")
                    or ""
                ),
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

            # PDF 与结构化公开财报交叉校验
            pdf_structured_reconciliation = None
            if structured_success and pipeline_result and (
                getattr(pipeline_result, "success", False)
                if hasattr(pipeline_result, "success")
                else pipeline_result.get("success", False)
            ):
                pdf_records = _pipeline_statements_to_records(pipeline_result)
                financial_statements = listed_data.get("financial_statements", {})
                if any(financial_statements.get(t) for t in ["income_statement", "balance_sheet", "cash_flow"]):
                    prefer_pdf = _should_prefer_pdf_pipeline(pipeline_result)
                    if prefer_pdf:
                        pdf_structured_reconciliation = reconcile_financial_providers(
                            primary_provider="巨潮资讯网年报PDF解析",
                            primary_statements=pdf_records,
                            secondary_provider=listed_data.get("data_source") or "结构化公开财报",
                            secondary_statements=financial_statements,
                        )
                    else:
                        pdf_structured_reconciliation = reconcile_financial_providers(
                            primary_provider=listed_data.get("data_source") or "结构化公开财报",
                            primary_statements=financial_statements,
                            secondary_provider="巨潮资讯网年报PDF解析",
                            secondary_statements=pdf_records,
                        )

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
            # P2.1：从行业报告提取行业名，用于后续同业中位数对标
            industry_name = _extract_industry_name(industry_report) if industry_report else None

            all_provider_fallbacks = list(listed_data.get("provider_fallbacks", [])) if structured_success else []
            all_provider_fallbacks.extend(pdf_provider_fallbacks)

            # 根据主数据源选择 source_type
            if _should_prefer_pdf_pipeline(pipeline_result):
                source_type = "annual_report_pdf"
            elif listed_data and listed_data.get("source_type"):
                source_type = listed_data.get("source_type")
            else:
                source_type = "investment_research_tool"

            # 数据源边界/降级提示
            pipeline_quality_note = ""
            if pipeline_result and (
                getattr(pipeline_result, "success", False)
                if hasattr(pipeline_result, "success")
                else pipeline_result.get("success", False)
            ):
                ajr = getattr(pipeline_result, "auto_judgment_rate", 0.0) if hasattr(pipeline_result, "auto_judgment_rate") else pipeline_result.get("auto_judgment_rate", 0.0)
                coverage = getattr(pipeline_result, "main_table_coverage", "0/3") if hasattr(pipeline_result, "main_table_coverage") else pipeline_result.get("main_table_coverage", "0/3")
                pipeline_quality_note = f"PDF解析自动判定率 {ajr:.1%}，主表覆盖 {coverage}"

            if _should_prefer_pdf_pipeline(pipeline_result):
                if pdf_provider_fallbacks:
                    fallback_tables = ", ".join(f.get("used_for", "").replace("fallback_", "") for f in pdf_provider_fallbacks)
                    data_source_detail = f"{pipeline_quality_note}；结构化接口补充：{fallback_tables}"
                else:
                    data_source_detail = f"{pipeline_quality_note}；主数据来自巨潮年报PDF"
            elif pipeline_result and (
                getattr(pipeline_result, "success", False)
                if hasattr(pipeline_result, "success")
                else pipeline_result.get("success", False)
            ):
                data_source_detail = f"PDF解析质量不足（{pipeline_quality_note}），已降级为 {data_source}"
            else:
                data_source_detail = f"年报PDF解析不可用，使用 {data_source}"

            result = _run_rebecca_analysis(
                enterprise_name,
                rebecca_data,
                include_structured_report=True,
                data_source=data_source,
                public_context=public_context,
                stock_code=listed_data.get("secu_code") or listed_data.get("stock_code") or listed_info.get("secu_code") or listed_info.get("stock_code") or "",
                source_type=source_type,
                cross_provider_reconciliation=pdf_structured_reconciliation or ((listed_data.get("cross_provider_reconciliation") if structured_success else None) or None),
                session_id=session_id,
                task_id=task_id,
                annual_report_notes=annual_report_notes,
                financial_business_hints=financial_business_hints,
                industry_context=industry_context,
                industry_name=industry_name,
                business_segments=annual_report_notes.get("business_segments") or None,
                annual_business_review=annual_report_notes.get("business_review") or None,
                bank_flow_data=bank_flow_data,
                five_see_analysis=five_see,
                approval_opinion=approval_opinion,
            )

            pipeline_coverage = (
                getattr(pipeline_result, "main_table_coverage", "0/3")
                if hasattr(pipeline_result, "main_table_coverage")
                else (pipeline_result or {}).get("main_table_coverage", "0/3")
            )
            pipeline_auto_rate = (
                getattr(pipeline_result, "auto_judgment_rate", 0.0)
                if hasattr(pipeline_result, "auto_judgment_rate")
                else (pipeline_result or {}).get("auto_judgment_rate", 0.0)
            )
            result["timeline"] = [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "识别上市公司并获取公开财报",
                "detail": f"{(listed_data if structured_success else listed_info).get('security_name')} {(listed_data if structured_success else listed_info).get('secu_code')}；{data_source_detail}",
                "status": "completed",
                "type": "discovery",
                "findings": [f"已获取年度：{', '.join(listed_data.get('years', []))}"] if structured_success else ["使用巨潮资讯网年报PDF解析数据"],
            }, {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "年报PDF四阶段解析完成",
                "detail": f"共解析 {len(pdf_extraction_results)} 份年报PDF；覆盖度：{pipeline_coverage}，自动判定率：{pipeline_auto_rate:.2f}",
                "status": "completed" if pipeline_result is not None else "skipped",
                "type": "discovery",
            }, {
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "标准化上市公司三大表",
                "detail": f"已映射{data_source}字段到利润表、资产负债表、现金流量表标准科目",
                "status": "completed",
                "type": "analysis",
            }] + result.get("timeline", [])

            if pdf_structured_reconciliation:
                result.setdefault("timeline", []).insert(3, {
                    "id": str(uuid.uuid4()),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "agent": "财务Agent",
                    "content": "年报PDF与公开财报交叉校验",
                    "detail": f"已校验{pdf_structured_reconciliation.get('checked_count', 0)}项，差异{pdf_structured_reconciliation.get('mismatch_count', 0)}项",
                    "status": "completed",
                    "type": "validation",
                    "findings": [
                        f"差异项：{item.get('year')}年{item.get('label')}"
                        for item in (pdf_structured_reconciliation.get("mismatches") or [])[:5]
                    ] or ["核心指标PDF交叉校验未发现超阈值差异"],
                })
                reconciliation_evidence = reconciliation_to_evidence(enterprise_name, pdf_structured_reconciliation)
                result.setdefault("evidence", []).extend(reconciliation_evidence)
                result.setdefault("gaps", []).extend(reconciliation_to_gaps("financial_pdf_reconciliation", enterprise_name, pdf_structured_reconciliation))

            if public_context:
                insert_index = 3 if pdf_structured_reconciliation else 2
                result.setdefault("timeline", []).insert(insert_index, {
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
                    ingest_index = 4 if pdf_structured_reconciliation else 3
                    if failed:
                        result.setdefault("timeline", []).insert(ingest_index, {
                            "id": str(uuid.uuid4()),
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "agent": "财务Agent",
                            "content": "巨潮年报 PDF 解析成功但入库失败",
                            "detail": "；".join(r.get("error") or "unknown" for r in failed),
                            "status": "completed",
                            "type": "risk",
                        })
                    else:
                        result.setdefault("timeline", []).insert(ingest_index, {
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
                result["financial_analysis_report"]["stock_code"] = listed_data.get("secu_code") if structured_success else listed_info.get("secu_code")
                result["financial_analysis_report"]["provider_fallbacks"] = all_provider_fallbacks
                reconciliation = pdf_structured_reconciliation or ((listed_data.get("cross_provider_reconciliation") if structured_success else {}) or {})
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

                    if pdf_structured_reconciliation:
                        timeline_title = "交叉校验年报PDF与结构化公开财报"
                        timeline_detail = f"PDF主数据源与结构化接口已校验{reconciliation.get('checked_count', 0)}项，差异{reconciliation.get('mismatch_count', 0)}项"
                    else:
                        timeline_title = "交叉校验公开财报结构化数据"
                        timeline_detail = f"东方财富与AKShare已校验{reconciliation.get('checked_count', 0)}项，差异{reconciliation.get('mismatch_count', 0)}项"
                    result.setdefault("timeline", []).insert(2, {
                        "id": str(uuid.uuid4()),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "agent": "财务Agent",
                        "content": timeline_title,
                        "detail": timeline_detail,
                        "status": "completed",
                        "type": "validation",
                        "findings": [
                            f"差异项：{item.get('year')}年{item.get('label')}"
                            for item in (reconciliation.get("mismatches") or [])[:5]
                        ] or ["核心指标跨源校验未发现超阈值差异"],
                    })
                for item in result["financial_analysis_report"].get("codeact_evidence") or []:
                    item.setdefault("source_url", listed_data.get("source_url") if structured_success else None)
                    item.setdefault("metadata", {})["stock_code"] = listed_data.get("secu_code") if structured_success else listed_info.get("secu_code")
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
                security_name = (listed_data if structured_success else listed_info).get("security_name")
                secu_code = (listed_data if structured_success else listed_info).get("secu_code")
                for key, label in metric_labels.items():
                    value = metrics.get(key)
                    if value and value != "数据不可用":
                        result.setdefault("evidence", []).append({
                            "label": label,
                            "value": value,
                            "source": data_source,
                            "source_name": f"{security_name} {secu_code} 近三年年报财务数据",
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
