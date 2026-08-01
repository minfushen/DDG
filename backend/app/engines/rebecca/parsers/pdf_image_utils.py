"""PDF 页面渲染与页码估算工具，供四阶段管道 Stage 2/4 视觉转录使用。"""

from __future__ import annotations

import base64
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


def render_pdf_pages(pdf_bytes: bytes, pages: List[int], dpi: int = 200) -> List[str]:
    """把 PDF 指定页渲染为 base64 PNG。

    Args:
        pdf_bytes: PDF 文件字节
        pages: 1-based 页码列表
        dpi: 渲染分辨率

    Returns:
        base64 编码的 PNG 图片列表
    """
    try:
        import fitz
    except ImportError as exc:
        raise ImportError("渲染 PDF 页面需要安装 PyMuPDF：pip install PyMuPDF") from exc

    images: List[str] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for page_num in pages:
            if page_num < 1 or page_num > len(doc):
                logger.warning("页码 %d 超出范围 [1, %d]", page_num, len(doc))
                continue
            page = doc.load_page(page_num - 1)
            pix = page.get_pixmap(matrix=mat)
            images.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
        doc.close()
    except Exception as exc:
        logger.warning("PDF 页面渲染失败: %s", exc)
    return images


def estimate_pages_by_text(text: str, keyword: str, total_pages: int, text_length: Optional[int] = None) -> List[int]:
    """根据关键词在全文中的位置估算页码。

    Args:
        text: 全文文本
        keyword: 关键词（如 "合并资产负债表"）
        total_pages: PDF 总页数
        text_length: 可选的文本总长度（用于提高估算精度）

    Returns:
        估算的 1-based 页码列表，最多返回 3 页
    """
    if not text or total_pages <= 0:
        return []

    total_len = text_length if text_length is not None else len(text)
    if total_len <= 0:
        return []

    idx = text.find(keyword)
    if idx == -1:
        return []

    # 根据关键词在全文中的相对位置估算页码
    ratio = idx / total_len
    estimated = max(1, min(total_pages, int(ratio * total_pages) + 1))

    # 返回关键词所在页及后两页（表格可能跨页）
    pages = []
    for offset in range(3):
        page = estimated + offset
        if page <= total_pages and page not in pages:
            pages.append(page)
    return pages


def estimate_pages_for_statement(text: str, keyword: str, total_pages: int) -> List[int]:
    """估算财务报表关键词所在的页码。

    优先查找 heading 形式的关键词，找不到再查找普通形式。
    """
    pages = estimate_pages_by_text(text, f"## {keyword}", total_pages)
    if pages:
        return pages
    return estimate_pages_by_text(text, keyword, total_pages)
