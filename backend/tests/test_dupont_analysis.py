"""杜邦分析离线测试（计算化，不依赖 LLM）。"""

import pandas as pd
import pytest

from app.agents.sub_agents.dupont_analyzer import build_dupont_analysis


def _mock_rebecca_data():
    years = ["2023", "2022", "2021"]
    income = pd.DataFrame({
        "项目": ["营业收入", "净利润"],
        "2023": [14_000_000_000.0, 300_000_000.0],
        "2022": [13_000_000_000.0, 200_000_000.0],
        "2021": [12_000_000_000.0, 100_000_000.0],
    })
    balance = pd.DataFrame({
        "项目": ["资产总计", "所有者权益"],
        "2023": [40_000_000_000.0, 20_000_000_000.0],
        "2022": [38_000_000_000.0, 19_000_000_000.0],
        "2021": [36_000_000_000.0, 18_000_000_000.0],
    })
    return {"income_statement": income, "balance_sheet": balance, "cash_flow": pd.DataFrame()}


def test_dupont_factors_and_roe():
    r = build_dupont_analysis(_mock_rebecca_data())
    assert r["success"] is True
    f = r["factors"]
    # 2023: 净利率 3/140=2.14%, 周转率 140/400=0.35, 权益乘数 400/200=2.0
    assert abs(f["net_margin"]["2023"] - 3 / 140) < 1e-4
    assert abs(f["asset_turnover"]["2023"] - 140 / 400) < 1e-4
    assert abs(f["equity_multiplier"]["2023"] - 400 / 200) < 1e-4
    # 三因子乘积应等于 ROE（3/200=1.5%）
    assert abs(f["roe"]["2023"] - 0.015) < 1e-4


def test_dupont_driver_attribution():
    r = build_dupont_analysis(_mock_rebecca_data())
    dec = r["decomposition"]
    # 最新年度应有驱动归因（与前一年比较）
    assert dec[0]["year"] == "2023"
    assert dec[0]["driver"]  # 非空
    assert "ROE" in dec[0]["driver"]


def test_dupont_red_flags_on_low_margin():
    r = build_dupont_analysis(_mock_rebecca_data())
    # 净利率 2.14% < 3% → 触发主业盈利偏弱红黄灯
    assert any("净利率" in flag for flag in r["red_flags"])


def test_dupont_decomposition_includes_raw_values():
    r = build_dupont_analysis(_mock_rebecca_data())
    latest = r["decomposition"][0]
    # 2023 原始科目值应写入 decomposition，供杜邦 Mermaid 叶子节点使用
    assert latest["revenue"] == pytest.approx(14_000_000_000.0)
    assert latest["net_profit"] == pytest.approx(300_000_000.0)
    assert latest["total_assets"] == pytest.approx(40_000_000_000.0)
    assert latest["equity"] == pytest.approx(20_000_000_000.0)
    assert r["raw_values"]["2023"]["revenue"] == pytest.approx(14_000_000_000.0)
