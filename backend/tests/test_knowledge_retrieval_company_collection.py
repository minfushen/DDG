from app.rag.collection_names import GENERAL_COLLECTION, company_collection_name
from app.rag.knowledge_retrieval_service import retrieve_knowledge


def _fake_doc(content: str, **metadata):
    class FakeDoc:
        def __init__(self, content, metadata):
            self.page_content = content
            self.metadata = metadata
    return FakeDoc(content, metadata)


def test_retrieve_knowledge_without_company_name(monkeypatch):
    def fake_vector_search(query, domain, top_k, collection_name):
        assert collection_name == GENERAL_COLLECTION
        return [{
            "id": "kb_1",
            "title": "授信决策规则",
            "content": "速动比率达标可贷款",
            "source": "credit_guide.md",
            "category": "credit_guide",
            "score": 8.0,
            "confidence": 0.85,
            "reliability": "high",
            "requires_manual_review": False,
        }]

    monkeypatch.setattr("app.rag.knowledge_retrieval_service._vector_search", fake_vector_search)

    result = retrieve_knowledge("速动比率 贷款", domain="credit", top_k=5)
    assert result["success"] is True
    assert result["mode"] == "vector"
    assert len(result["results"]) == 1


def test_retrieve_knowledge_with_company_name(monkeypatch):
    searched_collections = []

    def fake_vector_search(query, domain, top_k, collection_name):
        searched_collections.append(collection_name)
        if collection_name == company_collection_name("测试公司"):
            return [{
                "id": "pdf_1",
                "title": "测试公司 - 2025年年度报告",
                "content": "资产负债率上升但速动比率达标",
                "source": "https://example.com/ar.pdf",
                "category": "annual_report",
                "score": 9.0,
                "confidence": 0.85,
                "reliability": "high",
                "requires_manual_review": False,
            }]
        return [{
            "id": "kb_2",
            "title": "授信决策规则",
            "content": "速动比率达标可作为贷款参考",
            "source": "credit_guide.md",
            "category": "credit_guide",
            "score": 7.0,
            "confidence": 0.82,
            "reliability": "high",
            "requires_manual_review": False,
        }]

    monkeypatch.setattr("app.rag.knowledge_retrieval_service._vector_search", fake_vector_search)

    result = retrieve_knowledge("速动比率 贷款", domain="credit", top_k=5, company_name="测试公司")
    assert result["success"] is True
    assert result["mode"] == "vector"
    assert company_collection_name("测试公司") in searched_collections
    assert GENERAL_COLLECTION in searched_collections
    # Company hit has higher score and should rank first.
    assert result["results"][0]["id"] == "pdf_1"
    assert any(hit["id"] == "kb_2" for hit in result["results"])


def test_retrieve_knowledge_fallback_when_vector_empty(monkeypatch):
    def fake_vector_search(query, domain, top_k, collection_name):
        return []

    def fake_local_search(query, domain, top_k):
        return [{
            "id": "local_1",
            "title": "本地规则",
            "content": "速动比率规则",
            "source": "local.md",
            "score": 5.0,
            "confidence": 0.7,
            "reliability": "medium",
            "requires_manual_review": False,
            "retrieval_mode": "local_keyword",
        }]

    monkeypatch.setattr("app.rag.knowledge_retrieval_service._vector_search", fake_vector_search)
    monkeypatch.setattr("app.rag.knowledge_retrieval_service._local_keyword_search", fake_local_search)

    result = retrieve_knowledge("速动比率 贷款", domain="credit", top_k=5)
    assert result["success"] is True
    assert result["mode"] == "local_keyword"
    assert len(result["results"]) == 1


def test_dedupe_merge_ranks_by_hierarchy_path():
    from app.rag.knowledge_retrieval_service import _dedupe_and_merge_hits

    path_hit = {
        "id": "a",
        "source": "s1",
        "chunk_index": 0,
        "content": "坏账准备按预期信用损失模型计提。",
        "score": 6.0,
        "hierarchy_path": "财务报告附注 > （一）重要会计政策 > 1. 收入确认 > （1）坏账准备计提方法",
    }
    raw_higher_hit = {
        "id": "b",
        "source": "s2",
        "chunk_index": 0,
        "content": "其他内容。",
        "score": 8.0,
        "hierarchy_path": "",
    }

    merged = _dedupe_and_merge_hits([[path_hit], [raw_higher_hit]], top_k=2, query="坏账准备计提方法")

    # 原始分数较低但层级路径命中 query 的 hit 应排到前面
    assert merged[0]["id"] == "a"
    assert merged[1]["id"] == "b"
