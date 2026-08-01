"""灵活修改（非功能需求②）测试：提示词覆盖 + 可编辑知识库。"""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import prompt_overrides  # noqa: E402
from app.config.prompt_loader import load_prompt_template  # noqa: E402
from app.rag import editable_knowledge  # noqa: E402
from app.rag.knowledge_retrieval_service import retrieve_knowledge  # noqa: E402


@pytest.fixture()
def tmp_override(tmp_path, monkeypatch):
    p = tmp_path / "prompt_overrides.json"
    monkeypatch.setattr(prompt_overrides, "OVERRIDES_PATH", p)
    p.write_text("{}", encoding="utf-8")
    yield p


@pytest.fixture()
def tmp_kb(tmp_path, monkeypatch):
    p = tmp_path / "editable_knowledge.json"
    monkeypatch.setattr(editable_knowledge, "STORE_PATH", p)
    p.write_text("[]", encoding="utf-8")
    yield p


def test_prompt_override_takes_effect_and_resets(tmp_override):
    key = "financial_narrative"
    base = load_prompt_template(key)
    assert base  # 基线存在
    prompt_overrides.set_override(key, "CUSTOM_PROMPT_TEXT")
    assert load_prompt_template(key) == "CUSTOM_PROMPT_TEXT"
    # 列表可见 overridden=True
    meta = next(m for m in prompt_overrides.list_prompts() if m["key"] == key)
    assert meta["overridden"] is True
    # 重置后回到基线
    assert prompt_overrides.reset_override(key) is True
    assert load_prompt_template(key) == base


def test_editable_knowledge_crud(tmp_kb):
    e = editable_knowledge.create_entry("risk_frameworks", "授信风控要点", "关注资产负债率与现金流覆盖。", tags=["授信"])
    assert e["id"]
    assert editable_knowledge.get_entry(e["id"])["title"] == "授信风控要点"
    updated = editable_knowledge.update_entry(e["id"], content="关注资产负债率、现金流与担保覆盖。")
    assert "担保覆盖" in updated["content"]
    assert editable_knowledge.delete_entry(e["id"]) is True
    assert editable_knowledge.get_entry(e["id"]) is None


def test_editable_knowledge_search_and_retrieval_merge(tmp_kb):
    editable_knowledge.create_entry("credit_guide", "制造业授信审查", "制造业客户应重点核验产能利用率与回款周期。", tags=["授信", "制造业"])
    hits = editable_knowledge.search_editable_knowledge("制造业 授信", top_k=3)
    assert hits and "制造业" in hits[0]["content"]

    # 作为 RAG 额外召回源参与 retrieve_knowledge（domain=credit 命中 credit_guide）
    res = retrieve_knowledge("制造业授信审查", domain="credit", top_k=5)
    assert res["success"] is True
    titles = [h.get("title") for h in res["results"]]
    assert any("制造业授信审查" in (t or "") for t in titles)
