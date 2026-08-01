"""Cninfo announcement provider.

Cninfo is used as an authoritative A-share disclosure source. This module only
collects announcement metadata and PDF URLs; PDF table parsing is handled by a
separate future pipeline.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import html
import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.pdf_extraction_engine import extract_pdf_from_url, download_pdf, extract_pdf
from app.agents.tools.annual_report_section_extractor import (
    extract_all_sections,
    extract_main_business_tables,
    sections_to_evidence,
)
from app.config import settings
from app.engines.rebecca.parsers.financial_pdf_pipeline import parse_annual_report_pdf
from app.rag.pdf_knowledge_ingestion import auto_ingest_cninfo_annual_report


CNINFO_FULLTEXT_URL = "https://www.cninfo.com.cn/new/fulltextSearch/full"
CNINFO_HISTORY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE = "https://static.cninfo.com.cn"
CNINFO_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.cninfo.com.cn/new/fulltextSearch",
    "User-Agent": "Mozilla/5.0",
}


ANNOUNCEMENT_KEYWORDS = {
    "annual_report": ["年度报告", "年报"],
    "semiannual_report": ["半年度报告", "半年报"],
    "quarterly_report": ["季度报告", "一季度", "三季度"],
    "inquiry_letter": ["问询函", "问询函回复", "审核问询"],
    "litigation": ["诉讼", "仲裁"],
    "guarantee": ["担保", "对外担保"],
    "pledge": ["质押", "股权质押"],
    "penalty": ["处罚", "监管函", "纪律处分", "行政处罚"],
    "performance": ["业绩预告", "业绩快报"],
}


def clean_cninfo_title(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"</?em>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def classify_announcement(title: str) -> str:
    clean_title = clean_cninfo_title(title)
    for kind, keywords in ANNOUNCEMENT_KEYWORDS.items():
        if any(keyword in clean_title for keyword in keywords):
            return kind
    return "other"


# 摘要/英文/已取消版本通常正文很短或非中文，应让完整年报优先解析。
_ANNUAL_REPORT_LOW_PRIORITY_MARKERS = ["摘要", "英文", "已取消", "更正后", "（修订版）"]


def _annual_report_priority(title: str) -> int:
    """完整年报排在摘要/英文/更正版之前（数值越小优先级越高）。"""
    clean_title = clean_cninfo_title(title)
    if any(marker in clean_title for marker in _ANNUAL_REPORT_LOW_PRIORITY_MARKERS):
        return 1
    return 0


def _format_timestamp(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ""
    if number <= 0:
        return ""
    # Cninfo timestamps are milliseconds. Use Asia/Shanghai for display.
    dt = datetime.fromtimestamp(number / 1000, tz=timezone(timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d")


def _pdf_url(adjunct_url: str) -> str:
    if not adjunct_url:
        return ""
    if adjunct_url.startswith("http"):
        return adjunct_url
    return f"{CNINFO_STATIC_BASE}/{adjunct_url.lstrip('/')}"


def normalize_cninfo_announcement(item: Dict[str, Any]) -> Dict[str, Any]:
    title = clean_cninfo_title(item.get("announcementTitle") or item.get("shortTitle"))
    adjunct_url = item.get("adjunctUrl") or ""
    return {
        "sec_code": str(item.get("secCode") or ""),
        "sec_name": str(item.get("secName") or ""),
        "org_id": str(item.get("orgId") or ""),
        "announcement_id": str(item.get("announcementId") or item.get("id") or ""),
        "title": title,
        "announcement_type": classify_announcement(title),
        "published_at": _format_timestamp(item.get("announcementTime")),
        "adjunct_url": adjunct_url,
        "pdf_url": _pdf_url(adjunct_url),
        "adjunct_size_kb": item.get("adjunctSize"),
        "source_name": "巨潮资讯网",
        "source_type": "official_or_authoritative_public_source",
        "trust_level": "high",
        "confidence": 0.9,
        "requires_manual_review": False,
    }


def announcement_to_evidence(item: Dict[str, Any], agent: str = "financial") -> Dict[str, Any]:
    return {
        "label": f"巨潮公告：{item.get('announcement_type') or '公告'}",
        "value": item.get("title") or "公告",
        "claim": f"巨潮资讯网披露公告《{item.get('title') or '公告'}》。",
        "source": item.get("pdf_url") or "巨潮资讯网",
        "source_name": "巨潮资讯网",
        "source_url": item.get("pdf_url"),
        "source_type": "official_or_authoritative_public_source",
        "trust_level": "high",
        "confidence": 0.9,
        "requires_manual_review": False,
        "agent": agent,
        "domain": agent,
        "metadata": item,
    }


def fetch_and_extract_annual_report_pdf(
    item: Dict[str, Any],
    enterprise_name: str = "",
    timeout: int = 30,
) -> Dict[str, Any]:
    """Download, extract and optionally ingest a single annual report PDF.

    Returns extraction_result, sections, main_business_rows, evidence_items,
    pipeline_result and ingestion_result. Failures are captured gracefully
    and do not raise.
    """
    import hashlib

    pdf_url = item.get("pdf_url") or ""
    if not pdf_url:
        return {
            "success": False,
            "pdf_url": "",
            "extraction_result": {},
            "sections": {},
            "main_business_rows": [],
            "evidence_items": [],
            "pipeline_result": None,
            "ingestion_result": {},
            "error": "No PDF URL",
        }

    pipeline_result = None
    extraction_result: Dict[str, Any] = {}

    # 优先使用四阶段 PDF 解析管道
    if settings.ENABLE_CNINFO_PDF_PIPELINE:
        pdf_bytes = download_pdf(pdf_url, timeout=timeout)
        if pdf_bytes:
            report_year = None
            # 年报标题里的年份才是报告期（如 2025 年报），披露日期可能是 2026 年
            title = item.get("title", "")
            if title:
                m = re.search(r"20\d{2}", title)
                if m:
                    report_year = int(m.group())
            if report_year is None:
                published = item.get("published_at") or ""
                if published:
                    m = re.search(r"20\d{2}", published)
                    if m:
                        report_year = int(m.group())
            pipeline_result = parse_annual_report_pdf(
                pdf_bytes=pdf_bytes,
                enterprise_name=enterprise_name or item.get("sec_name") or "",
                stock_code=item.get("sec_code") or "",
                report_year=report_year,
                pdf_url=pdf_url,
            )
            if pipeline_result.success:
                extraction_result = pipeline_result.extraction_result or {}
            else:
                # pipeline 失败时兜底用本地解析器抽取原文
                fallback = extract_pdf(pdf_bytes)
                extraction_result = fallback if fallback.get("success") else {}
        else:
            # 下载失败回退到旧路径
            extraction_result = extract_pdf_from_url(pdf_url, timeout=timeout)
    else:
        extraction_result = extract_pdf_from_url(pdf_url, timeout=timeout)

    if not extraction_result.get("success"):
        return {
            "success": False,
            "pdf_url": pdf_url,
            "extraction_result": extraction_result,
            "sections": {},
            "main_business_rows": [],
            "evidence_items": [],
            "pipeline_result": pipeline_result,
            "ingestion_result": {},
            "error": extraction_result.get("error") or "PDF extraction failed",
        }

    sections = extract_all_sections(extraction_result, context_chars=2000)
    main_business_rows = extract_main_business_tables(extraction_result.get("tables") or [])
    meta = {
        **item,
        "parser_used": extraction_result.get("metadata", {}).get("parser_used"),
        "full_text_length": len(extraction_result.get("text") or ""),
    }
    evidence_items = sections_to_evidence(sections, pdf_url, meta)
    if main_business_rows:
        evidence_items.append({
            "label": "巨潮年报-主营业务构成表",
            "value": f"{len(main_business_rows)}项",
            "claim": f"巨潮资讯网披露《{item.get('title') or '年报'}》PDF中提取到主营业务构成表。",
            "source": pdf_url,
            "source_name": "巨潮资讯网",
            "source_url": pdf_url,
            "source_type": "exchange_announcement",
            "trust_level": "high",
            "confidence": 0.85,
            "requires_manual_review": True,
            "agent": "financial",
            "domain": "financial",
            "metadata": {
                "section": "main_business_composition_table",
                "announcement_type": item.get("announcement_type"),
                "announcement_id": item.get("announcement_id"),
                "title": item.get("title"),
                "published_at": item.get("published_at"),
                "parser_used": extraction_result.get("metadata", {}).get("parser_used"),
                "rows": main_business_rows,
            },
        })

    if pipeline_result is not None:
        evidence_items.extend(pipeline_result_to_evidence(pipeline_result, meta))

    ingestion_result: Dict[str, Any] = {}
    if enterprise_name:
        ingestion_result = auto_ingest_cninfo_annual_report(
            enterprise_name=enterprise_name,
            cninfo_extraction_result={
                "success": True,
                "pdf_url": pdf_url,
                "title": item.get("title"),
                "announcement_id": item.get("announcement_id"),
                "published_at": item.get("published_at"),
                "extraction_result": extraction_result,
                "sections": sections,
                "main_business_rows": main_business_rows,
                "pipeline_result": pipeline_result,
            },
        )
        if not ingestion_result.get("success"):
            evidence_items.append({
                "label": "巨潮年报-入库状态",
                "value": "解析成功但未能写入企业知识库",
                "claim": f"巨潮资讯网披露《{item.get('title') or '年报'}》PDF解析成功，但自动入库失败：{ingestion_result.get('error')}。",
                "source": pdf_url,
                "source_name": "巨潮资讯网",
                "source_url": pdf_url,
                "source_type": "exchange_announcement",
                "trust_level": "medium",
                "confidence": 0.7,
                "requires_manual_review": True,
                "agent": "financial",
                "domain": "financial",
                "metadata": {
                    "section": "ingestion_status",
                    "ingestion_result": ingestion_result,
                },
            })

    return {
        "success": True,
        "pdf_url": pdf_url,
        "extraction_result": extraction_result,
        "sections": sections,
        "main_business_rows": main_business_rows,
        "evidence_items": evidence_items,
        "pipeline_result": pipeline_result,
        "ingestion_result": ingestion_result,
        "error": "",
    }


def _stable_pipeline_evidence_id(prefix: str, pdf_url: str, salt: str) -> str:
    import hashlib
    raw = f"cninfo_pipeline|{prefix}|{pdf_url}|{salt}"
    return "ev_cninfo_pl_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def pipeline_result_to_evidence(
    pipeline_result: Any,
    announcement_meta: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """把四阶段 PDF 管道结果转成可审计 evidence。"""
    if pipeline_result is None:
        return []

    # 兼容 dataclass 和 dict
    def _get(attr: str, default: Any = None) -> Any:
        if isinstance(pipeline_result, dict):
            return pipeline_result.get(attr, default)
        return getattr(pipeline_result, attr, default)

    pdf_url = _get("pdf_url", "")
    title = announcement_meta.get("title") or "年报"
    announcement_id = announcement_meta.get("announcement_id") or ""
    evidence: List[Dict[str, Any]] = []

    evidence.append({
        "id": _stable_pipeline_evidence_id("coverage", pdf_url, announcement_id),
        "label": "年报PDF-三大表覆盖度",
        "value": _get("main_table_coverage", "0/3"),
        "claim": f"巨潮资讯网披露《{title}》PDF四阶段解析完成，三大表覆盖度为{_get('main_table_coverage', '0/3')}。",
        "source": pdf_url,
        "source_name": "巨潮资讯网",
        "source_url": pdf_url,
        "source_type": "exchange_announcement",
        "trust_level": "high",
        "confidence": 0.85,
        "requires_manual_review": False,
        "agent": "financial",
        "domain": "financial",
        "metadata": {
            "section": "pipeline_coverage",
            "auto_judgment_rate": _get("auto_judgment_rate", 0.0),
            "rule_family_coverage": _get("rule_family_coverage", "0/23"),
            "digital_reach_rate": _get("digital_reach_rate", 0.0),
            "announcement_id": announcement_id,
            "title": title,
        },
    })

    issues = _get("issues", []) or []
    validation_passed = not bool(issues)
    evidence.append({
        "id": _stable_pipeline_evidence_id("validation", pdf_url, announcement_id),
        "label": "年报PDF-会计恒等式校验",
        "value": "通过" if validation_passed else f"未通过（{len(issues)}项）",
        "claim": f"巨潮资讯网披露《{title}》PDF四阶段解析的会计恒等式校验{'通过' if validation_passed else '未通过'}。",
        "source": pdf_url,
        "source_name": "巨潮资讯网",
        "source_url": pdf_url,
        "source_type": "exchange_announcement",
        "trust_level": "high" if validation_passed else "medium",
        "confidence": 0.85 if validation_passed else 0.7,
        "requires_manual_review": not validation_passed,
        "agent": "financial",
        "domain": "financial",
        "metadata": {
            "section": "pipeline_validation",
            "issues": issues[:10],
            "auto_judgment_rate": _get("auto_judgment_rate", 0.0),
            "announcement_id": announcement_id,
            "title": title,
        },
    })

    if _get("needs_human_review", True):
        evidence.append({
            "id": _stable_pipeline_evidence_id("manual_review", pdf_url, announcement_id),
            "label": "年报PDF-需人工复核",
            "value": "解析结果存在缺失表或勾稽异常，建议人工复核",
            "claim": f"巨潮资讯网披露《{title}》PDF四阶段解析识别到缺失表或勾稽异常，已标记需人工复核。",
            "source": pdf_url,
            "source_name": "巨潮资讯网",
            "source_url": pdf_url,
            "source_type": "exchange_announcement",
            "trust_level": "medium",
            "confidence": 0.7,
            "requires_manual_review": True,
            "agent": "financial",
            "domain": "financial",
            "metadata": {
                "section": "pipeline_manual_review",
                "issues": issues[:10],
                "announcement_id": announcement_id,
                "title": title,
            },
        })

    return evidence


def enhance_annual_report_evidence(
    base_evidence: List[Dict[str, Any]],
    extract_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge PDF-extracted evidence into base announcement evidence."""
    merged = list(base_evidence)
    for result in extract_results:
        for item in result.get("evidence_items") or []:
            merged.append(item)
    return merged


def _date_range(years_back: int = 4) -> tuple[str, str]:
    end = datetime.now(tz=timezone(timedelta(hours=8))).date()
    start = end.replace(year=max(2000, end.year - years_back))
    return start.isoformat(), end.isoformat()


def search_cninfo_announcements(
    enterprise_name: str,
    stock_code: str = "",
    stock_exchange: str = "",
    keyword: str = "",
    max_results: int = 10,
    years_back: int = 4,
    extract_pdf_content: bool = False,
    max_pdf_extract: int = 2,
) -> Dict[str, Any]:
    company = resolve_listed_company(enterprise_name, stock_code=stock_code, stock_exchange=stock_exchange)
    if not company:
        return {"success": False, "error": "未识别到上市公司证券代码", "results": [], "evidence": []}

    start_date, end_date = _date_range(years_back)
    stock = company.get("stock_code") or ""
    keyword_parts = [part for part in re.split(r"[\s,，、/]+", keyword or "") if part]
    query_candidates = []
    if keyword:
        query_candidates.append(" ".join([stock, keyword]).strip())
    query_candidates.extend(" ".join([stock, part]).strip() for part in keyword_parts)
    query_candidates.append(stock or enterprise_name)

    payloads: List[Dict[str, Any]] = []
    errors: List[str] = []
    normalized_by_key: Dict[str, Dict[str, Any]] = {}
    for query in query_candidates:
        params = {
            "searchkey": query,
            "sdate": start_date,
            "edate": end_date,
            "isfulltext": "false",
            "sortName": "pubdate",
            "sortType": "desc",
            "pageNum": "1",
        }
        try:
            response = httpx.get(CNINFO_FULLTEXT_URL, params=params, headers=CNINFO_HEADERS, timeout=20)
            response.raise_for_status()
            payload = response.json()
            payloads.append(payload)
        except Exception as exc:
            errors.append(f"{query}: {type(exc).__name__}: {exc}")
            continue
        rows = payload.get("announcements") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = normalize_cninfo_announcement(row)
            key = item.get("announcement_id") or item.get("pdf_url") or item.get("title")
            if key:
                normalized_by_key.setdefault(key, item)
        if normalized_by_key:
            break

    normalized = list(normalized_by_key.values())
    normalized = [row for row in normalized if row.get("sec_code") == company.get("stock_code")]
    normalized = normalized[: max(1, int(max_results or 10))]
    evidence = [announcement_to_evidence(row) for row in normalized]

    pdf_extraction_results: List[Dict[str, Any]] = []
    ingestion_results: List[Dict[str, Any]] = []
    ingestion_gaps: List[Dict[str, Any]] = []
    pipeline_results: List[Dict[str, Any]] = []
    if extract_pdf_content:
        annual_reports = [row for row in normalized if row.get("announcement_type") == "annual_report"]
        # 先按发布时间倒序（最新在前），再按完整年报优先于摘要/英文版稳定排序。
        annual_reports.sort(key=lambda row: str(row.get("published_at") or ""), reverse=True)
        annual_reports.sort(key=lambda row: _annual_report_priority(row.get("title", "")))
        for item in annual_reports[:max(1, int(max_pdf_extract or 1))]:
            result = fetch_and_extract_annual_report_pdf(item, enterprise_name=enterprise_name, timeout=20)
            pdf_extraction_results.append(result)
            if result.get("ingestion_result"):
                ingestion_results.append(result["ingestion_result"])
                ingestion_gaps.extend(result["ingestion_result"].get("gaps") or [])
            if result.get("pipeline_result") is not None:
                pr = result["pipeline_result"]
                if hasattr(pr, "success"):
                    pipeline_results.append({
                        "pdf_url": result.get("pdf_url"),
                        "success": pr.success,
                        "main_table_coverage": pr.main_table_coverage,
                        "auto_judgment_rate": pr.auto_judgment_rate,
                        "needs_human_review": pr.needs_human_review,
                        "issues": pr.issues,
                    })
                else:
                    pipeline_results.append({
                        "pdf_url": result.get("pdf_url"),
                        "success": pr.get("success"),
                        "main_table_coverage": pr.get("main_table_coverage"),
                        "auto_judgment_rate": pr.get("auto_judgment_rate"),
                        "needs_human_review": pr.get("needs_human_review"),
                        "issues": pr.get("issues"),
                    })
        evidence = enhance_annual_report_evidence(evidence, pdf_extraction_results)

    return {
        "success": bool(normalized),
        "provider": "cninfo",
        "query": query_candidates[0] if query_candidates else enterprise_name,
        "query_candidates": query_candidates,
        "enterprise_name": enterprise_name,
        "stock_code": company.get("stock_code"),
        "stock_exchange": company.get("stock_exchange"),
        "secu_code": company.get("secu_code"),
        "security_name": company.get("security_name"),
        "total_record_num": (payloads[-1].get("totalRecordNum") if payloads else None),
        "errors": errors,
        "results": normalized,
        "evidence": evidence,
        "pdf_extraction_results": pdf_extraction_results,
        "pipeline_results": pipeline_results,
        "extracted_evidence": [item for result in pdf_extraction_results for item in result.get("evidence_items", [])],
        "ingestion_results": ingestion_results,
        "ingestion_gaps": ingestion_gaps,
    }


class _CninfoAnnouncementTool:
    name = "search_cninfo_announcements"

    def _run(self, enterprise_name: str, stock_code: str = "", stock_exchange: str = "", keyword: str = "", max_results: int = 10, **_: Any) -> str:
        return json.dumps(search_cninfo_announcements(
            enterprise_name=enterprise_name,
            stock_code=stock_code,
            stock_exchange=stock_exchange,
            keyword=keyword,
            max_results=max_results,
        ), ensure_ascii=False)


search_cninfo_announcements_tool = _CninfoAnnouncementTool()
