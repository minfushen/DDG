import httpx

from app.agents.evidence import normalize_evidence
from app.agents.tools.searxng_search_tool import search_with_searxng


class FakeResponse:
    def __init__(self, status_code=200, headers=None, json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers or {"content-type": "application/json"}
        self._json_data = json_data
        self.text = text

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


def test_searxng_search_normalizes_json_results(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(json_data={
            "query": "欣旺达 年报",
            "results": [
                {
                    "title": "欣旺达2024年年度报告",
                    "url": "https://www.cninfo.com.cn/new/disclosure/detail",
                    "content": "年度报告摘要",
                    "engine": "baidu",
                }
            ],
        })

    monkeypatch.setattr(httpx, "get", fake_get)
    result = search_with_searxng("欣旺达 年报", max_results=5, base_url="http://test.local")

    assert result["success"] is True
    assert result["provider"] == "searxng"
    assert len(result["results"]) == 1
    row = result["results"][0]
    assert row["provider"] == "searxng"
    assert row["title"] == "欣旺达2024年年度报告"
    assert row["trust_level"] == "high"


def test_searxng_search_reports_html_response(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: FakeResponse(headers={"content-type": "text/html"}, text="<!doctype html><html></html>"),
    )
    result = search_with_searxng("欣旺达", base_url="http://test.local")

    assert result["success"] is False
    assert "returned HTML" in result["error"]


def test_searxng_search_empty_results(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse(json_data={"query": "none", "results": []}))
    result = search_with_searxng("none", base_url="http://test.local")

    assert result["success"] is False
    assert result["results"] == []


def test_searxng_result_can_be_normalized_to_evidence(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse(json_data={
        "query": "药明康德 诉讼",
        "results": [{"title": "药明康德公告", "url": "https://www.sse.com.cn/disclosure", "content": "公告内容", "engine": "sogou"}],
    }))
    result = search_with_searxng("药明康德 诉讼", base_url="http://test.local")
    item = result["results"][0]
    evidence = normalize_evidence({
        "label": "聚合公开搜索线索",
        "value": item["title"],
        "source": item["source"],
        "source_name": item["site_name"],
        "source_url": item["url"],
        "source_type": item["source_type"],
        "trust_level": item["trust_level"],
        "confidence": item["confidence"],
    }, agent="legal", domain="legal")

    assert evidence["source_type"] == item["source_type"]
    assert evidence["source_url"] == "https://www.sse.com.cn/disclosure"
    assert evidence["trust_level"] == "high"
