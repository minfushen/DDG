import pytest
from unittest.mock import patch, MagicMock

import pandas as pd

from app.agents.tools.industry_market_data_tool import (
    _map_to_index_symbol,
    get_industry_index_data,
    get_industry_market_data,
    _score_search_result,
    _apply_quality_to_category,
    _is_index_data_stale,
    _is_index_data_anomaly,
    _refill_category,
)


class FakeAk:
    @staticmethod
    def stock_board_industry_hist_em(symbol, period, start_date, end_date, adjust):
        return pd.DataFrame([
            {"日期": "20240102", "开盘": 1000.0, "收盘": 1010.0, "最高": 1020.0, "最低": 990.0, "成交量": 50000, "成交额": 1.5e8, "振幅": 3.0, "涨跌幅": 1.0, "涨跌额": 10.0, "换手率": 2.5},
            {"日期": "20240103", "开盘": 1010.0, "收盘": 1020.0, "最高": 1030.0, "最低": 1000.0, "成交量": 55000, "成交额": 1.6e8, "振幅": 2.9, "涨跌幅": 1.0, "涨跌额": 10.0, "换手率": 2.6},
            {"日期": "20241230", "开盘": 1100.0, "收盘": 1150.0, "最高": 1160.0, "最低": 1090.0, "成交量": 60000, "成交额": 2.0e8, "振幅": 6.0, "涨跌幅": 2.0, "涨跌额": 22.0, "换手率": 3.0},
        ])


class FakeAkEmpty:
    @staticmethod
    def stock_board_industry_hist_em(symbol, period, start_date, end_date, adjust):
        return pd.DataFrame()


class FakeAkFailure:
    @staticmethod
    def stock_board_industry_hist_em(symbol, period, start_date, end_date, adjust):
        raise RuntimeError("network error")


@pytest.fixture
def mock_akshare_success(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAk)


@pytest.fixture
def mock_akshare_empty(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAkEmpty)


@pytest.fixture
def mock_akshare_failure(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "akshare", FakeAkFailure)


class TestMapToIndexSymbol:
    def test_exact_match(self):
        assert _map_to_index_symbol("半导体") == "半导体"
        assert _map_to_index_symbol("白酒") == "白酒"

    def test_substring_match(self):
        # "芯片" is in map, "芯片设计" contains "芯片"
        assert _map_to_index_symbol("芯片设计") == "半导体"
        # "集成电路设计" contains "集成电路"
        assert _map_to_index_symbol("集成电路设计") == "半导体"
        # map contains "电机", query "微电机" contains "电机"
        assert _map_to_index_symbol("微电机") == "电机"

    def test_no_match(self):
        assert _map_to_index_symbol("不存在的行业") is None
        # Empty string after normalization falls back to original empty string,
        # and the empty string is a substring of every key, so it matches.
        # We just verify it doesn't crash and returns a valid mapped symbol.
        result = _map_to_index_symbol("")
        assert result is not None  # empty string matches first key via substring


class TestGetIndustryIndexData:
    def test_success(self, mock_akshare_success):
        with patch("app.agents.tools.industry_market_data_tool._is_index_data_stale", return_value=False):
            with patch("app.agents.tools.industry_market_data_tool._is_index_data_anomaly", return_value=False):
                result = get_industry_index_data("半导体")
        assert result["success"] is True
        assert result["symbol"] == "半导体"
        assert result["latest_close"] == 1150.0
        assert result["latest_date"] == "20241230"
        # year_change = (1150 - 1010) / 1010 * 100 = 13.86...
        assert result["year_change_pct"] == pytest.approx(13.86, abs=0.1)
        # avg_turnover over last 20 (only 3 rows here) = mean([1.5e8, 1.6e8, 2.0e8]) / 1e8 = 1.7
        assert result["avg_turnover"] == pytest.approx(1.7, abs=0.1)
        assert result["source"] == "东方财富行业指数"
        assert result["error"] == ""
        assert result["quality_level"] == "ok"
        assert result["fallback_search"] == {}

    def test_empty_data(self, mock_akshare_empty):
        result = get_industry_index_data("半导体")
        assert result["success"] is False
        assert result["symbol"] == "半导体"
        assert "No index data" in result["error"]

    def test_akshare_failure(self, mock_akshare_failure):
        result = get_industry_index_data("半导体")
        assert result["success"] is False
        assert result["symbol"] == "半导体"
        assert "No index data" in result["error"]

    def test_no_mapping(self):
        result = get_industry_index_data("完全不存在的行业XYZ")
        assert result["success"] is False
        assert result["symbol"] is None
        assert "No index mapping" in result["error"]

    @patch("app.agents.tools.industry_market_data_tool._is_index_data_stale", return_value=True)
    @patch("app.agents.tools.industry_market_data_tool._fallback_index_text_search")
    def test_stale_data(self, mock_fallback, mock_stale, mock_akshare_success):
        mock_fallback.return_value = {"success": True, "results": [{"title": "fallback"}], "error": ""}
        result = get_industry_index_data("半导体")
        assert result["quality_level"] == "stale"
        assert "指数数据过期" in result["error"]
        assert result["fallback_search"]["success"] is True

    @patch("app.agents.tools.industry_market_data_tool._is_index_data_anomaly", return_value=True)
    @patch("app.agents.tools.industry_market_data_tool._fallback_index_text_search")
    def test_anomaly_data(self, mock_fallback, mock_anomaly, mock_akshare_success):
        mock_fallback.return_value = {"success": True, "results": [{"title": "fallback"}], "error": ""}
        result = get_industry_index_data("半导体")
        assert result["quality_level"] == "anomaly"
        assert "指数数据异常" in result["error"]
        assert result["fallback_search"]["success"] is True


class TestScoreSearchResult:
    def test_gov_cn(self):
        item = {"url": "https://www.miit.gov.cn/xxx"}
        scored = _score_search_result(item, "query")
        assert scored["trust_level"] == "high"
        assert scored["confidence"] == 0.86
        assert scored["requires_manual_review"] is False

    def test_eastmoney(self):
        item = {"url": "https://data.eastmoney.com/xxx"}
        scored = _score_search_result(item, "query")
        assert scored["trust_level"] == "medium"
        assert scored["confidence"] == 0.72
        assert scored["requires_manual_review"] is True

    def test_unknown(self):
        item = {"url": "https://example.com/xxx"}
        scored = _score_search_result(item, "query")
        assert scored["trust_level"] == "low_to_medium"
        assert scored["confidence"] == 0.58
        assert scored["requires_manual_review"] is True

    def test_empty_url(self):
        item = {"url": ""}
        scored = _score_search_result(item, "query")
        assert scored["trust_level"] == "low"
        assert scored["confidence"] == 0.42
        assert scored["source_type"] == "unknown"
        assert scored["requires_manual_review"] is True


class TestApplyQualityToCategory:
    def test_with_results(self):
        category = {
            "queries": ["q1"],
            "results": [
                {"url": "https://www.miit.gov.cn/1"},
                {"url": "https://example.com/2"},
            ],
        }
        result = _apply_quality_to_category(category, "market_size")
        assert "quality_score" in result
        assert "quality_level" in result
        assert result["quality_score"] == pytest.approx((0.86 + 0.58) / 2, abs=0.01)
        assert result["quality_level"] == "medium"
        assert len(result["results"]) == 2
        assert result["results"][0]["confidence"] == 0.86

    def test_no_results(self):
        category = {"queries": ["q1"], "results": []}
        result = _apply_quality_to_category(category, "market_size")
        assert result["quality_score"] == 0.0
        assert result["quality_level"] == "none"


class TestIsIndexDataStale:
    def test_stale(self):
        assert _is_index_data_stale({"latest_date": "20240101"}, days=5) is True

    def test_not_stale(self):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        assert _is_index_data_stale({"latest_date": today}, days=5) is False

    def test_parse_failure(self):
        assert _is_index_data_stale({"latest_date": "invalid"}, days=5) is True

    def test_none_date(self):
        assert _is_index_data_stale({}, days=5) is True


class TestIsIndexDataAnomaly:
    def test_year_change_out_of_range(self):
        assert _is_index_data_anomaly({"year_change_pct": -81, "avg_turnover": 1.0, "latest_close": 100.0}) is True
        assert _is_index_data_anomaly({"year_change_pct": 201, "avg_turnover": 1.0, "latest_close": 100.0}) is True

    def test_avg_turnover_negative(self):
        assert _is_index_data_anomaly({"year_change_pct": 10.0, "avg_turnover": -1.0, "latest_close": 100.0}) is True

    def test_latest_close_none(self):
        assert _is_index_data_anomaly({"year_change_pct": 10.0, "avg_turnover": 1.0, "latest_close": None}) is True

    def test_latest_close_nan(self):
        import math
        assert _is_index_data_anomaly({"year_change_pct": 10.0, "avg_turnover": 1.0, "latest_close": float("nan")}) is True

    def test_normal(self):
        assert _is_index_data_anomaly({"year_change_pct": 10.0, "avg_turnover": 1.0, "latest_close": 100.0}) is False


class TestRefillCategory:
    @patch("app.agents.tools.industry_market_data_tool._bocha_search")
    @patch("app.agents.tools.industry_market_data_tool._fallback_search_with_searxng")
    def test_refill_market_size(self, mock_searxng, mock_bocha, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.INDUSTRY_MARKET_DATA_ENABLE_REFILL", True
        )
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = [
            {"url": "https://example.com/new1", "title": "new1"},
        ]
        mock_searxng.return_value = []
        category = {"queries": ["q"], "results": [], "quality_level": "none", "quality_score": 0.0}
        result = _refill_category(category, "market_size", "半导体")
        assert result["refilled"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://example.com/new1"

    @patch("app.agents.tools.research_report_search_tool.search_industry_research_reports")
    def test_refill_research_reports(self, mock_reports, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.INDUSTRY_MARKET_DATA_ENABLE_REFILL", True
        )
        mock_reports.return_value = {
            "success": True,
            "results": [{"url": "https://report.com/1", "title": "report"}],
        }
        category = {"queries": ["q"], "results": [], "quality_level": "none", "quality_score": 0.0}
        result = _refill_category(category, "research_reports", "半导体")
        assert result["refilled"] is True
        assert any(r.get("url") == "https://report.com/1" for r in result["results"])

    def test_no_refill_when_disabled(self, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.INDUSTRY_MARKET_DATA_ENABLE_REFILL", False
        )
        category = {"queries": ["q"], "results": [], "quality_level": "none", "quality_score": 0.0}
        result = _refill_category(category, "market_size", "半导体")
        assert "refilled" not in result

    def test_no_refill_when_quality_high(self, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.INDUSTRY_MARKET_DATA_ENABLE_REFILL", True
        )
        category = {"queries": ["q"], "results": [{"url": "https://example.com/1"}], "quality_level": "high", "quality_score": 0.8}
        result = _refill_category(category, "market_size", "半导体")
        assert "refilled" not in result


class TestGetIndustryMarketData:
    @patch("app.agents.tools.industry_market_data_tool.search_with_bocha")
    def test_composite_success(self, mock_bocha, mock_akshare_success, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = {
            "success": True,
            "results": [
                {"title": "半导体市场规模", "snippet": "2024年市场规模约5000亿元", "url": "http://example.com/1"}
            ],
        }
        result = get_industry_market_data("半导体")
        assert result["success"] is True
        assert result["industry_name"] == "半导体"
        assert result["index_data"]["success"] is True
        assert result["market_size"]["results"]
        assert result["concentration"]["queries"]
        assert result["policy"]["queries"]
        assert result["chain"]["queries"]
        assert result["research_reports"]["queries"]
        assert "quality_summary" in result
        assert "overall_quality" in result["quality_summary"]
        assert "categories_present" in result["quality_summary"]
        assert "categories_missing" in result["quality_summary"]
        assert "needs_refill" in result["quality_summary"]

    @patch("app.agents.tools.industry_market_data_tool.search_with_bocha")
    def test_quality_summary(self, mock_bocha, mock_akshare_success, monkeypatch):
        monkeypatch.setattr(
            "app.agents.tools.industry_market_data_tool.settings.BOCHA_API_KEY", "test-key"
        )
        mock_bocha.return_value = {
            "success": True,
            "results": [
                {"title": "半导体市场规模", "snippet": "2024年市场规模约5000亿元", "url": "http://example.com/1"}
            ],
        }
        result = get_industry_market_data("半导体")
        qs = result["quality_summary"]
        assert qs["overall_quality"] > 0
        assert qs["categories_present"] >= 1  # at least index_data
        assert isinstance(qs["categories_missing"], list)
        assert isinstance(qs["needs_refill"], bool)
