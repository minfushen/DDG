# ========================================
# 行业分析Agent
# 基于行业代码库 + 本地行业知识库生成行业分析 MVP
# ========================================

from typing import Dict, Any, Tuple
from datetime import datetime
import uuid
import json

from app.agents.tools.authoritative_business_tool import fetch_authoritative_business_info
from app.agents.tools.business_search_tool import tavily_business_search
from app.agents.tools.industry_classifier_tool import classify_industry_tool
from app.agents.tools.rag_tool import search_industry_knowledge
from app.agents.sub_agents.industry_report_builder import build_industry_analysis_report


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _timeline(agent: str, content: str, detail: str, status: str = "running", event_type: str = "analysis") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": _now(),
        "agent": agent,
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


def _extract_business_context(enterprise_name: str) -> Tuple[str, str, Dict[str, Any], str]:
    """获取经营范围和补充上下文。"""
    registry_result = json.loads(fetch_authoritative_business_info._run(enterprise_name=enterprise_name))
    if registry_result.get("success"):
        basic_info = registry_result.get("basic_info", {})
        business_scope = basic_info.get("经营范围", {}).get("value", "")
        extra_context = " ".join([
            basic_info.get("企业名称", {}).get("value", ""),
            basic_info.get("企业类型", {}).get("value", ""),
            basic_info.get("经营范围", {}).get("value", ""),
        ])
        return business_scope, extra_context, registry_result, registry_result.get("generated_from", "企业工商专项 API")

    search_result = json.loads(tavily_business_search._run(enterprise_name=enterprise_name))
    if search_result.get("success"):
        results = search_result.get("results", [])
        extra_context = " ".join([
            search_result.get("enterprise_name", enterprise_name),
            search_result.get("answer", ""),
            " ".join((item.get("content") or "")[:500] for item in results[:3]),
        ])
        return "", extra_context, search_result, "Tavily 公开搜索"

    return "", enterprise_name, registry_result, "企业名称"


async def run_industry_agent(enterprise_name: str) -> Dict[str, Any]:
    """运行行业分析Agent。"""
    try:
        timeline = []
        evidence = []

        timeline.append(_timeline(
            "行业Agent",
            "获取经营上下文",
            "优先使用工商专项 API 的经营范围，失败时回退公开搜索摘要",
            event_type="discovery",
        ))
        business_scope, extra_context, context_result, context_source = _extract_business_context(enterprise_name)
        timeline[-1]["status"] = "completed"
        timeline[-1]["detail"] = f"上下文来源：{context_source}"
        timeline[-1]["findings"] = [
            f"经营范围：{business_scope[:80]}" if business_scope else "经营范围未稳定获取，使用企业名和公开摘要补充判断",
        ]

        timeline.append(_timeline(
            "行业Agent",
            "识别标准行业分类",
            "基于 industry_code4 四级行业代码表匹配行业路径",
            event_type="analysis",
        ))
        classification = json.loads(classify_industry_tool._run(
            enterprise_name=enterprise_name,
            business_scope=business_scope,
            extra_context=extra_context,
        ))
        if not classification.get("success"):
            return {
                "success": False,
                "error": classification.get("error", "行业识别失败"),
                "timeline": timeline + [_timeline(
                    "行业Agent",
                    "行业识别失败",
                    classification.get("error", "未识别到标准行业分类"),
                    "completed",
                    "risk",
                )],
                "evidence": evidence,
            }

        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"标准行业：{' > '.join(classification.get('industry_path', []))}",
            f"行业码：{classification.get('industry_code')}",
            f"置信度：{round(classification.get('confidence', 0) * 100)}%",
        ]
        timeline[-1]["conclusion"] = classification.get("semantic_industry_name") or classification.get("industry_name")

        evidence.append({
            "label": "标准行业分类",
            "value": f"{classification.get('industry_code')} {classification.get('industry_name')}",
            "source": "industry_code4 国民经济行业四级代码表",
        })

        guide_query = " ".join([
            enterprise_name,
            classification.get("semantic_industry_name") or "",
            classification.get("industry_name") or "",
            "行业尽调 风险 指标 授信审查",
        ])
        timeline.append(_timeline(
            "行业Agent",
            "调用行业知识库",
            f"知识库文件：{', '.join(classification.get('guide_files', []))}",
            event_type="discovery",
        ))
        retrieval_result = json.loads(search_industry_knowledge._run(query=guide_query, knowledge_type="guide"))
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            "已检索本地行业指南",
            f"映射知识库：{', '.join(classification.get('guide_files', []))}",
        ]

        timeline.append(_timeline(
            "行业Agent",
            "生成行业分析报告",
            "按行业识别、尽调重点、指标阈值、行业风险、核验路径组织结论",
            event_type="conclusion",
        ))
        report = build_industry_analysis_report(
            enterprise_name=classification.get("enterprise_name") or enterprise_name,
            classification=classification,
            retrieval_result=retrieval_result,
        )
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = report.get("risk_summary", [])
        timeline[-1]["conclusion"] = f"完成 {report.get('industry', {}).get('semantic_industry_name')} 行业知识库分析"

        evidence.extend(report.get("evidence", []))
        if context_result.get("attempts"):
            evidence.append({
                "label": "工商上下文通道",
                "value": "；".join(item.get("reason", "") for item in context_result.get("attempts", []) if item.get("reason")),
                "source": "工商上下文获取过程",
            })

        return {
            "success": True,
            "timeline": timeline,
            "evidence": evidence,
            "industry_analysis_report": report,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timeline": [_timeline(
                "行业Agent",
                "行业分析失败",
                str(e),
                "completed",
                "risk",
            )],
            "evidence": [],
        }
