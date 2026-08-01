"""尽调模板解析器。

支持两种上传格式：
- ``markdown``：直接使用标题层级（# / ## / ###）作为章节，正文中的占位标记定义指标/解读/子报告。
- ``docx``：用 python-docx 抽取标题与段落，转换为伪 Markdown 后复用同一套解析逻辑。

占位标记语法（indicator/interpret/subreport 的中英文别名均可）：
- 指标：``{{指标:营业收入}}`` / ``{{indicator:营业收入|单位:万元}}``
- 解读位置：``{{解读:财务健康度}}`` / ``{{interpret:财务健康度@financial}}``
- 子报告嵌入：``{{子报告:financial}}`` / ``{{subreport:industry}}``
- 指标表：表格首列含「指标/indicator」时，其余数据行按指标占位解析（第二列作为单位）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from .models import BlockType, ReportTemplate, TemplateBlock, TemplateSection

# ── 占位标记 ──────────────────────────────────────────────────────────────
_ALIAS = {
    "indicator": "indicator", "指标": "indicator",
    "interpret": "interpretation", "解读": "interpretation",
    "subreport": "subreport", "子报告": "subreport",
}

_SLOT_RE = re.compile(
    r"\{\{\s*(?P<kind>指标|indicator|解读|interpret|子报告|subreport)"
    r"\s*:\s*(?P<body>[^}]*?)\s*\}\}",
    re.IGNORECASE,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*#*\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_DIM_RE = re.compile(r"@\s*([a-z_]+)", re.IGNORECASE)
_UNIT_RE = re.compile(r"单位\s*[:：]\s*([^\|\n]+)")


def _split_slot_body(body: str) -> Tuple[str, Optional[str], Optional[str]]:
    """把标记体拆成 (key, unit, source_dimension)。

    形如 ``营业收入|单位:万元@financial`` 或 ``财务健康度@financial``。
    """
    key = body.strip()
    unit: Optional[str] = None
    dim: Optional[str] = None
    if "|" in key:
        key, rest = key.split("|", 1)
        m = _UNIT_RE.search(rest)
        if m:
            unit = m.group(1).strip()
    key = key.strip()
    m = _DIM_RE.search(key)
    if m:
        dim = m.group(1).strip().lower()
        key = _DIM_RE.sub("", key).strip(" -@")
    return key, unit, dim


def _parse_slot(line: str) -> Optional[TemplateBlock]:
    """若整行是单个占位标记，返回对应块；否则返回 None。"""
    stripped = line.strip()
    m = _SLOT_RE.search(stripped)
    if not m:
        return None
    remainder = _SLOT_RE.sub("", stripped).strip(" :：")
    if remainder != "":
        return None
    kind = _ALIAS[m.group("kind").lower()]
    key, unit, dim = _split_slot_body(m.group("body"))
    if kind == "indicator":
        return TemplateBlock(type=BlockType.INDICATOR, key=key, label=key, unit=unit)
    if kind == "interpretation":
        return TemplateBlock(type=BlockType.INTERPRETATION, key=key, label=key, source_dimension=dim)
    return TemplateBlock(type=BlockType.SUBREPORT, key=key, label=key, source_dimension=key)


def _table_cells(line: str) -> List[str]:
    cells = [c.strip() for c in _TABLE_ROW_RE.pattern and line.strip().strip("|").split("|")]
    return [c for c in cells if c != ""]


def _is_separator_row(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:-]+\|", line)) and set(line.replace("|", "").replace(" ", "")) <= set("-:")


def _parse_table_block(rows: List[str]) -> List[TemplateBlock]:
    """解析一组连续的表格行。

    - 若表头首格为「指标/indicator」，数据行解析为指标占位（第二列单位）；
    - 否则整张表作为静态指引（narrative）保留原始文本。
    """
    # 去掉分隔行
    data_rows = [r for r in rows if not _is_separator_row(r)]
    if not data_rows:
        return []
    header_cells = _table_cells(data_rows[0])
    is_indicator_table = bool(header_cells) and header_cells[0] in ("指标", "indicator", "指标名")
    if is_indicator_table and len(data_rows) > 1:
        blocks: List[TemplateBlock] = []
        for row in data_rows[1:]:
            cells = _table_cells(row)
            if not cells:
                continue
            key = cells[0]
            unit = cells[1] if len(cells) > 1 else None
            blocks.append(TemplateBlock(type=BlockType.INDICATOR, key=key, label=key, unit=unit))
        return blocks
    # 普通表格：保留为静态文本
    return [TemplateBlock(type=BlockType.NARRATIVE, text="\n".join(rows))]


def _parse_section_lines(lines: List[str]) -> List[TemplateBlock]:
    blocks: List[TemplateBlock] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if _HEADING_RE.match(stripped):
            i += 1
            continue
        # 表格组
        if _TABLE_ROW_RE.match(stripped):
            j = i
            while j < n and _TABLE_ROW_RE.match(lines[j].strip()):
                j += 1
            blocks.extend(_parse_table_block([lines[k] for k in range(i, j)]))
            i = j
            continue
        # 占位标记
        slot = _parse_slot(stripped)
        if slot is not None:
            blocks.append(slot)
            i += 1
            continue
        # 静态指引
        blocks.append(TemplateBlock(type=BlockType.NARRATIVE, text=stripped))
        i += 1
    return blocks


def parse_markdown(text: str, name: str, description: Optional[str] = None,
                   filename: Optional[str] = None) -> ReportTemplate:
    """解析 Markdown 模板文本为 ReportTemplate。"""
    sections: List[TemplateSection] = []
    current: Optional[TemplateSection] = None
    buf: List[str] = []

    def flush() -> None:
        nonlocal current, buf
        if current is not None:
            current.blocks = _parse_section_lines(buf)
            if current.blocks or current.title:
                sections.append(current)
        buf = []

    for raw in text.splitlines():
        line = raw.rstrip("\n")
        hm = _HEADING_RE.match(line.strip())
        if hm:
            flush()
            level = len(hm.group(1))
            current = TemplateSection(id=f"sec_{len(sections)+1}", title=hm.group("title").strip(), level=level)
            buf = []
        else:
            if current is None:
                current = TemplateSection(id="sec_0", title="概述", level=1)
            buf.append(line)

    flush()
    if not sections:
        sections.append(TemplateSection(
            id="sec_1", title=name or "自定义尽调模板", level=1,
            blocks=_parse_section_lines(text.splitlines()),
        ))
    return ReportTemplate(
        id="",
        name=name or "未命名模板",
        description=description,
        source_format="markdown",
        filename=filename,
        sections=sections,
    )


def parse_docx(path: Path, name: str, description: Optional[str] = None) -> ReportTemplate:
    """解析 DOCX 模板。优先用 python-docx；不可用时抛清晰错误。"""
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:  # pragma: no cover - 依赖可选
        raise RuntimeError(
            "解析 DOCX 需要 python-docx；请先 `pip install python-docx`，或改用 Markdown 模板上传。"
        ) from exc

    doc = Document(str(path))
    md_lines: List[str] = []
    for para in doc.paragraphs:
        text = (para.text or "").strip()
        style = (para.style.name or "") if para.style else ""
        if style.startswith("Heading") or style.startswith("标题"):
            level = 1
            if style[-1].isdigit():
                level = max(1, min(6, int(style[-1])))
            md_lines.append(f"{'#' * level} {text}")
        elif text:
            md_lines.append(text)
    return parse_markdown("\n".join(md_lines), name, description, filename=path.name)


def parse_template_file(path: Path, name: str, description: Optional[str] = None) -> ReportTemplate:
    """按扩展名分派解析器。"""
    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown", ".txt"):
        return parse_markdown(path.read_text(encoding="utf-8"), name, description, filename=path.name)
    if suffix in (".docx", ".doc"):
        return parse_docx(path, name, description)
    raise ValueError(f"不支持的模板格式：{suffix}（仅支持 .md/.markdown/.txt/.docx）")
