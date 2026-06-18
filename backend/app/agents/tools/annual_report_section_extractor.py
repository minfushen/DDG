"""Section-specific extraction for Chinese A-share annual reports.

Extracts high-value narrative sections and converts them into auditable evidence.
Designed for digital PDFs; falls back gracefully when sections are missing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# Section header patterns. Order matters: more specific patterns first.
SECTION_PATTERNS: Dict[str, List[str]] = {
    "business_review": [
        r"经营情况讨论与分析",
        r"管理层讨论与分析",
        r"董事会(?:关于)?公司经营情况(?:的讨论与分析)?",
        r"第[三四]节\s+经营情况",
    ],
    "main_business_composition": [
        r"主营业务分产品、分地区、分行业",
        r"主营业务分产品(?:、分地区)?情况",
        r"营业收入构成",
        r"分行业.*?分产品.*?分地区",
        r"主营业务分析",
    ],
    "audit_opinion": [
        r"审计意见",
        r"审计报告",
        r"注册会计师.*?意见",
        r"标准无保留意见",
        r"保留意见",
        r"无法表示意见",
        r"否定意见",
    ],
    "asset_impairment": [
        r"资产减值(?:损失|准备)?",
        r"信用减值(?:损失|准备)?",
        r"减值准备",
        r"商誉减值",
        r"存货跌价",
    ],
    "major_risk_warnings": [
        r"重大风险提示",
        r"可能面对的风险",
        r"风险因素",
        r"重大风险",
        r"特别风险提示",
    ],
}

SECTION_LABELS: Dict[str, str] = {
    "business_review": "经营情况讨论与分析",
    "main_business_composition": "主营业务构成",
    "audit_opinion": "审计意见",
    "asset_impairment": "资产减值",
    "major_risk_warnings": "重大风险提示",
}

# Headers that signal the end of a narrative section.
SECTION_TERMINATORS = [
    r"^\s*第[一二三四五六七八九十\d]+节",
    r"^\s*\d+\.\d+\s+",
    r"^\s*重要事项",
    r"^\s*股份变动及股东情况",
    r"^\s*董事、监事、高级管理人员",
    r"^\s*财务报告",
    r"^\s*备查文件",
]


def _clean_text(text: str) -> str:
    """Normalize whitespace and strip noise from extracted text."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _find_section_bounds(text: str, patterns: List[str]) -> Optional[tuple[int, int]]:
    """Find (start, end) of the first matching section.

    End is determined by the next major section header or end of text.
    """
    combined = "|".join(f"(?:{pattern})" for pattern in patterns)
    match = re.search(combined, text)
    if not match:
        return None
    start = match.start()
    # Search for terminators after the header.
    terminator_pattern = "|".join(SECTION_TERMINATORS)
    remaining = text[start + 1:]
    term_match = re.search(terminator_pattern, remaining, re.MULTILINE)
    if term_match:
        end = start + 1 + term_match.start()
    else:
        end = len(text)
    return start, end


def extract_section(text: str, patterns: List[str], context_chars: int = 2000) -> Optional[str]:
    """Extract text around the first match of any pattern, bounded by section terminators."""
    bounds = _find_section_bounds(text, patterns)
    if not bounds:
        return None
    start, end = bounds
    snippet = text[start:end]
    if len(snippet) > context_chars:
        snippet = snippet[:context_chars] + "\n[...内容已截断...]"
    return _clean_text(snippet)


def extract_all_sections(extraction_result: Dict[str, Any], context_chars: int = 2000) -> Dict[str, Optional[str]]:
    """Extract all priority sections from PDF extraction result."""
    text = extraction_result.get("text") or ""
    return {
        section: extract_section(text, patterns, context_chars=context_chars)
        for section, patterns in SECTION_PATTERNS.items()
    }


def _is_main_business_table(table: List[List[str]]) -> bool:
    """Heuristic to identify main-business-composition tables."""
    if not table or len(table) < 2:
        return False
    header = " ".join(str(cell or "") for cell in table[0])
    keywords = ["产品", "地区", "行业", "营业收入", "营业成本", "毛利率", "收入", "占比"]
    score = sum(1 for keyword in keywords if keyword in header)
    return score >= 2


def _row_to_dict(header: List[str], row: List[str]) -> Dict[str, str]:
    """Map a table row to a dict using the header."""
    result: Dict[str, str] = {}
    for index, key in enumerate(header):
        key = str(key or "").strip().replace("\n", " ")
        if not key:
            continue
        value = str(row[index] if index < len(row) else "").strip()
        result[key] = value
    return result


def extract_main_business_tables(tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
    """Extract structured rows from main-business-composition tables."""
    results: List[Dict[str, Any]] = []
    for table in tables:
        if not _is_main_business_table(table):
            continue
        header = table[0]
        for row in table[1:]:
            row_dict = _row_to_dict(header, row)
            item_name = (
                row_dict.get("产品")
                or row_dict.get("地区")
                or row_dict.get("行业")
                or row_dict.get("项目")
                or row_dict.get("分产品")
                or row_dict.get("分地区")
                or row_dict.get("分行业")
                or ""
            )
            if not item_name or item_name in {"合计", "总计", "分产品", "分地区", "分行业"}:
                continue
            income = (
                row_dict.get("营业收入")
                or row_dict.get("收入")
                or row_dict.get("主营业务收入")
                or ""
            )
            income_ratio = (
                row_dict.get("营业收入占比")
                or row_dict.get("收入占比")
                or row_dict.get("占比")
                or ""
            )
            gross_margin = row_dict.get("毛利率") or ""
            results.append({
                "item_name": item_name,
                "income": income,
                "income_ratio": income_ratio,
                "gross_margin": gross_margin,
                "raw": row_dict,
            })
    return results[:20]


def _stable_evidence_id(announcement_id: str, section: str) -> str:
    import hashlib
    raw = f"cninfo_annual_report|{announcement_id}|{section}"
    return "ev_cninfo_ar_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def sections_to_evidence(
    sections: Dict[str, Optional[str]],
    source_url: str,
    announcement_meta: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Convert extracted sections into evidence items following the existing schema."""
    evidence: List[Dict[str, Any]] = []
    title = announcement_meta.get("title") or "年报"
    announcement_id = announcement_meta.get("announcement_id") or ""
    published_at = announcement_meta.get("published_at") or ""
    parser_used = announcement_meta.get("parser_used") or ""
    full_text_length = announcement_meta.get("full_text_length") or 0

    for section, text in sections.items():
        if not text:
            continue
        label = f"巨潮年报-{SECTION_LABELS.get(section, section)}"
        value = text[:500]
        claim = f"巨潮资讯网披露《{title}》PDF中提取到{SECTION_LABELS.get(section, section)}内容。"
        evidence.append({
            "id": _stable_evidence_id(announcement_id, section),
            "label": label,
            "value": value,
            "claim": claim,
            "source": source_url,
            "source_name": "巨潮资讯网",
            "source_url": source_url,
            "source_type": "exchange_announcement",
            "trust_level": "high",
            "confidence": 0.85,
            "requires_manual_review": True,
            "agent": "financial",
            "domain": "financial",
            "metadata": {
                "section": section,
                "section_label": SECTION_LABELS.get(section, section),
                "announcement_type": announcement_meta.get("announcement_type"),
                "announcement_id": announcement_id,
                "title": title,
                "published_at": published_at,
                "parser_used": parser_used,
                "full_text_length": full_text_length,
                "excerpt": text[:1200],
            },
        })
    return evidence
