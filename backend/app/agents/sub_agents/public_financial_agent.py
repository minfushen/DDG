"""Public-information financial pre-check for private companies.

This agent is used when a target company is not recognized as listed and no
financial statements have been uploaded. It must not invent financial ratios;
instead it summarizes public operating clues and states which metrics remain
unavailable until statements are provided.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.rag.knowledge_retrieval_service import knowledge_hits_to_evidence, retrieve_knowledge


UNAVAILABLE_METRICS = [
    "近三年营业收入增长率",
    "主营业务毛利率",
    "销售净利率",
    "资产负债率",
    "流动比率",
    "速动比率",
    "经营活动现金流量净额",
    "经营现金流/贷款本息覆盖倍数",
    "应收账款周转天数",
    "存货周转天数",
    "银行授信余额及对外担保规模",
]


REQUIRED_DOCUMENTS = [
    "近三年审计报告或年度财务报表",
    "最近一期资产负债表、利润表、现金流量表",
    "近12个月主要结算账户银行流水",
    "近12个月纳税申报表和完税证明",
    "前五大客户及供应商清单、主要销售/采购合同",
    "应收账款账龄表、存货明细表",
    "银行授信、借款、票据、担保及或有负债明细",
    "本次贷款用途对应的采购合同、订单或营销服务合同",
]


PUBLIC_CLUE_KEYWORDS = [
    "销售收入",
    "营收",
    "生产总值",
    "出口",
    "创汇",
    "订单",
    "基地",
    "产能",
    "冷库",
    "生产线",
    "认证",
    "HACCP",
    "ISO",
    "龙头企业",
    "地理标志",
    "商标",
    "专利",
]


def _timeline(content: str, detail: str = "", status: str = "completed", event_type: str = "analysis") -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": "财务Agent",
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }


def _text_from_report(report: Optional[Dict[str, Any]]) -> str:
    if not report:
        return ""
    pieces: List[str] = []
    for key in ["recommendation", "raw_answer", "generated_from"]:
        value = report.get(key)
        if value:
            pieces.append(str(value))
    for item in report.get("risk_summary") or []:
        pieces.append(str(item))
    for item in report.get("evidence") or []:
        pieces.append(" ".join(str(item.get(field, "")) for field in ["label", "value", "source"]))
    for section in report.get("sections") or []:
        for field in ["analysis", "risks", "signals"]:
            for value in section.get(field) or []:
                pieces.append(str(value))
        for row in section.get("rows") or []:
            pieces.append(" ".join(str(value) for value in row.values()))
    basic_info = report.get("basic_info") or {}
    for field, value in basic_info.items():
        if isinstance(value, dict):
            pieces.append(f"{field} {value.get('value', '')} {value.get('source_name', '')}")
        else:
            pieces.append(f"{field} {value}")
    return "\n".join(pieces)


def _extract_public_clues(sub_reports: Dict[str, Optional[Dict[str, Any]]], evidence: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    clues: List[Dict[str, str]] = []
    seen = set()

    for item in evidence:
        label = str(item.get("label") or "")
        value = str(item.get("value") or "")
        source = str(item.get("source") or "公开资料")
        text = f"{label} {value}"
        if any(keyword.lower() in text.lower() for keyword in PUBLIC_CLUE_KEYWORDS) and value:
            key = (label, value, source)
            if key not in seen:
                seen.add(key)
                clues.append({"label": label or "公开线索", "value": value, "source": source})

    combined_text = "\n".join(_text_from_report(report) for report in sub_reports.values())
    for keyword in PUBLIC_CLUE_KEYWORDS:
        pattern = rf"[^。；\n]*{re.escape(keyword)}[^。；\n]*"
        for match in re.findall(pattern, combined_text, flags=re.IGNORECASE):
            sentence = re.sub(r"\s+", " ", match).strip(" ，,。；;")
            if len(sentence) < 8:
                continue
            key = (keyword, sentence)
            if key in seen:
                continue
            seen.add(key)
            clues.append({"label": keyword, "value": sentence[:140], "source": "工商/行业/司法公开资料摘要"})
            if len(clues) >= 8:
                return clues

    return clues[:8]


def build_public_financial_report(
    enterprise_name: str,
    sub_reports: Dict[str, Optional[Dict[str, Any]]],
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a financial pre-check report without fabricating unavailable metrics."""
    evidence = evidence or []
    clues = _extract_public_clues(sub_reports, evidence)
    if not clues:
        clues = [
            {
                "label": "经营基础",
                "value": "公开资料暂未稳定提取收入、产能或出口等量化线索，需通过访谈和资料清单补充核验。",
                "source": "公开资料预尽调",
            }
        ]

    risk_summary = [
        "未获取近三年财务报表，暂无法计算偿债能力、盈利能力和营运效率核心指标。",
        "当前财务判断仅可作为公开资料预尽调结论，不应替代正式授信财务审查。",
        "授信审批前需补充财报、银行流水、纳税申报、合同订单和担保明细。",
    ]

    retrieval = retrieve_knowledge(
        query=f"{enterprise_name} 非上市企业 财报缺失 公开资料预尽调 中小企业财务审查 待补充材料 额度边界",
        domain="financial",
        top_k=5,
        company_name=enterprise_name,
    )
    knowledge_hits = retrieval.get("results", [])
    knowledge_evidence = knowledge_hits_to_evidence(knowledge_hits, agent="financial", domain="财务")
    public_evidence = [
        {
            "label": item["label"],
            "value": item["value"],
            "source": item["source"],
            "confidence": 0.55,
            "trust_level": "low",
            "requires_manual_review": True,
        }
        for item in clues[:6]
    ] + [
        {
            "label": "财务数据边界",
            "value": "未上传近三年财务报表",
            "source": "系统判定",
            "confidence": 1,
            "trust_level": "high",
            "requires_manual_review": False,
        },
    ] + knowledge_evidence

    return {
        "success": True,
        "timeline": [
            _timeline("进入公开资料财务预审", "未识别为上市公司且未上传财务报表，不硬算缺失指标", "completed", "discovery"),
            _timeline("提炼公开经营线索", f"已形成 {len(clues)} 条公开线索，重点用于辅助判断经营基础", "completed", "analysis"),
            _timeline("检索财务审查知识库", f"命中 {len(knowledge_hits)} 条财报缺失、SME 财务审查和公开预尽调话术", "completed", "discovery"),
            _timeline("列出财务核验缺口", f"{len(UNAVAILABLE_METRICS)} 项核心财务指标需待财报补充", "completed", "risk"),
        ],
        "evidence": public_evidence,
        "financial_analysis_report": {
            "report_type": "financial_analysis",
            "enterprise_name": enterprise_name,
            "risk_rating": "medium",
            "risk_score": 58,
            "recommendation": "当前仅完成公开资料财务预审，需补充近三年财报后再形成正式偿债能力和额度判断。",
            "generated_from": "公开资料预尽调（未上传财报）",
            "financial_data_status": "public_clues_only",
            "available_clues": clues,
            "unavailable_metrics": UNAVAILABLE_METRICS,
            "required_documents": REQUIRED_DOCUMENTS,
            "credit_boundary": "本财务结论仅用于贷前初筛和访谈准备，不可替代正式财务审查或授信审批依据。",
            "knowledge_hits": knowledge_hits,
            "sections": [
                {
                    "title": "一、公开财务与经营线索",
                    "subsections": [
                        {
                            "title": "可用公开线索",
                            "analysis": [f"{item['label']}：{item['value']}（来源：{item['source']}）" for item in clues],
                        }
                    ],
                },
                {
                    "title": "二、不可计算指标与资料缺口",
                    "subsections": [
                        {
                            "title": "不可计算指标",
                            "risks": UNAVAILABLE_METRICS,
                            "analysis": ["上述指标需依赖企业近三年三大财务报表、银行流水和纳税资料，不应基于公开资料推断。"],
                        },
                        {
                            "title": "需补充材料",
                            "risks": REQUIRED_DOCUMENTS,
                        },
                    ],
                },
                {
                    "title": "三、知识库依据",
                    "subsections": [
                        {
                            "title": "命中的财务审查知识",
                            "analysis": [
                                f"{hit.get('title')}：{(hit.get('content') or '')[:180]}"
                                for hit in knowledge_hits[:5]
                            ] or ["未命中可用知识库条目。"],
                        }
                    ],
                },
            ],
            "risk_summary": risk_summary,
        },
    }


async def run_public_financial_agent(
    enterprise_name: str,
    sub_reports: Dict[str, Optional[Dict[str, Any]]],
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return build_public_financial_report(enterprise_name, sub_reports, evidence)
