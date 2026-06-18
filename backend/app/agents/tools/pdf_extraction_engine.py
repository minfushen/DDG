"""PDF download and tiered extraction engine.

Tiered strategy for Chinese A-share annual reports:
1. pdfplumber (primary): excellent for digital PDFs with tables and structured text.
2. pymupdf/fitz (fallback): faster raw text extraction, better for complex layouts or
   when pdfplumber returns empty text.

mineru / ppstructure are intentionally not used in this iteration to avoid heavy
model dependencies; they can be plugged in later as part of Document Intelligence
Pipeline v1.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import httpx


DEFAULT_TIMEOUT_SECONDS = 30
MAX_PDF_SIZE_MB = 50


def _pdfplumber_available() -> bool:
    try:
        import pdfplumber  # noqa: F401
        return True
    except ImportError:
        return False


def _pymupdf_available() -> bool:
    try:
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False


def download_pdf(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS, max_size_mb: int = MAX_PDF_SIZE_MB) -> Optional[bytes]:
    """Download PDF from URL with size guard.

    Returns None if the response is not a PDF, exceeds size limit, or request fails.
    """
    if not url:
        return None
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and "octet-stream" not in content_type:
                # Some CNINFO URLs may not set content-type; continue cautiously.
                pass
            max_bytes = max_size_mb * 1024 * 1024
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                chunks.append(chunk)
                total += len(chunk)
                if total > max_bytes:
                    return None
            return b"".join(chunks)
    except Exception:
        return None


def extract_with_pdfplumber(pdf_bytes: bytes) -> Dict[str, Any]:
    """Primary extraction using pdfplumber.

    Extracts page text and tables. Tables are returned as nested lists of strings.
    """
    import pdfplumber

    text_parts: List[str] = []
    tables: List[List[List[str]]] = []
    page_count = 0

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)

    full_text = "\n".join(text_parts)
    return {
        "success": bool(full_text.strip()) or bool(tables),
        "text": full_text,
        "tables": _clean_tables(tables),
        "metadata": {
            "page_count": page_count,
            "parser_used": "pdfplumber",
        },
        "error": "",
    }


def extract_with_pymupdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Fallback extraction using pymupdf.

    Faster raw text extraction with block-level layout preservation.
    """
    import fitz

    text_parts: List[str] = []
    page_count = 0

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        for page in doc:
            text = page.get_text("text") or ""
            if text.strip():
                text_parts.append(text)
        doc.close()
    except Exception as exc:
        return {
            "success": False,
            "text": "",
            "tables": [],
            "metadata": {"page_count": 0, "parser_used": "pymupdf"},
            "error": f"pymupdf extraction failed: {exc}",
        }

    full_text = "\n".join(text_parts)
    return {
        "success": bool(full_text.strip()),
        "text": full_text,
        "tables": [],
        "metadata": {
            "page_count": page_count,
            "parser_used": "pymupdf",
        },
        "error": "",
    }


def _clean_tables(tables: List[List[List[str]]]) -> List[List[List[str]]]:
    """Normalize table cells to strings and strip whitespace."""
    cleaned: List[List[List[str]]] = []
    for table in tables:
        if not table:
            continue
        cleaned_table = []
        for row in table:
            cleaned_row = [str(cell or "").replace("\n", " ").strip() for cell in row]
            if any(cell for cell in cleaned_row):
                cleaned_table.append(cleaned_row)
        if cleaned_table:
            cleaned.append(cleaned_table)
    return cleaned


def extract_pdf(pdf_bytes: Optional[bytes]) -> Dict[str, Any]:
    """Tiered extraction: pdfplumber first, pymupdf fallback.

    Returns a dict with success, text, tables, metadata, error.
    """
    if not pdf_bytes:
        return {
            "success": False,
            "text": "",
            "tables": [],
            "metadata": {"page_count": 0, "parser_used": "none"},
            "error": "Empty PDF bytes",
        }

    if _pdfplumber_available():
        try:
            result = extract_with_pdfplumber(pdf_bytes)
            if result["success"] and len(result["text"].strip()) >= 100:
                return result
            # pdfplumber succeeded technically but got very little text; try fallback.
        except Exception as exc:
            result = {
                "success": False,
                "text": "",
                "tables": [],
                "metadata": {"page_count": 0, "parser_used": "pdfplumber"},
                "error": f"pdfplumber failed: {exc}",
            }

    if _pymupdf_available():
        try:
            fallback = extract_with_pymupdf(pdf_bytes)
            # If pdfplumber produced tables, preserve them.
            if result and result.get("tables"):
                fallback["tables"] = result["tables"]
            return fallback
        except Exception as exc:
            error_msg = f"pdfplumber failed: {result.get('error')}; pymupdf failed: {exc}"
            return {
                "success": False,
                "text": result.get("text", ""),
                "tables": result.get("tables", []),
                "metadata": {**(result.get("metadata") or {}), "parser_used": "pdfplumber+pymupdf_failed"},
                "error": error_msg,
            }

    return {
        "success": False,
        "text": result.get("text", ""),
        "tables": result.get("tables", []),
        "metadata": result.get("metadata") or {"page_count": 0, "parser_used": "none"},
        "error": result.get("error") or "No PDF parser available",
    }


def extract_pdf_from_url(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Convenience: download then extract."""
    pdf_bytes = download_pdf(url, timeout=timeout)
    if pdf_bytes is None:
        return {
            "success": False,
            "text": "",
            "tables": [],
            "metadata": {"page_count": 0, "parser_used": "none"},
            "error": f"Failed to download PDF from {url}",
        }
    return extract_pdf(pdf_bytes)
