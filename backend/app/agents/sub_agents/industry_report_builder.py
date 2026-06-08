"""行业分析报告生成器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

from app.config import settings


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
    }

    sections = [
        {
            "title": "一、行业识别结论",
            "analysis": [
                f"目标企业被识别为 {industry.get('semantic_industry_name') or industry.get('name')}。",
                f"标准行业路径：{' > '.join(industry.get('path') or [])}。",
                f"行业识别置信度：{round((industry.get('confidence') or 0) * 100)}%。",
            ],
            "signals": industry.get("matched_signals", []),
        },
        {
            "title": "二、行业尽调重点",
            "analysis": focus + diligence_points,
        },
        {
            "title": "三、关键财务指标阈值",
            "rows": metric_rows,
        },
        {
            "title": "四、行业风险",
            "risks": risks,
        },
        {
            "title": "五、建议来源与核验路径",
            "analysis": source_paths or ["建议补充行业主管部门、行业协会、评级机构与上市公司年报等资料。"],
        },
        {
            "title": "六、知识库来源",
            "sources": [
                {"title": _title(item["content"], item["file"]), "file": item["file"], "path": item["path"]}
                for item in guides
            ],
        },
    ]

    evidence = [
        {
            "label": "标准行业分类",
            "value": f"{industry.get('code')} {industry.get('name')}",
            "source": "国民经济行业分类四级代码表",
        },
        {
            "label": "行业知识库",
            "value": ", ".join(guide_files),
            "source": "本地行业尽调指南",
        },
    ]

    risk_summary = risks[:3]
    return {
        "report_type": "industry_analysis",
        "enterprise_name": enterprise_name,
        "generated_from": "行业代码库 + 本地行业知识库",
        "industry": industry,
        "sections": sections,
        "risk_summary": risk_summary,
        "evidence": evidence,
        "retrieval_result": retrieval_result,
    }
