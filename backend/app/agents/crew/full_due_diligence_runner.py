"""完整尽调运行器。

CrewAI 在完整尽调中承担综合审查职责；专项数据获取和结构化报告继续复用现有单 Agent。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.sub_agents.business_agent import run_business_agent
from app.agents.sub_agents.financial_agent import run_financial_agent, run_financial_agent_with_uploaded_data
from app.agents.sub_agents.public_financial_agent import run_public_financial_agent
from app.agents.sub_agents.industry_agent import run_industry_agent
from app.agents.sub_agents.legal_agent import run_legal_agent
from app.agents.sub_agents.full_report_builder import build_full_due_diligence_report
from app.agents.planning.report_mode_detector import detect_report_mode
from app.agents.evidence import normalize_evidence_list
from app.agents.tools.listed_company_tool import resolve_listed_company
from app.agents.tools.listed_company_public_info_tool import fetch_listed_company_public_info_data


def _timeline(agent: str, content: str, detail: str = "", status: str = "completed", event_type: str = "action") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


def _extract_report(result: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    return result.get(f"{key}_analysis_report")


def _summary_for_crew(sub_reports: Dict[str, Optional[Dict[str, Any]]]) -> str:
    compact = {}
    for key, report in sub_reports.items():
        if not report:
            compact[key] = {"status": "missing"}
            continue
        compact[key] = {
            "risk_rating": report.get("risk_rating"),
            "risk_score": report.get("risk_score"),
            "recommendation": report.get("recommendation"),
            "risk_summary": report.get("risk_summary", [])[:5],
            "generated_from": report.get("generated_from"),
        }
        if key == "industry":
            compact[key]["industry"] = report.get("industry", {})
        if key == "legal":
            compact[key]["summary"] = report.get("summary", {})
        if key == "business":
            basic_info = report.get("basic_info", {})
            compact[key]["basic_info"] = {
                name: value.get("value") if isinstance(value, dict) else value
                for name, value in list(basic_info.items())[:8]
            }
        if key == "financial":
            compact[key]["years"] = report.get("years", [])
    return json.dumps(compact, ensure_ascii=False, indent=2)


def run_crew_credit_review(
    enterprise_name: str,
    sub_reports: Dict[str, Optional[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """调用 CrewAI 做综合审查，失败时返回 None 由规则报告兜底。"""
    try:
        from crewai import Agent, Crew, Process, Task
        from app.agents.crew.roles import get_default_llm

        reviewer = Agent(
            role="授信尽调综合审查专家",
            goal="基于工商、财务、司法、行业四份专项报告形成可执行的授信审查意见",
            backstory="你是银行对公授信审批团队的资深审查人，擅长把专项尽调结果转化为准入判断、额度条件、贷后监控和补充尽调问题。",
            llm=get_default_llm(),
            verbose=False,
            allow_delegation=False,
            max_iter=2,
            memory=False,
        )
        task = Task(
            description=f"""请审查 {enterprise_name} 的四份专项尽调摘要，并只输出 JSON。

专项摘要：
{_summary_for_crew(sub_reports)}

输出 JSON 字段必须包含：
- executive_summary: 字符串数组，3-5条
- cross_findings: 数组，每项包含 title、risk_level、conclusion、evidence_refs
- credit_decision: 对象，包含 suggestion、credit_limit_advice、term_advice、collateral_advice、post_loan_monitoring
- due_diligence_questions: 字符串数组，5-8条
- recommendation: 一段最终授信建议

要求：结论必须基于输入摘要，不要编造企业没有提供的数据。""",
            expected_output="严格 JSON，不要 Markdown，不要代码块。",
            agent=reviewer,
        )
        crew = Crew(
            agents=[reviewer],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
            memory=False,
            max_rpm=3,
        )
        result = crew.kickoff(inputs={"enterprise_name": enterprise_name})
        text = str(result)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        parsed = json.loads(text[start:end])
        if not isinstance(parsed, dict):
            return None
        return parsed
    except Exception:
        return None


def _merge_result(
    bucket: Dict[str, Any],
    key: str,
    result: Dict[str, Any],
) -> None:
    bucket["timeline"].extend(result.get("timeline", []))
    bucket["evidence"].extend(normalize_evidence_list(result.get("evidence", []), agent=key))
    bucket["raw_results"][key] = result
    bucket["sub_reports"][key] = _extract_report(result, key)
    if not result.get("success"):
        bucket["errors"][key] = result.get("error", "专项分析失败")


async def run_full_due_diligence(
    enterprise_name: str,
    parsed_financial_data: Optional[Dict[str, Any]] = None,
    existing_context: Optional[Dict[str, Any]] = None,
    use_crew_review: bool = False,
) -> Dict[str, Any]:
    """运行完整尽调。"""
    bucket: Dict[str, Any] = existing_context or {
        "timeline": [],
        "evidence": [],
        "sub_reports": {"business": None, "financial": None, "legal": None, "industry": None},
        "raw_results": {},
        "errors": {},
    }

    bucket["timeline"].append(_timeline(
        "系统",
        "启动完整尽调流程",
        "工商、财务、司法、行业四个专项将汇总为统一授信审查报告",
        event_type="action",
    ))

    mode_info = detect_report_mode(enterprise_name, parsed_financial_data)
    report_mode = mode_info["report_mode"]
    bucket["report_mode"] = report_mode
    bucket["financial_data_status"] = mode_info["financial_data_status"]
    bucket["timeline"].append(_timeline(
        "Plan Agent",
        "判断尽调报告模式",
        mode_info["reason"],
        "completed",
        "analysis",
    ))

    listed_info = mode_info.get("listed_info") or resolve_listed_company(enterprise_name)
    public_info = bucket.get("listed_company_public_info")
    if listed_info and not public_info:
        bucket["timeline"].append(_timeline(
            "公开资料Agent",
            "采集上市公司公开资料包",
            "获取年报经营讨论、主营构成、诉讼公告、担保质押、行业地位和研报摘要",
            "completed",
            "discovery",
        ))
        public_info = fetch_listed_company_public_info_data(
            enterprise_name,
            listed_info.get("stock_code", ""),
            listed_info.get("stock_exchange", ""),
        )
        bucket["listed_company_public_info"] = public_info
        if public_info.get("success"):
            bucket["evidence"].extend(normalize_evidence_list(public_info.get("evidence", []), agent="public_info"))
            bucket["timeline"][-1]["findings"] = [
                f"主营构成 {len(public_info.get('main_business_composition', []))} 项",
                f"年报经营讨论：{(public_info.get('annual_business_review') or {}).get('report_name') or '已获取'}",
                f"公开搜索线索 {sum(len(items) for items in (public_info.get('search_clues') or {}).values())} 条",
            ]
        else:
            bucket["timeline"][-1]["findings"] = [public_info.get("error", "公开资料包获取失败")]

    if not existing_context:
        for key, runner, label in [
            ("business", run_business_agent, "工商专项分析"),
            ("industry", run_industry_agent, "行业专项分析"),
            ("legal", run_legal_agent, "司法专项分析"),
        ]:
            bucket["timeline"].append(_timeline("系统", f"执行{label}", "调用已验证的单Agent能力", "completed", "action"))
            result = await runner(enterprise_name, public_info=public_info) if key == "industry" else await runner(enterprise_name)
            _merge_result(bucket, key, result)

    if parsed_financial_data:
        bucket["timeline"].append(_timeline("系统", "执行财务专项分析", "使用用户上传近三年三大表", "completed", "action"))
        financial_result = await run_financial_agent_with_uploaded_data(enterprise_name, parsed_financial_data)
        _merge_result(bucket, "financial", financial_result)
    elif not bucket["sub_reports"].get("financial"):
        if listed_info:
            bucket["timeline"].append(_timeline("系统", "执行财务专项分析", "已识别上市公司，自动获取公开财报", "completed", "action"))
            financial_result = await run_financial_agent(enterprise_name)
            _merge_result(bucket, "financial", financial_result)
        else:
            bucket["timeline"].append(_timeline(
                "财务Agent",
                "执行公开资料财务预审",
                "非上市企业未上传财报，先基于公开线索生成预尽调财务章节",
                "completed",
                "action",
            ))
            financial_result = await run_public_financial_agent(enterprise_name, bucket["sub_reports"], bucket["evidence"])
            _merge_result(bucket, "financial", financial_result)

    crew_review = run_crew_credit_review(enterprise_name, bucket["sub_reports"]) if use_crew_review and report_mode != "public_pre_dd" else None
    report = build_full_due_diligence_report(
        enterprise_name=enterprise_name,
        sub_reports=bucket["sub_reports"],
        evidence=bucket["evidence"],
        crew_review=crew_review,
        report_mode=report_mode,
        financial_data_status=bucket.get("financial_data_status"),
    )
    if report_mode == "public_pre_dd":
        report["generated_from"] = "工商/司法/行业公开资料 + 公开财务线索预审"
    else:
        report["generated_from"] = "四个专项Agent + CrewAI综合审查" if crew_review else "四个专项Agent + 规则综合评分"
    bucket["timeline"].append(_timeline(
        "CrewAI 综合审查" if crew_review else "系统",
        "形成完整尽调综合结论",
        "已汇总工商、财务、司法、行业专项结果并生成统一授信建议" if report_mode != "public_pre_dd" else "已生成公开资料预尽调报告，财务结论待上传报表后增强",
        "completed",
        "conclusion",
    ))
    return {
        "success": True,
        "timeline": bucket["timeline"],
        "evidence": bucket["evidence"],
        "report": report,
        "full_due_diligence_context": bucket,
    }


def run_full_due_diligence_sync(
    enterprise_name: str,
    parsed_financial_data: Optional[Dict[str, Any]] = None,
    existing_context: Optional[Dict[str, Any]] = None,
    use_crew_review: bool = True,
) -> Dict[str, Any]:
    """同步包装，供 orchestrator 在线程节点中调用。"""
    return asyncio.run(run_full_due_diligence(
        enterprise_name=enterprise_name,
        parsed_financial_data=parsed_financial_data,
        existing_context=existing_context,
        use_crew_review=use_crew_review,
    ))
