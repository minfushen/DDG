"""模板驱动的报告渲染。

把用户上传并解析好的模板，绑定到已经由各专项 Agent 生成的子报告（sub_reports）与
计算指标（indicators）上，产出「按模板章节顺序组织、在指定位置填指标/写解读」的报告结构。

设计原则：
- 不重复调用大模型，所有绑定都可确定性回溯（便于测试与人工核验）；
- 指标/解读若暂无可绑定数据，明确标记为「待补充 / AI 解读位置」，而非静默丢失。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.template.models import BlockType, ReportTemplate

_VALUE_RE = re.compile(r"([\d][\d,\.]*\d?)\s*(亿元|万元|千元|元|%|％)?")


def _subreport_chapters(sub_report: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从形态各异的子报告中抽取 (title, analysis[]) 章节列表。"""
    if not sub_report or not isinstance(sub_report, dict):
        return []
    if sub_report.get("report_chapters"):
        return sub_report["report_chapters"]
    if sub_report.get("sections"):
        return sub_report["sections"]
    if sub_report.get("report_sections"):
        return sub_report["report_sections"]
    # 退化：用关键摘要字段拼一章
    parts: List[str] = []
    for key in ("recommendation", "conclusion", "executive_summary"):
        val = sub_report.get(key)
        if isinstance(val, list):
            parts.extend(str(v) for v in val)
        elif val:
            parts.append(str(val))
    rs = sub_report.get("risk_summary")
    if isinstance(rs, list):
        parts.extend(str(v) for v in rs)
    if parts:
        return [{"title": sub_report.get("title") or "专项结论", "analysis": parts}]
    return []


def _find_indicator_in_text(label: str, text: str) -> Optional[str]:
    """在子报告文本里按「指标名 + 数字」粗略抽取指标值。"""
    idx = text.find(label)
    if idx < 0:
        return None
    window = text[idx: idx + 120]
    m = _VALUE_RE.search(window)
    return f"{m.group(1)}{m.group(2) or ''}" if m else None


def _lookup_indicator(block, indicators: Dict[str, Any], sub_reports: Dict[str, Any]) -> str:
    key = block.key or block.label or ""
    if indicators and key in indicators and indicators[key] not in (None, ""):
        return str(indicators[key])
    # 退而在财务子报告文本里找
    fin = sub_reports.get("financial") or {}
    text = " ".join(
        " ".join(str(a) for a in ch.get("analysis", []))
        for ch in _subreport_chapters(fin)
    )
    found = _find_indicator_in_text(key, text)
    if found:
        return found + (f" {block.unit}" if block.unit else "")
    return "待补充"


def _interpretation_for(block, sub_reports: Dict[str, Any], overall_summary: Optional[List[str]]) -> str:
    dim = block.source_dimension or block.key
    if dim and dim in sub_reports:
        sr = sub_reports[dim] or {}
        rec = sr.get("recommendation")
        if rec:
            return str(rec)
        rs = sr.get("risk_summary")
        if isinstance(rs, list) and rs:
            return str(rs[0])
        chapters = _subreport_chapters(sr)
        if chapters and chapters[0].get("analysis"):
            return str(chapters[0]["analysis"][0])
    if overall_summary:
        return overall_summary[0]
    return "（AI 解读位置：由系统在生成报告时基于专项结论填充）"


def render_report_from_template(
    template: ReportTemplate,
    sub_reports: Dict[str, Any],
    indicators: Optional[Dict[str, Any]] = None,
    overall_summary: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """按模板结构渲染报告章节。返回可直接嵌入最终报告的 ``template_sections``。"""
    sections_out: List[Dict[str, Any]] = []
    for sec in template.sections:
        content: List[Dict[str, Any]] = []
        for b in sec.blocks:
            if b.type == BlockType.NARRATIVE:
                content.append({"type": "narrative", "text": b.text or ""})
            elif b.type == BlockType.INDICATOR:
                content.append({
                    "type": "indicator",
                    "label": b.label or b.key,
                    "unit": b.unit,
                    "value": _lookup_indicator(b, indicators or {}, sub_reports),
                })
            elif b.type == BlockType.INTERPRETATION:
                content.append({
                    "type": "interpretation",
                    "label": b.label or b.key,
                    "text": _interpretation_for(b, sub_reports, overall_summary),
                })
            elif b.type == BlockType.SUBREPORT:
                dim = b.source_dimension or b.key
                chapters = _subreport_chapters(sub_reports.get(dim))
                content.append({
                    "type": "subreport",
                    "dimension": dim,
                    "label": b.label or dim,
                    "chapters": chapters,
                })
        sections_out.append({
            "id": sec.id,
            "title": sec.title,
            "level": sec.level,
            "content": content,
        })
    return sections_out
