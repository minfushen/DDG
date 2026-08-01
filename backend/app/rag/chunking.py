"""Shared RAG chunking primitives.

被年报 PDF 入库（``pdf_knowledge_ingestion``）和 Markdown 知识库入库
（``knowledge_ingestion``）共用，统一三条规则：

1. 原子表格保护：连续含 ``|`` 的行串整块保留，不允许跨表格行切分
   （JoyAgent ``or has_atomic`` 规则）。
2. 标题层级路径：chunk 元数据携带完整标题链（分号拼接），检索可按层级命中。
3. 小块合并：低于 ``MIN_CHUNK_CHARS`` 的块并入同 section 相邻块
   （JoyAgent ``merge_small_chunks`` 策略）。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


MIN_CHUNK_CHARS = 200

HeadingFn = Callable[[str], Optional[Dict[str, Any]]]


def split_into_blocks(text: str, heading_fn: HeadingFn) -> List[Dict[str, Any]]:
    """把文本切成块：表格行串保持原子（永不拆行），标题行单独标记。

    表格识别：连续 >=2 行包含 ``|`` 的行视为表格块（对齐 ``_table_to_text`` 的
    ``" | "`` 输出与 Markdown 表格）；单行含 ``|`` 的文本按普通段落处理，
    避免把正文里的管道符误判成表格。

    Args:
        text: 待切分文本（保留换行结构）。
        heading_fn: 单行标题识别函数，返回 ``{"level": int, "title": str}``
            或 None。PDF 链路用中文编号（（一）→ 1. → （1）），Markdown 链路用
            ``#`` / ``##`` / ``###``。
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: List[Dict[str, Any]] = []
    table: List[str] = []

    def flush_table() -> None:
        nonlocal table
        if table:
            if len(table) >= 2:
                blocks.append({"text": "\n".join(table), "atomic": True, "heading": None})
            else:
                blocks.append({"text": table[0], "atomic": False, "heading": heading_fn(table[0])})
            table = []

    for raw_line in normalized.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            flush_table()
            continue
        if "|" in stripped:
            table.append(stripped)
        else:
            flush_table()
            blocks.append({"text": stripped, "atomic": False, "heading": heading_fn(stripped)})
    flush_table()
    return blocks


def hard_split_text(text: str, max_chars: int, prefer_newline: bool = False) -> List[str]:
    """超长段落硬切（表格块不会走到这里，始终整块保留）。

    ``prefer_newline=True`` 时优先在 max_chars 前的换行处切分（Markdown 链路）。
    """
    pieces: List[str] = []
    remaining = text
    while len(remaining) > max_chars:
        end = max_chars
        if prefer_newline:
            split_at = remaining.rfind("\n", 0, max_chars)
            if split_at >= max_chars // 2:
                end = split_at
        pieces.append(remaining[:end])
        remaining = remaining[end:]
    if remaining:
        pieces.append(remaining)
    return pieces


def pack_blocks(
    blocks: List[Dict[str, Any]],
    max_chars: int,
    prefer_newline: bool = False,
) -> List[List[Dict[str, Any]]]:
    """按段落边界把块打包成不超过 max_chars 的 chunk 组。

    表格块（atomic）永远独占一个 chunk 且不参与硬切，即 JoyAgent 的
    ``or has_atomic`` 规则：含表格的文本块不允许跨表格行切分。
    """
    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            groups.append(current)
            current = []
            current_len = 0

    for block in blocks:
        block_len = len(block["text"])
        if block["atomic"]:
            flush()
            groups.append([block])
            continue
        if current and current_len + block_len + 1 > max_chars:
            flush()
        if block_len > max_chars:
            flush()
            for piece in hard_split_text(block["text"], max_chars, prefer_newline=prefer_newline):
                groups.append([{"text": piece, "atomic": False, "heading": None}])
        else:
            current.append(block)
            current_len += block_len + 1
    flush()
    return groups


def merge_small_chunks(chunks: List[str], min_chars: int = MIN_CHUNK_CHARS) -> List[str]:
    """把 <min_chars 的块合并到相邻块（同 section 内）。

    移植 JoyAgent ``merge_small_chunks`` 的策略：连续小块先合并为一组，
    再并入前一块；无前块时保留为独立块。
    """
    if not chunks:
        return chunks
    merged: List[str] = []
    i = 0
    while i < len(chunks):
        if len(chunks[i]) >= min_chars:
            merged.append(chunks[i])
            i += 1
            continue
        group: List[str] = []
        while i < len(chunks) and len(chunks[i]) < min_chars:
            group.append(chunks[i])
            i += 1
        group_text = "\n".join(group)
        if merged:
            merged[-1] = f"{merged[-1]}\n{group_text}"
        else:
            merged.append(group_text)
    return merged


def merge_small_chunk_dicts(
    chunks: List[Dict[str, Any]],
    min_chars: int = MIN_CHUNK_CHARS,
) -> List[Dict[str, Any]]:
    """带元数据版本的小块合并：并入前一块并保留其层级路径。"""
    if not chunks:
        return chunks
    merged: List[Dict[str, Any]] = []
    i = 0
    while i < len(chunks):
        if len(chunks[i]["text"]) >= min_chars:
            merged.append(chunks[i])
            i += 1
            continue
        group: List[Dict[str, Any]] = []
        while i < len(chunks) and len(chunks[i]["text"]) < min_chars:
            group.append(chunks[i])
            i += 1
        group_text = "\n".join(item["text"] for item in group)
        if merged:
            prev = merged[-1]
            merged[-1] = {
                "text": f"{prev['text']}\n{group_text}",
                "hierarchy_path": prev["hierarchy_path"],
                "chunk_type": prev["chunk_type"] if prev["chunk_type"] == group[0]["chunk_type"] else "mixed",
            }
        else:
            merged.append({
                "text": group_text,
                "hierarchy_path": group[0]["hierarchy_path"],
                "chunk_type": group[0]["chunk_type"],
            })
    return merged


def build_group_records(
    groups: List[List[Dict[str, Any]]],
    section_label: str = "",
    min_chars: int = MIN_CHUNK_CHARS,
) -> List[Dict[str, Any]]:
    """把打包后的块组转为 (text, hierarchy_path, chunk_type) 记录。

    ``hierarchy_path`` 记录组内出现的全部标题链（分号拼接），单块跨多个兄弟
    标题时也能全部命中；``section_label`` 非空时作为路径根节点（PDF 链路的
    section 名），Markdown 链路传空字符串（路径从首个 ``#`` 标题开始）。
    小块合并时保留前一 chunk 的路径。
    """
    path: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    prefix = [section_label] if section_label else []
    for group in groups:
        chains: List[str] = []
        current_path = list(path)
        for block in group:
            heading = block.get("heading")
            if heading:
                current_path = [p for p in current_path if p["level"] < heading["level"]] + [heading]
                chains.append(" > ".join(prefix + [p["title"] for p in current_path]))
        if not chains:
            chains = [" > ".join(prefix + [p["title"] for p in current_path])]
        group_text = "\n".join(block["text"] for block in group)
        results.append({
            "text": group_text,
            "hierarchy_path": "; ".join(chains),
            "chunk_type": "table" if any(block.get("atomic") for block in group) else "narrative",
        })
        path = current_path
    return merge_small_chunk_dicts(results, min_chars)
