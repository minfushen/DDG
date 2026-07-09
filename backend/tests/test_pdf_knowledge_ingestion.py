from app.rag.collection_names import company_collection_name, GENERAL_COLLECTION
from app.rag.pdf_knowledge_ingestion import (
    build_documents_from_pdf_extraction,
    ingest_company_documents,
    _chunk_text,
)
from app.rag.pdf_knowledge_ingestion import Document


def test_company_collection_name_normalization():
    # Chinese names are normalized to a stable hash suffix to satisfy Chroma's
    # [a-zA-Z0-9._-] name restriction.
    assert company_collection_name("三安光电").startswith("ddg_kb_company_")
    assert len(company_collection_name("三安光电")) <= 63
    assert company_collection_name("三安光电") == company_collection_name("三安光电")
    assert company_collection_name("三安光电") != company_collection_name("贵州茅台")

    assert company_collection_name("ABC Corp., Ltd.") == "ddg_kb_company_ABC_Corp_Ltd"
    assert company_collection_name("  ") == "ddg_kb_company_unknown_company"
    assert len(company_collection_name("x" * 100)) <= 63


def test_chunk_text_splits_on_paragraphs():
    text = "\n".join([f"段落{i}" * 50 for i in range(3)])
    chunks = _chunk_text(text, max_chars=200)
    assert len(chunks) >= 2


def test_build_documents_from_pdf_extraction_annual_report():
    extraction_result = {
        "text": "2025年年度报告。",
        "tables": [[["产品", "收入"], ["A", "100"]]],
        "metadata": {"parser_used": "pdfplumber"},
    }
    sections = {
        "business_review": "第三节 经营情况讨论与分析\n公司主营半导体。",
        "audit_opinion": "标准无保留意见。",
    }
    main_business_rows = [{"item_name": "产品A", "income": "100", "income_ratio": "50%", "gross_margin": "30%"}]

    docs = build_documents_from_pdf_extraction(
        enterprise_name="测试公司",
        doc_type="annual_report",
        source_url="https://example.com/ar.pdf",
        title="2025年年度报告",
        extraction_result=extraction_result,
        sections=sections,
        main_business_rows=main_business_rows,
        published_at="2026-04-28",
        announcement_id="12345",
    )

    assert len(docs) >= 3  # business_review, audit_opinion, table
    section_names = {doc.metadata["section"] for doc in docs}
    assert "business_review" in section_names
    assert "audit_opinion" in section_names
    assert "main_business_composition_table" in section_names
    for doc in docs:
        assert doc.metadata["enterprise_name"] == "测试公司"
        assert doc.metadata["category"] == "annual_report"
        assert doc.metadata["source"] == "https://example.com/ar.pdf"
        assert doc.metadata["id"].startswith("pdf_")


def test_build_documents_from_pdf_extraction_research_report():
    extraction_result = {
        "text": "研报摘要：行业景气回升。\n" * 20,
        "tables": [],
        "metadata": {"parser_used": "pymupdf"},
    }
    docs = build_documents_from_pdf_extraction(
        enterprise_name="测试公司",
        doc_type="research_report",
        source_url="https://example.com/report.pdf",
        title="半导体行业研报",
        extraction_result=extraction_result,
        sections={},
    )
    assert len(docs) >= 1
    assert all(doc.metadata["category"] == "research_report" for doc in docs)
    assert any(doc.metadata["section"] == "full_text" for doc in docs)


def test_ingest_company_documents_empty():
    result = ingest_company_documents("测试公司", [])
    assert result["success"] is True
    assert result["document_count"] == 0


def test_ingest_company_documents_mocked(monkeypatch):
    called = {}

    class FakeVectorstore:
        def add_documents(self, documents, ids=None):
            called["documents"] = documents
            called["ids"] = ids

    class FakeManager:
        def __init__(self, *args, **kwargs):
            called["manager_kwargs"] = kwargs

        def get_vectorstore(self):
            return FakeVectorstore()

    monkeypatch.setattr("app.rag.pdf_knowledge_ingestion.VectorStoreManager", FakeManager)
    monkeypatch.setattr("app.config.embedding_config.get_embedding_model", lambda: None)

    docs = [Document(page_content="test", metadata={"id": "pdf_123"})]
    result = ingest_company_documents("测试公司", docs)

    assert result["success"] is True
    assert result["collection_name"].startswith("ddg_kb_company_")
    assert called["manager_kwargs"]["collection_name"] == result["collection_name"]
    assert called["documents"] == docs
    assert called["ids"] == ["pdf_123"]
