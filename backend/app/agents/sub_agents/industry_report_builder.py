"""行业分析报告生成器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

from app.config import settings
from app.agents.sub_agents.industry_diagnostic_writer import build_industry_diagnostic_narrative


INDUSTRY_GUIDE_DIR = settings.BASE_DIR / "knowledge_base" / "industry_guides"


def _read_guide(file_name: str) -> Dict[str, str]:
    path = INDUSTRY_GUIDE_DIR / file_name
    if not path.exists():
        return {"file": file_name, "content": "", "path": str(path)}
    return {"file": file_name, "content": path.read_text(encoding="utf-8"), "path": str(path)}


def _strip_frontmatter(content: str) -> str:
    return re.sub(r"^---\n.*?\n---\n", "", content or "", flags=re.S).strip()


def _section(content: str, title_keywords: List[str]) -> str:
    text = _strip_frontmatter(content)
    pattern = r"^##\s+[^\n]*(?:" + "|".join(map(re.escape, title_keywords)) + r")[^\n]*\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text, re.M | re.S)
    if not match:
        return ""
    return match.group(1).strip()


def _bullets(section: str, limit: int = 8) -> List[str]:
    rows = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        item = re.sub(r"^-\s*", "", line).strip()
        item = re.sub(r"\*\*(.*?)\*\*", r"\1", item)
        if item:
            rows.append(item)
    return rows[:limit]


def _risk_items(content: str, limit: int = 8) -> List[str]:
    risk_section = _section(content, ["风险点识别", "风险"])
    items = []
    for line in risk_section.splitlines():
        line = line.strip()
        numbered = re.match(r"\d+[.、]\s*\*\*(.*?)\*\*[:：]?(.*)", line)
        if numbered:
            items.append(f"{numbered.group(1)}：{numbered.group(2).strip()}".strip("："))
            continue
        bullet = re.match(r"-\s*(.*)", line)
        if bullet:
            items.append(re.sub(r"\*\*(.*?)\*\*", r"\1", bullet.group(1)).strip())
    if items:
        return [item for item in items if item][:limit]

    text = _strip_frontmatter(content)
    for match in re.finditer(r"^###\s+\d*[.、]?\s*([^\n]*风险[^\n]*)\n(.*?)(?=^###\s+|^##\s+|\Z)", text, re.M | re.S):
        heading = match.group(1).strip()
        bullets = _bullets(match.group(2), 4)
        if bullets:
            items.extend([f"{heading}：{item}" for item in bullets])
        else:
            items.append(heading)
    return [item for item in items if item][:limit]


def _tables(content: str) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    tables = []
    i = 0
    while i < len(lines):
        if "|" not in lines[i] or i + 1 >= len(lines) or "---" not in lines[i + 1]:
            i += 1
            continue
        headers = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
        i += 2
        rows = []
        while i < len(lines) and "|" in lines[i]:
            cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
            i += 1
        tables.append({"headers": headers, "rows": rows})
    return tables


def _focus_line(content: str) -> str:
    match = re.search(r"\*\*重点[:：](.*?)\*\*", content or "")
    return match.group(1).strip() if match else ""


def _title(content: str, fallback: str) -> str:
    text = _strip_frontmatter(content)
    match = re.search(r"^#\s+(.+)$", text, re.M)
    return match.group(1).strip() if match else fallback


def _merge_unique(items: List[str], limit: int = 10) -> List[str]:
    result = []
    seen = set()
    for item in items:
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def build_industry_analysis_report(
    enterprise_name: str,
    classification: Dict[str, Any],
    retrieval_result: Dict[str, Any] | None = None,
    public_info: Dict[str, Any] | None = None,
    industry_knowledge_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """基于行业识别结果和本地行业指南生成结构化行业分析报告。"""
    guide_files = classification.get("guide_files") or ["manufacturing.md"]
    guides = [_read_guide(file_name) for file_name in guide_files]
    primary = guides[0] if guides else {"content": "", "file": "", "path": ""}
    combined = "\n\n".join(item["content"] for item in guides if item.get("content"))

    focus = _merge_unique([_focus_line(item["content"]) for item in guides if item.get("content")], 3)
    diligence_points = _merge_unique(
        _bullets(_section(combined, ["尽调该看什么", "尽调重点关注领域"]), 10),
        10,
    )
    source_paths = _merge_unique(
        _bullets(_section(combined, ["建议重点来源", "建议重点来源与检索路径", "实用检索词"]), 10),
        10,
    )
    risks = _merge_unique(_risk_items(combined, 10), 10)
    tables = _tables(combined)
    metric_rows = tables[0]["rows"] if tables else []
    retrieved_hits = (retrieval_result or {}).get("results") or []
    public_info = public_info or {}
    public_basic = public_info.get("basic_info") or {}
    public_review = public_info.get("annual_business_review") or {}
    public_main_business = public_info.get("main_business_composition") or []
    public_clues = public_info.get("search_clues") or {}
    industry_knowledge_context = industry_knowledge_context or {}
    triggered_rules = industry_knowledge_context.get("triggered_rules") or []
    knowledge_briefs = industry_knowledge_context.get("knowledge_briefs") or []
    industry_position_lines = []
    if public_basic.get("profile"):
        industry_position_lines.append(public_basic.get("profile"))
    if public_basic.get("concepts"):
        industry_position_lines.append(f"资本市场概念标签：{public_basic.get('concepts')}。")

    if not risks:
        risks = ["行业风险知识库尚未覆盖该细分行业，建议补充行业指南或人工复核。"]
    if not diligence_points:
        diligence_points = ["行业指南未抽取到明确尽调重点，建议补充该行业的授信审查模板。"]

    industry = {
        "code": classification.get("industry_code"),
        "name": classification.get("industry_name"),
        "path": classification.get("industry_path", []),
        "path_codes": classification.get("industry_path_codes", []),
        "semantic_industry_id": classification.get("semantic_industry_id"),
        "semantic_industry_name": classification.get("semantic_industry_name"),
        "confidence": classification.get("confidence", 0),
        "matched_signals": classification.get("matched_signals", []),
        "candidates": classification.get("candidates", []),
        "classification_source": classification.get("classification_source") or "rule_fallback",
        "llm_reason": classification.get("llm_reason") or "",
        "ignored_noise": classification.get("ignored_noise") or [],
        "llm_elapsed_ms": classification.get("llm_elapsed_ms"),
        "llm_error": classification.get("llm_error") or "",
    }
    source_label = "LLM语义裁判" if industry.get("classification_source") == "llm_adjudicated" else "规则候选兜底"
    diagnostic_narrative = build_industry_diagnostic_narrative(
        enterprise_name=enterprise_name,
        classification=classification,
        public_info=public_info,
        industry_knowledge_context=industry_knowledge_context,
    )

    sections = [
        {
            "title": "一、行业定位与周期判断",
            "analysis": diagnostic_narrative.get("summary") or [],
            "diagnostics": (diagnostic_narrative.get("diagnostics") or {}).get("diagnostics") or [],
            "overall_position": (diagnostic_narrative.get("diagnostics") or {}).get("overall_position") or {},
            "source": diagnostic_narrative.get("source"),
            "llm_provider": diagnostic_narrative.get("llm_provider"),
            "llm_elapsed_ms": diagnostic_narrative.get("llm_elapsed_ms"),
            "quality_warnings": diagnostic_narrative.get("quality_warnings") or [],
        },
        {
            "title": "二、行业识别结论",
            "analysis": [
                f"目标企业被识别为 {industry.get('semantic_industry_name') or industry.get('name')}。",
                f"标准行业路径：{' > '.join(industry.get('path') or [])}。",
                f"行业识别置信度：{round((industry.get('confidence') or 0) * 100)}%。",
                f"行业识别方式：{source_label}。",
                f"LLM判断依据：{industry.get('llm_reason')}。" if industry.get("llm_reason") else "",
                f"已忽略通用经营范围噪声：{'、'.join(industry.get('ignored_noise') or [])}。" if industry.get("ignored_noise") else "",
                f"LLM裁判未启用或未通过：{industry.get('llm_error')}。" if industry.get("llm_error") else "",
                f"上市公司公开行业标签：{public_basic.get('industry') or '未获取'}。" if public_basic else "",
                f"主营业务：{public_basic.get('main_business') or '未获取'}。" if public_basic else "",
            ],
            "signals": industry.get("matched_signals", []),
        },
        {
            "title": "三、年报经营讨论与主营构成",
            "analysis": [
                f"年报经营讨论来源：{public_review.get('report_name') or '未获取'}。",
                public_review.get("business_review") or "未获取上市公司年报经营讨论摘要。",
            ],
            "rows": public_main_business[:10],
        },
        {
            "title": "四、行业地位与研报摘要",
            "analysis": industry_position_lines[:2] + [
                item.get("content", "") for item in (public_clues.get("industry_position") or [])[:3]
            ] + [
                item.get("content", "") for item in (public_clues.get("research_summaries") or [])[:3]
            ] or ["未获取到稳定的行业地位或研报摘要公开线索，建议补充券商研报和年报行业章节。"],
            "sources": [
                {"title": item.get("title"), "url": item.get("url"), "source": item.get("source")}
                for item in ((public_clues.get("industry_position") or []) + (public_clues.get("research_summaries") or []))[:8]
            ],
        },
        {
            "title": "五、诉讼公告、担保质押与资本市场风险线索",
            "analysis": [
                item.get("content", "") for item in (public_clues.get("litigation_announcements") or [])[:3]
            ] + [
                item.get("content", "") for item in (public_clues.get("guarantee_pledge_announcements") or [])[:3]
            ] or ["未获取到稳定的诉讼公告、担保或质押公开线索，仍需人工复核巨潮资讯和交易所公告。"],
            "sources": [
                {"title": item.get("title"), "url": item.get("url"), "source": item.get("source")}
                for item in ((public_clues.get("litigation_announcements") or []) + (public_clues.get("guarantee_pledge_announcements") or []))[:8]
            ],
        },
        {
            "title": "六、行业尽调重点",
            "analysis": focus + diligence_points,
        },
        {
            "title": "七、行业动态规则与关键假设",
            "analysis": _merge_unique([
                f"触发规则 {rule.get('rule_id')}：{rule.get('title')}。核查重点：{'、'.join(rule.get('required_checks') or [])}。"
                for rule in triggered_rules[:8]
            ] + [
                "关键假设需人工确认：未来行业增速、原材料价格、技术路线、核心客户需求、政策环境和行业集中度变化。",
                "低可信度来源只能作为线索，不得作为授信判断的核心证据。",
            ], 10),
            "rules": triggered_rules[:8],
            "knowledge_sources": knowledge_briefs[:6],
        },
        {
            "title": "八、关键财务指标阈值",
            "rows": metric_rows,
        },
        {
            "title": "九、行业风险",
            "risks": risks,
        },
        {
            "title": "十、建议来源与核验路径",
            "analysis": source_paths or ["建议补充行业主管部门、行业协会、评级机构与上市公司年报等资料。"],
        },
        {
            "title": "十一、知识库来源",
            "sources": [
                {"title": _title(item["content"], item["file"]), "file": item["file"], "path": item["path"]}
                for item in guides
            ] + [
                {
                    "title": hit.get("title"),
                    "file": hit.get("filename") or hit.get("relative_path"),
                    "path": hit.get("source"),
                    "category": hit.get("category"),
                    "confidence": hit.get("confidence"),
                    "retrieval_mode": hit.get("retrieval_mode"),
                    "disclaimer": hit.get("disclaimer"),
                }
                for hit in retrieved_hits[:8]
            ],
        },
    ]

    evidence = [
        {
            "label": "标准行业分类",
            "value": f"{industry.get('code')} {industry.get('name')}",
            "source": f"国民经济行业分类四级代码表 / {source_label}",
        },
        {
            "label": "行业知识库",
            "value": ", ".join(_merge_unique(guide_files + [str(hit.get("filename") or hit.get("relative_path") or "") for hit in retrieved_hits], 12)),
            "source": "本地行业尽调指南",
        },
    ]
    if public_info.get("success"):
        evidence.extend(public_info.get("evidence", []))
        if public_basic.get("industry"):
            evidence.append({"label": "上市公司行业标签", "value": public_basic.get("industry"), "source": "东方财富F10"})
        if public_review.get("business_review"):
            evidence.append({"label": "年报经营讨论", "value": public_review.get("report_name") or "已获取", "source": "东方财富F10经营分析"})
    for rule in triggered_rules[:8]:
        evidence.append({
            "label": "行业分析触发规则",
            "value": f"{rule.get('rule_id')} {rule.get('title')}",
            "source": "industry_analysis_rules.json",
            "confidence": rule.get("confidence", 0.78),
        })

    risk_summary = risks[:3]
    diagnostic_summary = diagnostic_narrative.get("summary") or []
    return {
        "report_type": "industry_analysis",
        "enterprise_name": enterprise_name,
        "generated_from": "行业代码库 + 本地行业知识库",
        "industry": industry,
        "sections": sections,
        "risk_summary": diagnostic_summary[:4] or risk_summary,
        "industry_diagnostics": diagnostic_narrative.get("diagnostics"),
        "industry_diagnostic_summary": diagnostic_summary,
        "industry_diagnostic_source": diagnostic_narrative.get("source"),
        "industry_diagnostic_provider": diagnostic_narrative.get("llm_provider"),
        "industry_diagnostic_elapsed_ms": diagnostic_narrative.get("llm_elapsed_ms"),
        "industry_diagnostic_warnings": diagnostic_narrative.get("quality_warnings") or [],
        "evidence": evidence,
        "retrieval_result": retrieval_result,
        "industry_knowledge_context": {
            "triggered_rules": triggered_rules,
            "knowledge_briefs": knowledge_briefs,
            "retrieval_mode": (industry_knowledge_context.get("retrieval") or {}).get("mode"),
            "query": industry_knowledge_context.get("query"),
        },
        "listed_company_public_info": public_info if public_info.get("success") else None,
    }
