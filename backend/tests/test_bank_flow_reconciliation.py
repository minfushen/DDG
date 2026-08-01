"""银行流水 × 年报交叉核验引擎离线测试（不依赖网络/LLM）。"""

import json
import os

import pandas as pd
import pytest

from app.agents.tools.bank_flow_tool import (
    BankFlowData,
    bank_flow_from_dict,
    classify_flow_roles,
    load_bank_flow_json,
)
from app.agents.tools.flow_reconciliation import reconcile_flow_with_annual_report


SAMPLE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "regression_samples", "bank_flow_sample_sanan.json"
)


def _build_mock_rebecca_data():
    """构造与样例流水量级的年报三大表（DataFrame 形式，对齐项目实际结构）。"""
    years = ["2023", "2022", "2021"]
    income = pd.DataFrame({
        "项目": ["营业收入", "净利润"],
        "2023": [14_000_000_000.0, 300_000_000.0],
        "2022": [13_000_000_000.0, 200_000_000.0],
        "2021": [12_000_000_000.0, 100_000_000.0],
    })
    balance = pd.DataFrame({
        "项目": ["货币资金", "其他应收款", "预付款项", "资产总计", "负债合计", "所有者权益"],
        "2023": [7_000_000_000.0, 1_000_000_000.0, 500_000_000.0, 40_000_000_000.0, 20_000_000_000.0, 20_000_000_000.0],
        "2022": [6_500_000_000.0, 900_000_000.0, 600_000_000.0, 38_000_000_000.0, 19_000_000_000.0, 19_000_000_000.0],
        "2021": [6_000_000_000.0, 800_000_000.0, 500_000_000.0, 36_000_000_000.0, 18_000_000_000.0, 18_000_000_000.0],
    })
    cash_flow = pd.DataFrame({
        "项目": ["经营活动产生的现金流量净额"],
        "2023": [2_000_000_000.0],
        "2022": [1_800_000_000.0],
        "2021": [1_500_000_000.0],
    })
    return {"income_statement": income, "balance_sheet": balance, "cash_flow": cash_flow}


def test_parse_mock_flow():
    bfd = load_bank_flow_json(SAMPLE_PATH)
    assert isinstance(bfd, BankFlowData)
    assert bfd.enterprise_name == "三安光电股份有限公司"
    assert len(bfd.accounts) == 2
    assert bfd.total_closing_balance() == 7_000_000_000.0
    # 账户1 的关联方拆借/代付应标记
    related = [t for t in bfd.all_transactions() if t.is_related_party]
    assert len(related) == 2


def test_classify_flow_roles():
    bfd = load_bank_flow_json(SAMPLE_PATH)
    roles = classify_flow_roles(bfd)
    # 销售回款贷方：账户1(8+5+12+13) + 账户2(6+9+9) = 62亿
    assert roles["operating_credit"] == 6_200_000_000.0
    # 非经营贷方：账户2 票据贴现 4亿
    assert roles["non_operating_credit"] == 400_000_000.0
    # 关联方往来净额：账户1 (+5亿 -3亿) = +2亿
    assert roles["related_party_flow"] == 200_000_000.0


def test_reconcile_cash_consistent():
    bfd = load_bank_flow_json(SAMPLE_PATH)
    r = reconcile_flow_with_annual_report(bfd, _build_mock_rebecca_data(), net_assets=20_000_000_000.0)
    assert r["success"] is True
    by_key = {c["key"]: c for c in r["check_items"]}
    # 货币资金 70亿 == 余额之和 70亿 → 一致
    assert by_key["cash_vs_balance"]["status"] == "consistent"
    assert by_key["cash_vs_balance"]["annual_report_value"] == 7_000_000_000.0
    # 销售回款 62亿 / 营收 140亿 = 0.44 → 差异（演示回款低于营收需复核）
    assert by_key["revenue_vs_flow"]["status"] == "mismatch"
    # 触发关联方大额往来红黄灯
    assert any(f["type"] == "related_party_large_flow" for f in r["red_flags"])
    assert r["status"] in {"mismatch", "partial"}


def test_reconcile_skipped_without_flow():
    r = reconcile_flow_with_annual_report(None, _build_mock_rebecca_data())
    assert r["status"] == "skipped"
    assert "未提供银行流水" in r["summary"]


def test_bank_flow_from_dict_field_mapping():
    data = {
        "enterprise_name": "测试企业",
        "accounts": [{
            "account_no": "6222****0001",
            "transactions": [
                {"日期": "2023-01-01", "摘要": "货款", "借方": 0, "贷方": 100, "余额": 100},
                {"日期": "2023-01-02", "摘要": "采购", "借方": 50, "贷方": 0, "余额": 50},
            ],
        }],
    }
    bfd = bank_flow_from_dict(data)
    assert bfd.accounts[0].transactions[0].credit == 100.0
    assert bfd.accounts[0].transactions[1].debit == 50.0
