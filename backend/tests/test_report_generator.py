import os
import sys

# 本地验证用：若运行环境尚未安装 reportlab（requirements 已加入），从 /tmp/rlpkgs 兜底
_RL = "/tmp/rlpkgs"
if os.path.isdir(_RL):
    sys.path.insert(0, _RL)

from app.engines.rebecca.report_generator import ReportGenerator

import pytest


@pytest.fixture
def gen(tmp_path):
    return ReportGenerator(output_dir=str(tmp_path))


def _sample_report():
    return {
        "enterprise_name": "单元测试公司",
        "risk_rating": "medium",
        "recommendation": "建议作为初步尽调结果使用。",
        "credit_decision": {"suggestion": "初步谨慎准入", "collateral_advice": "需落实担保"},
        "financial_analysis_report": {
            "risk_rating": "low",
            "recommendation": "财务结构稳健",
            "highlights": ["毛利率提升", "现金流为正"],
        },
        "industry_analysis_report": {"risk_rating": "medium", "conclusion": "行业景气度平稳"},
        "evidence": [{"label": "营业收入", "value": "120亿", "source": "CNINFO"}],
    }


def test_structured_docx(gen):
    path = gen.generate_from_report(_sample_report(), "单元测试公司", "docx")
    assert path.endswith(".docx")
    assert os.path.getsize(path) > 1000


def test_structured_pdf(gen):
    path = gen.generate_from_report(_sample_report(), "单元测试公司", "pdf")
    assert path.endswith(".pdf")
    assert os.path.getsize(path) > 1000


def test_structured_md(gen):
    path = gen.generate_from_report(_sample_report(), "单元测试公司", "md")
    assert path.endswith(".md")
    content = open(path, encoding="utf-8").read()
    assert "# 单元测试公司" in content
    assert "营业收入" in content
    assert os.path.getsize(path) > 100


def test_financial_pdf_schema(gen):
    fin = {
        "profitability": {"毛利率": {"data": [["指标", "值"], ["毛利率", "35%"]]}},
        "risk_assessment": {"risk_summary": [{"风险等级": "中", "风险描述": "应收账款偏高"}]},
    }
    path = gen._generate_pdf("财务公司", fin)
    assert path.endswith(".pdf")
    assert os.path.getsize(path) > 1000


def test_collect_blocks_none_and_scalar(gen):
    blocks = []
    gen._collect_blocks("root", {"a": None, "b": 1, "c": "x"}, blocks)
    kinds = {k for k, _ in blocks}
    assert "p" in kinds  # 标量 / None 都应落到段落，且不抛错
    assert gen._to_serializable(None) is None


def test_humanize():
    assert ReportGenerator._humanize("risk_rating") == "Risk rating"
    assert ReportGenerator._humanize("enterprise_name") == "Enterprise name"
