# ========================================
# 司法分析Agent
# 权威司法网站可用性探测 + Tavily 公开搜索兜底
# ========================================

from typing import Dict, Any
from datetime import datetime
import uuid
import json

from app.agents.tools.authoritative_legal_tool import probe_authoritative_legal_sources
from app.agents.tools.legal_search_tool import tavily_legal_search
from app.agents.sub_agents.legal_report_builder import build_legal_analysis_report


def _timeline(content: str, detail: str, status: str = "running", event_type: str = "analysis") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "司法Agent",
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


async def run_legal_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行司法分析Agent。"""
    try:
        timeline = []
        evidence = []

        timeline.append(_timeline(
            "探测权威司法数据源",
            "裁判文书网、执行信息公开网等站点是否存在稳定结构化 API",
            event_type="discovery",
        ))
        authority_probe = json.loads(probe_authoritative_legal_sources._run(enterprise_name=enterprise_name))
        attempts = authority_probe.get("attempts", [])
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [item.get("reason", "") for item in attempts if item.get("reason")]
        timeline[-1]["conclusion"] = "权威司法直连通道不可用，回退公开搜索"

        timeline.append(_timeline(
            "搜索公开司法风险线索",
            "裁判文书、被执行、失信、行政处罚、开庭公告",
            event_type="discovery",
        ))
        search_result = json.loads(tavily_legal_search._run(enterprise_name=enterprise_name))
        report = None
        if search_result.get("success"):
            report = build_legal_analysis_report(enterprise_name, search_result, authority_probe)
            timeline[-1]["status"] = "completed"
            timeline[-1]["detail"] = "Tavily 公开搜索 + 字段级来源置信度"
            timeline[-1]["findings"] = [
                f"搜索结果 {len(search_result.get('results', []))} 条",
                f"形成司法线索 {len(report.get('legal_items', []))} 条",
            ]
            timeline[-1]["conclusion"] = "已生成结构化司法风险报告"
        else:
            timeline[-1]["status"] = "completed"
            timeline[-1]["findings"] = [search_result.get("error", "公开搜索不可用，需人工复核权威司法渠道")]
            report = _build_unavailable_legal_report(enterprise_name, authority_probe)

        summary = report.get("summary", {})
        timeline.append(_timeline(
            "分析司法风险结构",
            "按裁判文书、被执行、失信、行政处罚、开庭公告归类",
            event_type="analysis",
        ))
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"裁判文书线索 {summary.get('裁判文书', 0)} 条",
            f"被执行线索 {summary.get('被执行', 0)} 条",
            f"失信/限高线索 {summary.get('失信', 0)} 条",
            f"行政处罚线索 {summary.get('行政处罚', 0)} 条",
        ]
        timeline[-1]["conclusion"] = report.get("recommendation")

        timeline.append(_timeline(
            "形成司法风险结论",
            "输出风险评级、风险提示和核验建议",
            event_type="conclusion",
        ))
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = report.get("risk_summary", [])
        timeline[-1]["conclusion"] = f"司法风险评级：{report.get('risk_rating')}，评分：{report.get('risk_score')}"

        evidence.extend(report.get("evidence", []))
        return {
            "success": True,
            "timeline": timeline,
            "evidence": evidence,
            "legal_analysis_report": report,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [_timeline("司法分析失败", str(e), "completed", "risk")],
            "evidence": [],
        }


def _build_unavailable_legal_report(enterprise_name: str, authority_probe: Dict[str, Any]) -> Dict[str, Any]:
    summary = {
        "裁判文书": 0,
        "被执行": 0,
        "失信": 0,
        "行政处罚": 0,
        "开庭公告": 0,
    }
    risk_summary = [
        "司法公开搜索未取得稳定结果，当前不展示模拟案件或推断性结论。",
        "正式授信前需人工复核裁判文书网、中国执行信息公开网、信用中国和市场监管处罚信息。",
    ]
    return {
        "report_type": "legal_analysis",
        "enterprise_name": enterprise_name,
        "generated_from": "司法公开搜索不可用",
        "risk_rating": "medium",
        "risk_score": 55,
        "recommendation": "司法数据源暂未形成可用证据链，需人工复核后再纳入正式授信判断。",
        "summary": summary,
        "legal_items": [],
        "sections": [
            {"title": "一、司法风险概览", "summary": [{"label": key, "value": value} for key, value in summary.items()]},
            {"title": "二、权威源可用性", "attempts": authority_probe.get("attempts", [])},
            {"title": "三、人工核验要求", "risks": risk_summary},
        ],
        "risk_summary": risk_summary,
        "evidence": [{"label": "司法数据边界", "value": "公开搜索未取得稳定结果", "source": "系统判定"}],
    }
