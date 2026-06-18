#!/usr/bin/env python3
"""Batch ingest company annual report / research report PDFs into per-company Chroma collections.

Usage:
    ./venv/bin/python scripts/ingest_company_pdf_knowledge.py \
        --enterprise-name "三安光电" \
        --pdf-urls "https://static.cninfo.com.cn/...pdf" \
        --doc-types "annual_report"

    ./venv/bin/python scripts/ingest_company_pdf_knowledge.py \
        --enterprise-name "三安光电" \
        --pdf-urls "https://.../report1.pdf" "https://.../report2.pdf" \
        --doc-types "research_report" "research_report"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List


# Make app imports work when running from scripts/ directory.
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


from app.agents.tools.annual_report_section_extractor import (
    extract_all_sections,
    extract_main_business_tables,
)
from app.agents.tools.cninfo_announcement_tool import fetch_and_extract_annual_report_pdf, normalize_cninfo_announcement
from app.agents.tools.research_report_tool import extract_research_report_from_url
from app.rag.pdf_knowledge_ingestion import (
    build_documents_from_pdf_extraction,
    ingest_company_documents,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest company PDFs into per-company Chroma collections")
    parser.add_argument("--enterprise-name", required=True, help="Company name (used for collection isolation)")
    parser.add_argument("--pdf-urls", nargs="+", required=True, help="List of PDF URLs")
    parser.add_argument("--doc-types", nargs="+", help="Doc type for each URL: annual_report | research_report | announcement")
    parser.add_argument("--titles", nargs="+", help="Optional title for each URL")
    parser.add_argument("--persist-dir", default=None, help="Optional Chroma persist directory")
    return parser.parse_args()


def _resolve_doc_types(urls: List[str], doc_types: List[str] | None) -> List[str]:
    if not doc_types:
        return ["annual_report"] * len(urls)
    if len(doc_types) != len(urls):
        raise ValueError("--doc-types must have the same number of items as --pdf-urls")
    return doc_types


def _resolve_titles(urls: List[str], titles: List[str] | None, doc_types: List[str]) -> List[str]:
    if not titles:
        return [f"{doc_type}_{index + 1}" for index, doc_type in enumerate(doc_types)]
    if len(titles) != len(urls):
        raise ValueError("--titles must have the same number of items as --pdf-urls")
    return titles


def _extract_pdf(doc_type: str, url: str, title: str) -> Dict[str, Any]:
    if doc_type == "annual_report":
        # Treat the URL as a CNINFO annual report announcement.
        item = normalize_cninfo_announcement({
            "announcementTitle": title,
            "adjunctUrl": url,
            "announcementId": "",
        })
        return fetch_and_extract_annual_report_pdf(item)
    if doc_type == "research_report":
        return extract_research_report_from_url(url, title=title)
    # Generic announcement: no section extraction, full text only.
    from app.agents.tools.pdf_extraction_engine import extract_pdf_from_url
    result = extract_pdf_from_url(url)
    return {
        "success": result.get("success", False),
        "pdf_url": url,
        "title": title,
        "extraction_result": result,
        "sections": {},
        "main_business_rows": [],
        "error": result.get("error", ""),
    }


def main() -> None:
    args = _parse_args()
    enterprise_name = args.enterprise_name
    urls = args.pdf_urls
    doc_types = _resolve_doc_types(urls, args.doc_types)
    titles = _resolve_titles(urls, args.titles, doc_types)

    all_documents: List[Any] = []
    summary: List[Dict[str, Any]] = []

    for url, doc_type, title in zip(urls, doc_types, titles):
        print(f"Processing {doc_type}: {url}")
        extraction = _extract_pdf(doc_type, url, title)
        if not extraction.get("success"):
            print(f"  Failed: {extraction.get('error')}")
            summary.append({"url": url, "doc_type": doc_type, "success": False, "error": extraction.get("error")})
            continue

        documents = build_documents_from_pdf_extraction(
            enterprise_name=enterprise_name,
            doc_type=doc_type,
            source_url=url,
            title=title,
            extraction_result=extraction.get("extraction_result") or {},
            sections=extraction.get("sections") or {},
            main_business_rows=extraction.get("main_business_rows") or [],
        )
        all_documents.extend(documents)
        print(f"  Generated {len(documents)} chunks")
        summary.append({"url": url, "doc_type": doc_type, "success": True, "chunks": len(documents)})

    if not all_documents:
        print("No documents to ingest.")
        for item in summary:
            print(item)
        return

    result = ingest_company_documents(
        enterprise_name=enterprise_name,
        documents=all_documents,
        persist_dir=args.persist_dir,
    )
    print(f"Ingested {result['document_count']} documents into collection {result['collection_name']}")
    for item in summary:
        print(item)


if __name__ == "__main__":
    main()
