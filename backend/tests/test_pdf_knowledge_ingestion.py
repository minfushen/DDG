from app.rag.collection_names import company_collection_name, GENERAL_COLLECTION
from app.rag.pdf_knowledge_ingestion import (
    build_documents_from_pdf_extraction,
    build_documents_from_pipeline_result,
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
    # 每段 300 字符，超过 max_chars=200，按段落边界拆成多块（不低于 min 阈值，不合并）
    text = "\n".join([f"段落{i}" * 100 for i in range(3)])
    chunks = _chunk_text(text, max_chars=200)
    assert len(chunks) >= 2


def test_chunk_text_merges_small_fragments():
    big = "财务分析。" * 100  # 500 字符
    small = "补充说明。"      # 5 字符
    chunks = _chunk_text(f"{big}\n{small}", max_chars=200)
    # 硬切产生 200/200/100 三块，100 字符的尾巴和小片段都应并入前块
    assert len(chunks) == 2
    assert "补充说明" in chunks[-1]
    assert all(len(chunk) >= 5 for chunk in chunks)


def test_chunk_text_keeps_table_block_atomic():
    rows = ["产品 | 收入 | 毛利率", "产品A | 100 | 30%", "产品B | 200 | 40%"]
    text = "主营构成如下：\n" + "\n".join(rows) + "\n以上为明细。"
    chunks = _chunk_text(text, max_chars=200)
    table_text = "\n".join(rows)
    # 表格行必须整块保留，不允许跨行切分
    assert any(table_text in chunk for chunk in chunks)
    assert all("产品B | 200 | 40%" in chunk for chunk in chunks if "产品A | 100" in chunk)


def test_chunk_text_keeps_oversized_table_whole():
    rows = [f"科目{i} | 2025年 | 2024年 | 备注{i}" for i in range(30)]
    text = "\n".join(rows)
    chunks = _chunk_text(text, max_chars=200)
    # 超过 max_chars 的表格仍整块保留（JoyAgent or has_atomic 规则）
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_respects_paragraph_boundaries():
    text = "\n".join(f"第{i}段" * 80 for i in range(4))  # 每段 240 字符
    chunks = _chunk_text(text, max_chars=300)
    assert len(chunks) == 4
    assert all(chunk.startswith("第") and chunk.endswith("段") for chunk in chunks)


def test_section_chunks_carry_hierarchy_path():
    sections = {
        "financial_notes": (
            "（一）重要会计政策\n"
            "1. 收入确认\n"
            "（1）坏账准备计提方法\n"
            "公司按预期信用损失模型计提坏账准备。\n"
            "2. 存货计价\n"
            "存货按加权平均法计价。"
        ),
    }
    docs = build_documents_from_pdf_extraction(
        enterprise_name="测试公司",
        doc_type="annual_report",
        source_url="https://example.com/ar.pdf",
        title="2025年年度报告",
        extraction_result={"text": "", "tables": [], "metadata": {"parser_used": "pdfplumber"}},
        sections=sections,
    )

    notes_docs = [doc for doc in docs if doc.metadata["section"] == "financial_notes"]
    assert len(notes_docs) == 1
    assert notes_docs[0].metadata["hierarchy_path"].startswith("financial_notes")
    assert "（一）重要会计政策" in notes_docs[0].metadata["hierarchy_path"]
    # 单块内出现多条标题链时应全部写入（分号拼接），保证"坏账准备计提方法"可命中
    assert "（一）重要会计政策 > 1. 收入确认 > （1）坏账准备计提方法" in notes_docs[0].metadata["hierarchy_path"]
    assert "（一）重要会计政策 > 2. 存货计价" in notes_docs[0].metadata["hierarchy_path"]
    assert notes_docs[0].metadata["chunk_type"] == "narrative"
    assert notes_docs[0].metadata["chunk_index"] == 0


def test_chunk_paths_follow_heading_branches():
    from app.rag.pdf_knowledge_ingestion import _chunk_text_with_paths

    notes = (
        "（一）重要会计政策\n"
        "1. 收入确认\n"
        "（1）坏账准备计提方法\n"
        "公司按预期信用损失模型计提坏账准备。\n"
        "2. 存货计价\n"
        "存货按加权平均法计价。"
    )
    chunks = _chunk_text_with_paths(notes, "financial_notes", max_chars=15, min_chars=1)

    bad_debt = next(chunk for chunk in chunks if "（1）坏账准备计提方法" in chunk["text"])
    assert bad_debt["hierarchy_path"].endswith("（一）重要会计政策 > 1. 收入确认 > （1）坏账准备计提方法")
    inventory = next(chunk for chunk in chunks if "加权平均" in chunk["text"])
    assert inventory["hierarchy_path"].endswith("（一）重要会计政策 > 2. 存货计价")
    first = next(chunk for chunk in chunks if "重要会计政策" in chunk["text"])
    assert first["hierarchy_path"] == "financial_notes > （一）重要会计政策"
    assert all(chunk["chunk_type"] == "narrative" for chunk in chunks)


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


def test_build_documents_from_pipeline_result():
    import pandas as pd
    from app.engines.rebecca.parsers.financial_pdf_pipeline import PipelineResult, FinancialStatementData

    pipeline_result = PipelineResult(
        success=True,
        pdf_url="https://example.com/ar.pdf",
        report_year=2025,
        statements=FinancialStatementData(
            income_statement=pd.DataFrame([
                {"field": "revenue", "label": "营业收入", "2025": 100000000.0},
                {"field": "net_profit", "label": "净利润", "2025": 12000000.0},
            ]),
            balance_sheet=pd.DataFrame([
                {"field": "total_assets", "label": "资产总计", "2025": 300000000.0},
            ]),
            cash_flow=pd.DataFrame([
                {"field": "net_operating_cash_flow", "label": "经营活动产生的现金流量净额", "2025": 20000000.0},
            ]),
        ),
        main_table_coverage="3/3",
        auto_judgment_rate=1.0,
        needs_human_review=False,
        issues=[],
    )

    docs = build_documents_from_pipeline_result("测试公司", pipeline_result)

    assert len(docs) == 4  # 3 张表 + 1 质量摘要
    sections = {doc.metadata["section"] for doc in docs}
    assert "pipeline_income_statement" in sections
    assert "pipeline_balance_sheet" in sections
    assert "pipeline_cash_flow" in sections
    assert "pipeline_quality" in sections
    for doc in docs:
        assert doc.metadata["enterprise_name"] == "测试公司"
        assert doc.metadata["parser_used"] == "financial_pdf_pipeline"
        assert doc.metadata["id"].startswith("pdf_")


def test_build_documents_from_pipeline_result_none():
    assert build_documents_from_pipeline_result("测试公司", None) == []


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
