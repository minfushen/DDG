# ========================================
# 工具函数 — Markdown 表格解析
# 将 MinerU 返回的 markdown 表格转回 pdfplumber 风格的嵌套列表结构，
# 保持下游 extract_main_business_tables 等逻辑无需改动。
# ========================================

from __future__ import annotations

import re
from io import StringIO
from typing import List


def _split_table_row(row: str) -> List[str]:
    """按 `|` 拆分行并清理单元格空白。"""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def _is_table_delimiter(row: List[str]) -> bool:
    """判断是否为 markdown 表格的对齐分隔行，如 `|---|---|`。"""
    if not row:
        return False
    return all(re.match(r"^[\s\-:]+$", cell) for cell in row)


def extract_tables_from_markdown(text: str) -> List[List[List[str]]]:
    """从 markdown 文本中提取所有表格。

    返回结构与 pdfplumber `page.extract_tables()` 一致：
    `List[table]`，其中每个 table 是 `List[row]`，每个 row 是 `List[cell_str]`。
    """
    tables: List[List[List[str]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            table_lines: List[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            rows = [_split_table_row(r) for r in table_lines]
            rows = [r for r in rows if not _is_table_delimiter(r)]
            if len(rows) >= 2:  # 至少包含表头和一行数据
                tables.append(rows)
            continue
        i += 1
    return tables


def extract_tables_from_html(text: str) -> List[List[List[str]]]:
    """从 HTML `<table>` 标签中提取所有表格。

    MinerU 对复杂表格常输出 HTML 标签，需要额外解析以保持下游兼容。
    依赖 pandas + lxml/html5lib（项目已包含）。
    """
    if "<table" not in text.lower():
        return []

    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return []

    tables: List[List[List[str]]] = []
    try:
        dfs = pd.read_html(StringIO(text))
        for df in dfs:
            table = []
            for _, row in df.iterrows():
                table.append([str(cell) if pd.notna(cell) else "" for cell in row])
            if table:
                tables.append(table)
    except Exception:
        # HTML 表格不完整或解析失败时静默忽略，避免阻塞主流程。
        pass
    return tables


def extract_tables(text: str) -> List[List[List[str]]]:
    """从 markdown 或 HTML 混合格式文本中提取所有表格。"""
    return extract_tables_from_markdown(text) + extract_tables_from_html(text)
