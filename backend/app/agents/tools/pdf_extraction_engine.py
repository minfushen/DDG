"""PDF download and tiered extraction engine.

Tiered strategy for Chinese A-share annual reports:
1. MinerU cloud API (primary when enabled): structured markdown + table extraction,
   best for complex layouts, tables, and scanned pages.
2. pdfplumber (local primary): excellent for digital PDFs with tables and structured text.
3. pymupdf/fitz (local fallback): faster raw text extraction, better for complex layouts or
   when pdfplumber returns empty text.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings


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


def _mineru_enabled() -> bool:
    """Return True if MinerU cloud parser is configured and enabled."""
    return settings.MINERU_ENABLED and bool(settings.MINERU_API_TOKEN)


def _mineru_available() -> bool:
    """Return True if the MinerU client module can be imported."""
    try:
        from app.services.mineru_client import extract_local_pdf  # noqa: F401
        return True
    except ImportError:
        return False





def extract_with_mineru(pdf_bytes: bytes) -> Dict[str, Any]:
    """Extract PDF using MinerU cloud API with automatic page splitting.

    PDFs with more than MINERU_MAX_PAGES_PER_TASK pages are split locally using
    pymupdf, submitted as separate tasks, and merged back in page order.
    """
    from app.services.mineru_client import MinerUError, extract_pdf_bytes

    try:
        return extract_pdf_bytes(pdf_bytes)
    except MinerUError as exc:
        return {
            "success": False,
            "text": "",
            "tables": [],
            "metadata": {"page_count": 0, "parser_used": "mineru"},
            "error": f"MinerU failed: {exc}",
        }
    except Exception as exc:
        return {
            "success": False,
            "text": "",
            "tables": [],
            "metadata": {"page_count": 0, "parser_used": "mineru"},
            "error": f"MinerU unexpected error: {exc}",
        }


def download_pdf(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS, max_size_mb: int = MAX_PDF_SIZE_MB) -> Optional[bytes]:
    """Download PDF from URL with size guard.

    优先 curl（巨潮 PDF 下载 httpx 常 SSL EOF），httpx 兜底。
    Returns None if the response is not a PDF, exceeds size limit, or request fails.
    """
    if not url:
        return None
    max_bytes = max_size_mb * 1024 * 1024

    # ── curl 优先（cninfo/巨潮 SSL 兼容性更好） ──
    try:
        import subprocess, tempfile, os as _os
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as _tf:
            _tmp = _tf.name
        try:
            _proc = subprocess.run(
                ["curl", "-sSL", "-o", _tmp, "--max-time", str(timeout), "--max-filesize", str(max_bytes), url],
                capture_output=True, text=True, timeout=timeout + 5,
            )
            if _proc.returncode == 0:
                with open(_tmp, "rb") as _f:
                    data = _f.read()
                if len(data) >= 4 and data[:4] == b"%PDF":
                    return data
        finally:
            try:
                _os.unlink(_tmp)
            except OSError:
                pass
    except Exception:
        pass

    # ── httpx 兜底 ──
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and "octet-stream" not in content_type:
                # Some CNINFO URLs may not set content-type; continue cautiously.
                pass
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
    """Tiered extraction: MinerU first (if enabled), then pdfplumber, then pymupdf.

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

    # 1. Try MinerU cloud parser first when configured.
    if _mineru_enabled() and _mineru_available():
        try:
            mineru_result = extract_with_mineru(pdf_bytes)
            if mineru_result.get("success"):
                return mineru_result
            # MinerU returned an error object; fall through to local parsers.
        except Exception as exc:
            # Import or unexpected failure; fall through to local parsers.
            pass

    # 2. Local tiered extraction.
    result = None
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
            prev_error = (result or {}).get("error") or "pdfplumber not available"
            error_msg = f"pdfplumber failed: {prev_error}; pymupdf failed: {exc}"
            return {
                "success": False,
                "text": (result or {}).get("text", ""),
                "tables": (result or {}).get("tables", []),
                "metadata": {**((result or {}).get("metadata") or {}), "parser_used": "pdfplumber+pymupdf_failed"},
                "error": error_msg,
            }

    return {
        "success": False,
        "text": (result or {}).get("text", ""),
        "tables": (result or {}).get("tables", []),
        "metadata": (result or {}).get("metadata") or {"page_count": 0, "parser_used": "none"},
        "error": (result or {}).get("error") or "No PDF parser available",
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
