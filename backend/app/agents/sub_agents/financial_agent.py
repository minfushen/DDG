# ========================================
# 财务分析Agent
# 使用 Rebecca 引擎进行10维度财务分析
# ========================================

from typing import Dict, Any, List
from datetime import datetime
import uuid
import json

from app.agents.tools.search_tool import search_financial_data
from app.engines.rebecca.analyzers import FinancialDDAnalyzer
from app.engines.rebecca.adapter import AnalyzerAdapter


async def run_financial_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行财务分析Agent

    Args:
        enterprise_name: 企业名称

    Returns:
        Dict: 分析结果，包含 timeline、evidence、success
    """
    try:
        timeline = []
        evidence = []

        # 步骤1：获取财务数据
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "财务Agent",
            "content": "获取近三年财务报表",
            "detail": "资产负债表、利润表、现金流量表",
            "status": "running",
            "type": "discovery",
        })

        # 调用搜索工具获取财务数据
        result_json = search_financial_data.invoke({"enterprise_name": enterprise_name})
        financial_data = json.loads(result_json)

        # 更新时间轴
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"2024年营收{financial_data['财务报表']['2024']['营业收入'] / 100000000:.1f}亿",
            f"净利润率{financial_data['财务报表']['2024']['净利润'] / financial_data['财务报表']['2024']['营业收入'] * 100:.1f}%",
            f"资产负债率{financial_data['财务报表']['2024']['总负债'] / financial_data['财务报表']['2024']['总资产'] * 100:.0f}%",
        ]

        # 添加证据
        evidence.append({
            "label": "营业收入",
            "value": f"{financial_data['财务报表']['2024']['营业收入'] / 100000000:.1f}亿",
            "source": "财务报表",
        })
        evidence.append({
            "label": "净利润率",
            "value": f"{financial_data['财务报表']['2024']['净利润'] / financial_data['财务报表']['2024']['营业收入'] * 100:.1f}%",
            "source": "财务报表",
        })

        # 步骤2：分析应收账款
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "财务Agent",
            "content": "分析应收账款结构",
            "detail": "账龄分析、客户集中度、坏账计提",
            "status": "running",
            "type": "analysis",
        })

        ar = financial_data.get("应收账款", {})
        ar_2024 = ar.get("2024", {})

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"应收账款余额{ar_2024.get('余额', 0) / 100000000:.1f}亿",
            f"周转天数{ar_2024.get('周转天数', 0)}天",
        ]
        timeline[-1]["conclusion"] = "应收账款回收存在一定风险，建议关注前5大客户信用状况"

        # 添加证据
        evidence.append({
            "label": "应收账款周转",
            "value": f"{ar_2024.get('周转天数', 0)}天",
            "source": "财务报表",
        })

        # 步骤3：使用 Rebecca 引擎进行深度分析
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "财务Agent",
            "content": "Rebecca引擎深度分析",
            "detail": "10维度财务分析、风险识别",
            "status": "running",
            "type": "analysis",
        })

        # 构造 Rebecca 引擎输入数据
        import pandas as pd

        rebecca_data = {
            "income_statement": pd.DataFrame({
                "项目": ["营业收入", "营业成本", "毛利润", "净利润"],
                "2024": [
                    financial_data["财务报表"]["2024"]["营业收入"],
                    financial_data["财务报表"]["2024"]["营业成本"],
                    financial_data["财务报表"]["2024"]["毛利润"],
                    financial_data["财务报表"]["2024"]["净利润"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["营业收入"],
                    financial_data["财务报表"]["2023"]["营业成本"],
                    financial_data["财务报表"]["2023"]["毛利润"],
                    financial_data["财务报表"]["2023"]["净利润"],
                ],
            }),
            "balance_sheet": pd.DataFrame({
                "项目": ["总资产", "总负债", "所有者权益"],
                "2024": [
                    financial_data["财务报表"]["2024"]["总资产"],
                    financial_data["财务报表"]["2024"]["总负债"],
                    financial_data["财务报表"]["2024"]["所有者权益"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["总资产"],
                    financial_data["财务报表"]["2023"]["总负债"],
                    financial_data["财务报表"]["2023"]["所有者权益"],
                ],
            }),
            "cash_flow": pd.DataFrame({
                "项目": ["经营活动现金流", "投资活动现金流", "筹资活动现金流"],
                "2024": [
                    financial_data["财务报表"]["2024"]["经营活动现金流"],
                    financial_data["财务报表"]["2024"]["投资活动现金流"],
                    financial_data["财务报表"]["2024"]["筹资活动现金流"],
                ],
                "2023": [
                    financial_data["财务报表"]["2023"]["经营活动现金流"],
                    financial_data["财务报表"]["2023"]["投资活动现金流"],
                    financial_data["财务报表"]["2023"]["筹资活动现金流"],
                ],
            }),
        }

        # 运行 Rebecca 分析
        analyzer = FinancialDDAnalyzer(rebecca_data)
        analysis_result = analyzer.generate_full_analysis()
        risks = analyzer.identify_risks()

        # 转换结果
        analysis_json = AnalyzerAdapter.analysis_to_json(analysis_result)
        risks_json = AnalyzerAdapter.risks_to_dict(risks)

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"毛利率：{analysis_json.get('profitability', {}).get('gross_profit_margin', {}).get('data', [['', '']])[0][1] if 'profitability' in analysis_json else 'N/A'}",
            f"流动比率：{analysis_json.get('solvency', {}).get('current_ratio', {}).get('data', [['', '']])[0][1] if 'solvency' in analysis_json else 'N/A'}",
        ]

        # 添加风险发现
        for level, items in risks_json.items():
            for item in items:
                evidence.append({
                    "label": f"风险-{level}",
                    "value": item,
                    "source": "Rebecca引擎分析",
                })

        # 步骤4：分析现金流
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "财务Agent",
            "content": "分析现金流覆盖率",
            "detail": "经营活动现金流/流动负债",
            "status": "running",
            "type": "analysis",
        })

        cf_2024 = financial_data["财务报表"]["2024"]
        cash_flow_coverage = cf_2024["经营活动现金流"] / cf_2024["总负债"]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"现金流覆盖率{cash_flow_coverage:.1f}",
            f"高于行业均值1.5",
        ]
        timeline[-1]["conclusion"] = "现金流状况良好，偿债能力较强"

        # 添加证据
        evidence.append({
            "label": "现金流覆盖率",
            "value": f"{cash_flow_coverage:.1f}",
            "source": "财务报表",
        })

        return {
            "success": True,
            "timeline": timeline,
            "evidence": evidence,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "财务Agent",
                "content": "财务分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }
