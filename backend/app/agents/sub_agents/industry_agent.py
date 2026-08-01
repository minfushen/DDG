# ========================================
# 行业分析Agent
# 基于行业代码库 + 本地行业知识库生成行业分析 MVP
# ========================================

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import json

from app.agents.tools.authoritative_business_tool import fetch_authoritative_business_info
from app.agents.tools.business_search_tool import tavily_business_search
from app.agents.tools.industry_classifier_tool import classify_industry_tool
from app.agents.sub_agents.industry_knowledge_context import build_industry_knowledge_context
from app.agents.sub_agents.industry_report_builder import build_industry_analysis_report
from app.rag.knowledge_retrieval_service import knowledge_hits_to_evidence, retrieve_knowledge
from app.config.rag_loader import get_knowledge_retrieval_top_k


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


def _public_info_context(public_info: Optional[Dict[str, Any]]) -> str:
    if not public_info or not public_info.get("success"):
        return ""
    basic = public_info.get("basic_info") or {}
    review = public_info.get("annual_business_review") or {}
    main_business = public_info.get("main_business_composition") or []
    clues = public_info.get("search_clues") or {}
    clue_text = " ".join(
        " ".join(str(item.get("content") or "")[:240] for item in items[:2])
        for items in clues.values()
    )
    return " ".join([
        str(basic.get("industry") or ""),
        str(basic.get("concepts") or ""),
        str(basic.get("main_business") or ""),
        str(basic.get("profile") or "")[:600],
        " ".join(f"{item.get('item_name')} {item.get('income')} {item.get('income_ratio')}" for item in main_business[:6]),
        str(review.get("business_review") or "")[:900],
        clue_text,
    ])


def _listed_company_business_scope(public_info: Optional[Dict[str, Any]]) -> str:
    """Use listed-company public information as a stable business context.

    For A-share companies we already fetch Eastmoney F10 and public clues. In
    that case, going back to a generic工商/搜索 channel can be slower and less
    precise than using the listed-company package directly.
    """
    if not public_info or not public_info.get("success"):
        return ""
    basic = public_info.get("basic_info") or {}
    rows = public_info.get("main_business_composition") or []
    parts = [
        str(basic.get("main_business") or ""),
        str(basic.get("industry") or ""),
        str(basic.get("concepts") or ""),
        " ".join(str(row.get("item_name") or "") for row in rows[:8] if isinstance(row, dict)),
    ]
    return " ".join(part for part in parts if part).strip()


async def run_industry_agent(
    enterprise_name: str,
    public_info: Optional[Dict[str, Any]] = None,
    annual_report_notes: Optional[Dict[str, Any]] = None,
    session_id: str | None = None,
    task_id: str | None = None,
    comparison: str | None = None,
    industry_segment: str | None = None,
) -> Dict[str, Any]:
    """运行行业分析Agent。

    ``comparison`` / ``industry_segment`` 来自多意图解析的 slots：
    - ``industry_segment`` 作为行业识别的强提示注入上下文，引导分类器偏向用户指定的细分方向；
    - ``comparison``（none/peer/self）透传给报告生成器，决定是否产出同业/纵向对比章节。
    """
    try:
        timeline = []
        evidence = []

        timeline.append(_timeline(
            "行业Agent",
            "获取经营上下文",
            "优先使用工商专项 API 的经营范围，失败时回退公开搜索摘要",
            event_type="discovery",
        ))
        listed_scope = _listed_company_business_scope(public_info)
        if listed_scope:
            business_scope = listed_scope
            extra_context = _public_info_context(public_info)
            context_result = {"success": True, "attempts": []}
            context_source = "上市公司公开资料包（东方财富F10 + 公开线索）"
        else:
            business_scope, extra_context, context_result, context_source = _extract_business_context(enterprise_name)
            listed_context = _public_info_context(public_info)
            if listed_context:
                extra_context = f"{extra_context} {listed_context}"
                context_source = f"{context_source} + 上市公司公开资料包"
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

        # 多意图槽位：行业细分方向作为强提示注入分类上下文
        if industry_segment:
            extra_context = f"{extra_context} 用户指定行业细分方向（重点参照）：{industry_segment}。"

        evidence.append({
            "label": "标准行业分类",
            "value": f"{classification.get('industry_code')} {classification.get('industry_name')}",
            "source": "industry_code4 国民经济行业四级代码表",
        })

        industry_knowledge_context = build_industry_knowledge_context(
            enterprise_name=classification.get("enterprise_name") or enterprise_name,
            classification=classification,
            public_info=public_info,
        )
        guide_query = industry_knowledge_context.get("query") or " ".join([
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
        retrieval_result = industry_knowledge_context.get("retrieval") or retrieve_knowledge(query=guide_query, domain="industry", top_k=get_knowledge_retrieval_top_k("industry"), company_name=enterprise_name)
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = [
            f"已检索本地行业指南（{retrieval_result.get('mode')}）",
            f"映射知识库：{', '.join(classification.get('guide_files', []))}",
            f"命中知识条目 {len(retrieval_result.get('results', []))} 条",
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
            public_info=public_info,
            industry_knowledge_context=industry_knowledge_context,
            annual_report_notes=annual_report_notes,
            session_id=session_id,
            task_id=task_id,
            comparison=comparison,
            industry_segment=industry_segment,
        )
        timeline[-1]["status"] = "completed"
        timeline[-1]["findings"] = report.get("risk_summary", [])
        timeline[-1]["conclusion"] = f"完成 {report.get('industry', {}).get('semantic_industry_name')} 行业知识库分析"

        evidence.extend(report.get("evidence", []))
        if public_info and public_info.get("success"):
            evidence.extend(public_info.get("evidence", []))
        evidence.extend(knowledge_hits_to_evidence(retrieval_result.get("results", []), agent="industry", domain="行业"))
        for rule in industry_knowledge_context.get("triggered_rules", []):
            evidence.append({
                "label": "行业分析触发规则",
                "value": f"{rule.get('rule_id')} {rule.get('title')}",
                "source": "industry_analysis_rules.json",
                "confidence": rule.get("confidence", 0.78),
            })
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
