# ========================================
# 关联网络分析 Agent
# 整合股权、担保/质押、上下游供应链等关联数据，呈现企业在关联网络中的
# 位置与影响力，并输出关联风险标签与评级。
# ========================================

from typing import Any, Dict, Optional

import uuid
from datetime import datetime

from app.agents.tools.relationship_network_tool import build_relationship_network
from app.agents.sub_agents.relationship_report_builder import build_relationship_report


def _timeline(content: str, detail: str, status: str = "running", event_type: str = "analysis") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "关联网络Agent",
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


async def run_relationship_agent(
    enterprise_name: str,
    stock_code: Optional[str] = None,
    industry_name: Optional[str] = None,
) -> Dict[str, Any]:
    """运行关联网络分析 Agent。"""
    try:
        timeline = []
        evidence = []

        timeline.append(_timeline(
            "探测股权与关联数据源",
            "优先巨潮/东方财富（上市）或元典企业工商（非上市），整合股东、实控人、担保、质押与冻结",
            event_type="discovery",
        ))
        network = build_relationship_network(
            enterprise_name, stock_code=stock_code, industry_name=industry_name
        )
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"数据源：{network.get('data_source')}",
            f"股东 {len(network.get('shareholders', []))} 个 / 对外担保 {len(network.get('guarantees', []))} 笔 / 股权冻结 {len(network.get('equity_freeze', []))} 项",
        ]
        timeline[-1]["conclusion"] = "已构建企业关联网络"

        report = build_relationship_report(enterprise_name, network)
        timeline.append(_timeline(
            "分析股权结构与关联风险",
            "识别实控人、担保圈、股权质押/冻结与上下游位置",
            event_type="analysis",
        ))
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"实际控制人：{report['summary'].get('实际控制人')}",
            f"关联风险标签 {len(report.get('risk_tags', []))} 项",
        ]
        timeline[-1]["conclusion"] = f"关联风险评级：{report.get('risk_rating')}"

        timeline.append(_timeline(
            "形成关联网络结论",
            "输出风险评级、关联信号与核查要点",
            event_type="conclusion",
        ))
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = report.get("risk_summary", [])
        timeline[-1]["conclusion"] = report.get("recommendation")

        evidence.extend(report.get("evidence", []))
        return {
            "success": True,
            "timeline": timeline,
            "evidence": evidence,
            "relationship_analysis_report": report,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [_timeline("关联网络分析失败", str(e), "completed", "risk")],
            "evidence": [],
        }
