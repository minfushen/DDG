"""Lightweight research report PDF extractor.

Research reports do not follow the standard annual report section structure, so this
module only downloads and extracts raw text, then delegates chunking to the shared
PDF knowledge ingestion pipeline.
"""

from __future__ import annotations

from typing import Any, Dict

from app.agents.tools.pdf_extraction_engine import extract_pdf_from_url


def extract_research_report_from_url(url: str, title: str = "研报") -> Dict[str, Any]:
    """Download and extract a research report PDF.

    Returns a dict compatible with build_documents_from_pdf_extraction.
    """
    result = extract_pdf_from_url(url)
    if not result.get("success"):
        return {
            "success": False,
            "pdf_url": url,
            "title": title,
            "extraction_result": result,
            "sections": {},
            "main_business_rows": [],
            "error": result.get("error") or "PDF extraction failed",
        }
    return {
        "success": True,
        "pdf_url": url,
        "title": title,
        "extraction_result": result,
        "sections": {},
        "main_business_rows": [],
        "error": "",
    }
