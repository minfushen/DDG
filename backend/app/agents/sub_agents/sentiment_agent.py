# ========================================
# 舆情/声誉风险分析 Agent
# 通过公开网络搜索监测企业正/负舆情，输出声誉风险评级与核查要点。
# ========================================

from typing import Any, Dict

import uuid
from datetime import datetime

from app.agents.tools.sentiment_tool import search_enterprise_sentiment
from app.agents.sub_agents.sentiment_report_builder import build_sentiment_report


def _timeline(content: str, detail: str, status: str = "running", event_type: str = "analysis") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "舆情Agent",
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


async def run_sentiment_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行舆情分析 Agent。"""
    try:
        timeline = []
        evidence = []

        timeline.append(_timeline(
            "检索企业公开舆情",
            "Bocha 为主、SearXNG 兜底，覆盖负面/正面舆情线索",
            event_type="discovery",
        ))
        sentiment = search_enterprise_sentiment(enterprise_name)
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"数据源：{sentiment.get('provider')}",
            f"结果 {len(sentiment.get('results', []))} 条",
        ]
        if not sentiment.get("success"):
            timeline[-1]["conclusion"] = "公开搜索不可用，需人工监测舆情"
        else:
            timeline[-1]["conclusion"] = "已检索并分类企业舆情"

        report = build_sentiment_report(enterprise_name, sentiment)
        timeline.append(_timeline(
            "分析声誉风险结构",
            "按正/中/负分类，识别权威源负面与重大舆情",
            event_type="analysis",
        ))
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"负面 {report['summary'].get('负面')} 条 / 权威源负面 {report['summary'].get('权威源负面')} 条",
        ]
        timeline[-1]["conclusion"] = f"声誉风险评级：{report.get('risk_rating')}"

        timeline.append(_timeline(
            "形成舆情结论",
            "输出风险评级、声誉风险与核查要点",
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
            "sentiment_analysis_report": report,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [_timeline("舆情分析失败", str(e), "completed", "risk")],
            "evidence": [],
        }
