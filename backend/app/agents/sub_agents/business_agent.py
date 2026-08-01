# ========================================
# 工商分析Agent
# 使用联网搜索获取企业工商信息
# ========================================

from typing import Dict, Any, List
from datetime import datetime
import uuid
import json

from app.agents.tools.business_search_tool import tavily_business_search
from app.agents.sub_agents.business_report_builder import build_business_analysis_report


async def run_business_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行工商分析Agent

    Args:
        enterprise_name: 企业名称

    Returns:
        Dict: 分析结果，包含 timeline、evidence、success
    """
    try:
        timeline = []
        evidence = []

        # 步骤1：获取工商信息（优先 Tavily 公开搜索）
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "获取企业工商信息",
            "detail": "统一社会信用代码、注册资本、经营范围",
            "status": "running",
            "type": "discovery",
        })

        search_result = None
        report = None

        search_json = tavily_business_search._run(enterprise_name=enterprise_name)
        search_result = json.loads(search_json)

        if search_result and search_result.get("success"):
            report = build_business_analysis_report(enterprise_name, search_result)
            result = {
                "统一社会信用代码": report.get("basic_info", {}).get("统一社会信用代码", {}).get("value", ""),
                "注册资本": report.get("basic_info", {}).get("注册资本", {}).get("value", ""),
                "成立日期": report.get("basic_info", {}).get("成立日期", {}).get("value", ""),
                "经营范围": report.get("basic_info", {}).get("经营范围", {}).get("value", ""),
                "股东信息": [],
                "对外投资": [],
            }
        else:
            report = _build_unavailable_business_report(enterprise_name, search_result)
            result = {
                "统一社会信用代码": "",
                "注册资本": "",
                "成立日期": "",
                "经营范围": "",
                "股东信息": [],
                "对外投资": [],
            }

        # 更新时间轴
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"成立于{result.get('成立日期', '未知')}",
            f"注册资本{result.get('注册资本', '未知')}",
            f"经营范围覆盖{result.get('经营范围', '未知')[:20]}...",
        ]
        if search_result and search_result.get("success"):
            timeline[-1]["detail"] = "Tavily 搜索 + 字段级来源置信度抽取"
            timeline[-1]["conclusion"] = "已生成结构化工商分析报告"
        else:
            timeline[-1]["detail"] = "公开搜索未取得稳定结果"
            timeline[-1]["conclusion"] = "工商数据源暂未形成可用证据链，需人工复核后再纳入正式授信判断"

        # 添加证据
        source_name = report.get("basic_info", {}).get("统一社会信用代码", {}).get("source_name", "Tavily 公开搜索") if search_result and search_result.get("success") else "公开搜索不可用"
        evidence.append({
            "label": "统一社会信用代码",
            "value": result.get("统一社会信用代码", ""),
            "source": source_name,
        })
        evidence.append({
            "label": "注册资本",
            "value": result.get("注册资本", ""),
            "source": report.get("basic_info", {}).get("注册资本", {}).get("source_name", source_name) if search_result and search_result.get("success") else source_name,
        })

        # 步骤2：分析股东结构
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "分析股东结构",
            "detail": "股东信息、持股比例",
            "status": "running",
            "type": "analysis",
        })

        shareholders = result.get("股东信息", [])
        findings = [f"{s['股东名称']}持股{s['持股比例']}" for s in shareholders]
        if report and not findings:
            controller = report.get("basic_info", {}).get("控股股东/实际控制人", {}).get("value")
            findings = [f"控股股东/实际控制人：{controller}"] if controller else ["公开搜索结果未稳定抽取股东结构，建议接入企业数据 API 补充"]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings

        # 步骤3：分析对外投资
        timeline.append({
            "id": str(uuid.uuid4()),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": "工商Agent",
            "content": "分析对外投资",
            "detail": "关联企业、投资关系",
            "status": "running",
            "type": "analysis",
        })

        investments = result.get("对外投资", [])
        findings = [f"{i['企业名称']}（持股{i['持股比例']}）" for i in investments]
        if report and not findings:
            findings = ["公开搜索结果未稳定抽取对外投资清单，建议接入企业数据 API 补充"]

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = findings
        timeline[-1]["conclusion"] = f"发现关联企业{len(investments)}家"

        # 添加证据
        evidence.append({
            "label": "关联企业",
            "value": f"{len(investments)}家",
            "source": "工商登记信息",
        })

        return {
            "success": True,
            "timeline": timeline,
            "evidence": evidence,
            "business_analysis_report": report,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [{
                "id": str(uuid.uuid4()),
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "工商Agent",
                "content": "工商分析失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
            "evidence": [],
        }


def _build_unavailable_business_report(enterprise_name: str, search_result: Dict[str, Any] | None) -> Dict[str, Any]:
    """公开搜索不可用时返回带数据边界的兜底报告。"""
    error = search_result.get("error", "公开搜索未取得稳定结果") if search_result else "未配置搜索工具"
    return {
        "report_type": "business_analysis",
        "enterprise_name": enterprise_name,
        "generated_from": "工商公开搜索不可用",
        "risk_rating": "medium",
        "risk_score": 55,
        "recommendation": "工商数据源暂未形成可用证据链，需人工复核国家企业信用信息公示系统后再纳入正式授信判断。",
        "basic_info": {
            "统一社会信用代码": {"value": "", "source_name": error},
            "注册资本": {"value": "", "source_name": error},
            "成立日期": {"value": "", "source_name": error},
            "经营范围": {"value": "", "source_name": error},
        },
        "shareholders": [],
        "investments": [],
        "risk_summary": [
            "工商公开搜索未取得稳定结果，当前不展示模拟信息或推断性结论。",
            "正式授信前需人工复核国家企业信用信息公示系统、天眼查/企查查等权威渠道。",
        ],
        "sections": [
            {"title": "一、工商基本信息", "summary": []},
            {"title": "二、股东与对外投资", "summary": []},
            {"title": "三、人工核验要求", "risks": ["公开搜索不可用，需人工补充工商材料。"]},
        ],
    }
