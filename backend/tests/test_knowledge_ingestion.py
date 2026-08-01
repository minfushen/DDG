"""Markdown 知识库分块测试：层级路径 / 原子表格 / 小块合并（与 PDF 链路共用规则）。"""

from app.rag.knowledge_ingestion import _chunk_markdown, build_documents_from_markdown


def test_markdown_chunks_carry_hierarchy_path(tmp_path):
    root = tmp_path
    md = root / "industry_guides" / "半导体.md"
    md.parent.mkdir(parents=True)
    md.write_text(
        "# 半导体行业指南\n"
        "行业概述内容。\n"
        "## 政策环境\n"
        "### 绿色信贷\n"
        "绿色信贷鼓励名单制管理。\n"
        "## 竞争格局\n"
        "行业集中度提升。\n",
        encoding="utf-8",
    )

    docs = build_documents_from_markdown(md, root)

    assert docs
    paths = [d.metadata["hierarchy_path"] for d in docs]
    assert any("半导体行业指南 > 政策环境 > 绿色信贷" in p for p in paths)
    assert any("半导体行业指南 > 竞争格局" in p for p in paths)
    assert all(d.metadata["chunk_type"] == "narrative" for d in docs)
    # header 兼容字段应等于最后一级标题
    for doc in docs:
        assert doc.metadata["header"] == doc.metadata["hierarchy_path"].split(" > ")[-1]


def test_markdown_table_kept_whole(tmp_path):
    root = tmp_path
    md = root / "industry_guides" / "指标表.md"
    md.parent.mkdir(parents=True)
    rows = [
        "| 指标名称 | 行业参考阈值 | 说明 |",
        "| --- | --- | --- |",
    ] + [f"| 指标{i} | 1.5 | 需结合行业周期复核 |" for i in range(8)]
    md.write_text("# 授信指标\n" + "\n".join(rows) + "\n", encoding="utf-8")

    docs = build_documents_from_markdown(md, root)
    table_text = "\n".join(rows)

    # 表格块整块保留，不允许跨行切分，且块类型标记为 table
    assert any(table_text in doc.page_content for doc in docs)
    assert any(doc.metadata["chunk_type"] == "table" for doc in docs)


def test_markdown_small_tail_merged():
    chunks = _chunk_markdown("# 规则\n" + "长段落内容。" * 30 + "\n补充说明。\n", max_chars=100)

    # 硬切产生 100/80 两段，80 与 5 字符的小片段都应并入前块
    assert len(chunks) == 1
    assert "补充说明" in chunks[0]["text"]
    assert chunks[0]["chunk_type"] == "narrative"
