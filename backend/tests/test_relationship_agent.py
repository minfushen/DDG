"""关联网络模块单元测试（mock 数据源，验证不依赖外网/密钥）。"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.agents.tools.listed_company_tool as listed_mod
import app.agents.tools.cninfo_webapi_tool as cninfo_mod
import app.agents.tools.listed_company_public_info_tool as public_mod
import app.agents.tools.yuandian_company_tool as yuandian_mod
import app.agents.tools.relationship_network_tool as rnt


def _mock_listed(monkeypatch):
    monkeypatch.setattr(
        listed_mod, "resolve_listed_company",
        lambda name, stock_code=None, stock_exchange=None: {
            "stock_code": "600703", "stock_exchange": "SH", "company_name": "测试股份",
        },
    )
    monkeypatch.setattr(cninfo_mod, "build_shareholder_table", lambda code: {
        "success": True, "stock_code": code, "report_date": "2024-12-31",
        "columns": ["股东名称", "股东性质", "持股比例", "持股数量", "质押/冻结"],
        "rows": [
            {"股东名称": "厦门三安", "股东性质": "境内非国有法人", "持股比例": "30.00%", "持股数量": 1000, "质押/冻结": "50,000,000股"},
            {"股东名称": "国家大基金", "股东性质": "国有法人", "持股比例": "10.00%", "持股数量": 300, "质押/冻结": "无"},
        ],
    })
    monkeypatch.setattr(cninfo_mod, "build_shareholder_profile", lambda code: {
        "stock_code": code,
        "top_shareholders": {"count": 2, "records": []},
        "actual_controller": {"count": 1, "records": [{"F004V": "林秀成"}]},
        "share_capital_changes": {"count": 0, "records": []},
    })
    monkeypatch.setattr(cninfo_mod, "build_risk_profile", lambda code: {
        "success": True, "stock_code": code,
        "litigation": {"count": 0, "records": []},
        "guarantees": {"count": 1, "records": [{"F001V": "关联方A", "F002N": 100.0, "F003V": "关联担保", "F004V": "关联方A"}]},
        "penalties": {"count": 0, "records": []},
        "asset_freezes": {"count": 1, "records": [{"F001V": "厦门三安", "F002N": 50.0, "F003V": "冻结"}]},
        "arbitration": {"count": 0, "records": []},
    })
    monkeypatch.setattr(public_mod, "fetch_listed_company_public_info_data", lambda *a, **k: {
        "success": True, "enterprise_name": "测试股份",
        "main_business_composition": [{"item_name": "LED芯片", "income_ratio": 0.5, "gross_margin": 0.3}],
        "search_clues": {"guarantee_pledge_announcements": ["质押公告1", "质押公告2"]},
    })
    monkeypatch.setattr(rnt, "_derive_supply_chain", lambda ind: {"upstream": ["晶圆"], "downstream": ["手机厂商"]})


def test_listed_network_builds_graph_and_tags(monkeypatch):
    _mock_listed(monkeypatch)
    net = rnt.build_relationship_network("测试股份", industry_name="半导体")
    assert net["success"] is True
    assert net["is_listed"] is True
    assert len(net["shareholders"]) == 2
    assert net["actual_controller"]["name"] == "林秀成"
    assert len(net["guarantees"]) == 1
    assert len(net["equity_freeze"]) == 1
    # 质押股东被标记
    assert any(s["name"] == "厦门三安" and s["pledge_freeze"] != "无" for s in net["shareholders"])
    # 关联担保 + 股权冻结 => high
    tag_names = {t["tag"] for t in net["risk_tags"]}
    assert "关联担保/担保圈" in tag_names
    assert "股权冻结" in tag_names
    assert net["risk_rating"] == "high"
    # 上下游来自 RAG mock
    assert net["supply_chain"]["upstream"] == ["晶圆"]


def test_agent_returns_report(monkeypatch):
    _mock_listed(monkeypatch)
    result = rnt_relationship_agent("测试股份")
    assert result["success"] is True
    report = result["relationship_analysis_report"]
    assert report["report_type"] == "relationship_analysis"
    assert report["risk_rating"] == "high"
    assert len(report["sections"]) == 4
    assert report["summary"]["实际控制人"] == "林秀成"


def test_nonlisted_network(monkeypatch):
    monkeypatch.setattr(listed_mod, "resolve_listed_company", lambda *a, **k: None)
    monkeypatch.setattr(yuandian_mod, "build_business_profile", lambda name: {
        "success": True, "enterprise_name": name,
        "basic_info": {"records": [{"股东": "张三", "proportion": 60, "isActualController": True}]},
        "risk_summary": {},
    })
    net = rnt.build_relationship_network("某未上市企业")
    assert net["is_listed"] is False
    assert any(s["name"] == "张三" and s["is_actual_controller"] for s in net["shareholders"])
    assert net["actual_controller"]["name"] == "张三"


def test_degraded_when_sources_fail(monkeypatch):
    monkeypatch.setattr(listed_mod, "resolve_listed_company", lambda *a, **k: (_ for _ in ()).throw(Exception("boom")))
    monkeypatch.setattr(cninfo_mod, "build_shareholder_table", lambda *a, **k: (_ for _ in ()).throw(Exception("x")))
    monkeypatch.setattr(cninfo_mod, "build_shareholder_profile", lambda *a, **k: (_ for _ in ()).throw(Exception("x")))
    monkeypatch.setattr(cninfo_mod, "build_risk_profile", lambda *a, **k: (_ for _ in ()).throw(Exception("x")))
    monkeypatch.setattr(public_mod, "fetch_listed_company_public_info_data", lambda *a, **k: (_ for _ in ()).throw(Exception("x")))
    monkeypatch.setattr(yuandian_mod, "build_business_profile", lambda *a, **k: (_ for _ in ()).throw(Exception("x")))
    net = rnt.build_relationship_network("故障企业")
    assert net["success"] is False
    assert net["risk_tags"][0]["tag"] == "关联数据暂不可得"
    assert net["risk_rating"] == "medium"


def rnt_relationship_agent(name):
    from app.agents.sub_agents.relationship_agent import run_relationship_agent
    return asyncio.run(run_relationship_agent(name))
