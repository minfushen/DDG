"""舆情/声誉风险模块单元测试（mock 搜索源，验证不依赖外网/密钥）。"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.agents.tools.bocha_search_tool as bocha_mod
import app.agents.tools.searxng_search_tool as searxng_mod
import app.agents.sub_agents.sentiment_agent as sa_mod


def _mock_bocha(results):
    bocha_mod.search_with_bocha = lambda *a, **k: {"success": True, "provider": "bocha", "results": results}
    searxng_mod.search_with_searxng = lambda *a, **k: {"success": False, "provider": "searxng", "results": []}


def _mock_bocha_fail_searxng_fail():
    bocha_mod.search_with_bocha = lambda *a, **k: {"success": False, "provider": "bocha", "error": "no key", "results": []}
    searxng_mod.search_with_searxng = lambda *a, **k: {"success": False, "provider": "searxng", "error": "no url", "results": []}


def test_agent_returns_report(monkeypatch):
    _mock_bocha([
        {"title": "测试科技中标大单", "snippet": "公司中标并增长", "url": "https://news.example.com/a", "source": "example.com"},
        {"title": "测试科技被处罚", "snippet": "因环保被行政处罚", "url": "https://news.example.com/b", "source": "example.com"},
    ])
    result = sa_run("测试科技")
    assert result["success"] is True
    report = result["sentiment_analysis_report"]
    assert report["report_type"] == "sentiment_analysis"
    assert report["summary"]["检索结果"] == 2
    assert report["summary"]["负面"] >= 1
    assert report["risk_rating"] in {"low", "medium", "high"}
    assert len(report["sections"]) == 4


def test_high_trust_negative_escalates_rating(monkeypatch):
    _mock_bocha([
        {"title": "测试科技被立案调查", "snippet": "证监会立案处罚", "url": "https://www.csrc.gov.cn/x", "source": "csrc.gov.cn"},
    ])
    result = sa_run("测试科技")
    report = result["sentiment_analysis_report"]
    # 权威源（监管）负面 => high
    assert report["risk_rating"] == "high"
    tag_names = {t["tag"] for t in report["risk_tags"]}
    assert "权威源负面舆情" in tag_names


def test_positive_only_rating_low(monkeypatch):
    _mock_bocha([
        {"title": "测试科技签约突破", "snippet": "公司获奖并扩产增长", "url": "https://news.example.com/c", "source": "example.com"},
    ])
    result = sa_run("测试科技")
    report = result["sentiment_analysis_report"]
    assert report["risk_rating"] == "low"
    tag_names = {t["tag"] for t in report["risk_tags"]}
    assert "舆情平稳" in tag_names


def test_degraded_when_search_fails(monkeypatch):
    _mock_bocha_fail_searxng_fail()
    result = sa_run("故障企业")
    # 两个搜索源都失败，agent 仍应返回成功结构（安全降级），舆情平稳
    assert result["success"] is True
    report = result["sentiment_analysis_report"]
    assert report["risk_rating"] in {"low", "medium"}
    tag_names = {t["tag"] for t in report["risk_tags"]}
    assert "舆情平稳" in tag_names


def sa_run(name):
    from app.agents.sub_agents.sentiment_agent import run_sentiment_agent

    return asyncio.run(run_sentiment_agent(name))
