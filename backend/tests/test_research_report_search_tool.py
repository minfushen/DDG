import pytest
from unittest.mock import patch, MagicMock

from app.agents.tools.research_report_search_tool import (
    _rank_reports,
    _normalize_report_result,
    search_research_reports,
    search_industry_research_reports,
)


class TestNormalizeReportResult:
    def test_bocha_result(self):
        item = {
            "title": "半导体行业深度研报",
            "url": "http://example.com/report.pdf",
            "summary": "这是一份深度报告",
            "publishedDate": "2024-01-01",
            "siteName": "中信证券",
            "rank": 1,
        }
        result = _normalize_report_result(item, "半导体")
        assert result["title"] == "半导体行业深度研报"
        assert result["url"] == "http://example.com/report.pdf"
        assert result["is_pdf"] is True
        assert result["date"] == "2024-01-01"
        assert result["source"] == "中信证券"
        assert result["query"] == "半导体"

    def test_searxng_result(self):
        item = {
            "title": "新能源电池研究报告",
            "url": "http://example.com/article",
            "content": "电池行业分析",
            "published_at": "2024-06-01",
        }
        result = _normalize_report_result(item, "电池")
        assert result["is_pdf"] is False
        assert result["date"] == "2024-06-01"
        assert result["snippet"] == "电池行业分析"


class TestRankReports:
    def test_title_keyword_priority(self):
        results = [
            {"title": "普通新闻", "url": "http://example.com/1", "date": "", "is_pdf": False, "rank": 1},
            {"title": "半导体行业研报", "url": "http://example.com/2", "date": "", "is_pdf": False, "rank": 2},
            {"title": "新能源深度研究报告", "url": "http://example.com/3", "date": "", "is_pdf": False, "rank": 3},
        ]
        ranked = _rank_reports(results, "测试", max_results=8)
        # "研报" +2, "研究报告" +2 (both keywords hit "研报" and "研究报告"? Actually "研报" is in _REPORT_KEYWORDS, "研究报告" contains "研报" and "研究"? Let's check: _REPORT_KEYWORDS = ["研报", "研究报告", "深度", "行业", "证券"])
        # "半导体行业研报" hits "研报" (+2), "行业" (+2) = 4
        # "新能源深度研究报告" hits "研究报告" (+2), "深度" (+2), "行业"? no, = 4
        # But "半导体行业研报" has rank 2, "新能源深度研究报告" has rank 3
        # So order should be: 半导体行业研报 first (same score, lower rank), then 新能源深度研究报告, then 普通新闻
        titles = [r["title"] for r in ranked]
        assert titles[0] == "半导体行业研报"
        assert titles[1] == "新能源深度研究报告"
        assert titles[2] == "普通新闻"

    def test_deduplication_by_url(self):
        results = [
            {"title": "研报A", "url": "http://example.com/same", "date": "2024-01-01", "is_pdf": True, "rank": 1},
            {"title": "研报B", "url": "http://example.com/same", "date": "2024-01-01", "is_pdf": True, "rank": 2},
        ]
        # search_research_reports handles dedup after ranking; _rank_reports itself doesn't dedup
        # Let's test through search_research_reports
        pass


class TestSearchResearchReports:
    @patch("app.agents.tools.research_report_search_tool.search_with_bocha")
    @patch("app.agents.tools.research_report_search_tool.search_with_searxng")
    def test_bocha_priority(self, mock_searxng, mock_bocha, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.research_report_search_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = {
            "success": True,
            "results": [
                {"title": "半导体行业研报", "url": "http://example.com/1", "summary": "报告内容", "publishedDate": "2024-01-01", "siteName": "中信证券"}
            ],
        }
        result = search_research_reports("半导体", max_results=5)
        assert result["success"] is True
        assert result["provider"] == "bocha"
        assert result["total"] == 1
        assert result["results"][0]["title"] == "半导体行业研报"
        mock_bocha.assert_called_once()
        mock_searxng.assert_not_called()

    @patch("app.agents.tools.research_report_search_tool.search_with_bocha")
    @patch("app.agents.tools.research_report_search_tool.search_with_searxng")
    def test_bocha_failure_fallback_to_searxng(self, mock_searxng, mock_bocha, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.research_report_search_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = {"success": False, "error": "Bocha quota exceeded"}
        mock_searxng.return_value = {
            "success": True,
            "results": [
                {"title": "新能源研究报告", "url": "http://example.com/2", "content": "内容", "published_at": "2024-02-01"}
            ],
        }
        result = search_research_reports("新能源", max_results=5)
        assert result["success"] is True
        assert result["provider"] == "searxng"
        assert result["total"] == 1
        mock_bocha.assert_called_once()
        mock_searxng.assert_called_once()

    @patch("app.agents.tools.research_report_search_tool.search_with_bocha")
    @patch("app.agents.tools.research_report_search_tool.search_with_searxng")
    def test_no_api_key_uses_searxng(self, mock_searxng, mock_bocha, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.research_report_search_tool.settings.BOCHA_API_KEY", None
        )
        mock_searxng.return_value = {
            "success": True,
            "results": [
                {"title": "白酒行业分析", "url": "http://example.com/3", "content": "分析内容"}
            ],
        }
        result = search_research_reports("白酒", max_results=5)
        assert result["success"] is True
        assert result["provider"] == "searxng"
        mock_bocha.assert_not_called()

    @patch("app.agents.tools.research_report_search_tool.search_with_bocha")
    @patch("app.agents.tools.research_report_search_tool.search_with_searxng")
    def test_both_fail(self, mock_searxng, mock_bocha, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.research_report_search_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = {"success": False, "error": "Bocha error"}
        mock_searxng.return_value = {"success": False, "error": "SearXNG error"}
        result = search_research_reports("测试", max_results=5)
        assert result["success"] is False
        assert result["total"] == 0
        assert "Bocha error" in result["error"]

    @patch("app.agents.tools.research_report_search_tool.search_with_bocha")
    @patch("app.agents.tools.research_report_search_tool.search_with_searxng")
    def test_deduplication(self, mock_searxng, mock_bocha, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.research_report_search_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = {
            "success": True,
            "results": [
                {"title": "研报A", "url": "http://example.com/dup", "summary": "内容1", "publishedDate": "2024-01-01"},
                {"title": "研报B", "url": "http://example.com/dup", "summary": "内容2", "publishedDate": "2024-01-02"},
            ],
        }
        result = search_research_reports("测试", max_results=5)
        assert result["success"] is True
        assert result["total"] == 1
        assert result["results"][0]["title"] == "研报A"


class TestSearchIndustryResearchReports:
    @patch("app.agents.tools.research_report_search_tool.search_research_reports")
    def test_merge_and_deduplicate(self, mock_search):
        def side_effect(query, max_results):
            if "券商研报" in query:
                return {
                    "success": True,
                    "results": [
                        {"title": "研报1", "url": "http://a.com/1", "snippet": "内容1"},
                        {"title": "研报2", "url": "http://a.com/2", "snippet": "内容2"},
                    ],
                }
            else:
                return {
                    "success": True,
                    "results": [
                        {"title": "研报2", "url": "http://a.com/2", "snippet": "内容2"},  # duplicate
                        {"title": "研报3", "url": "http://a.com/3", "snippet": "内容3"},
                    ],
                }

        mock_search.side_effect = side_effect
        result = search_industry_research_reports("半导体", max_results=5)
        assert result["success"] is True
        assert result["total"] == 3
        urls = [r["url"] for r in result["results"]]
        assert "http://a.com/1" in urls
        assert "http://a.com/2" in urls
        assert "http://a.com/3" in urls

    @patch("app.agents.tools.research_report_search_tool.search_research_reports")
    def test_no_results(self, mock_search):
        mock_search.return_value = {"success": False, "results": [], "error": "No results"}
        result = search_industry_research_reports("不存在的行业", max_results=5)
        assert result["success"] is False
        assert result["total"] == 0
