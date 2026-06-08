"""司法风险分析报告生成器。"""

from __future__ import annotations

from typing import Any, Dict, List
import re


CASE_NO_PATTERN = re.compile(r"[（(]\d{4}[）)]?[\u4e00-\u9fa5]{0,6}\d{2,6}[\u4e00-\u9fa5]{1,4}\d+号")
CAUSE_KEYWORDS = ["买卖合同纠纷", "合同纠纷", "劳动争议", "建设工程", "金融借款", "票据追索", "侵权", "行政处罚"]
RISK_KEYWORDS = {
    "裁判文书": ["裁判文书", "民事判决", "民事裁定", "案号", "纠纷"],
    "被执行": ["被执行人", "执行标的", "执行案件", "执行法院"],
    "失信": ["失信被执行", "限制高消费", "限高"],
    "行政处罚": ["行政处罚", "处罚决定", "罚款", "市场监督", "环保处罚", "税务处罚"],
    "开庭公告": ["开庭公告", "开庭时间", "法院公告"],
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _collect_text(result: Dict[str, Any]) -> str:
    return _clean("\n".join([result.get("title", ""), result.get("content", ""), result.get("raw_content", "")]))


def _classify_item(text: str) -> List[str]:
    labels = []
    for label, keywords in RISK_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            labels.append(label)
    return labels or ["司法公开线索"]


def _is_target_related(text: str, enterprise_name: str) -> bool:
    short_name = enterprise_name.replace("股份有限公司", "").replace("有限公司", "").replace("集团", "")
    return enterprise_name in text or (len(short_name) >= 3 and short_name in text)


def _has_substantive_signal(label: str, text: str, case_numbers: List[str]) -> bool:
    if label == "裁判文书":
        return bool(case_numbers) or any(cause in text for cause in CAUSE_KEYWORDS)
    if label == "被执行":
        return bool(case_numbers) or any(keyword in text for keyword in ["执行标的", "执行法院", "立案时间", "案号", "元"])
    if label == "失信":
        return bool(case_numbers) or any(keyword in text for keyword in ["履行情况", "限制高消费", "限高", "执行法院", "案号"])
    if label == "行政处罚":
        return any(keyword in text for keyword in ["处罚决定", "罚款", "处罚机关", "处罚金额", "行政处罚决定书"])
    if label == "开庭公告":
        return any(keyword in text for keyword in ["开庭时间", "案由", "案号", "法院"])
    return True


def _extract_causes(text: str) -> List[str]:
    return [keyword for keyword in CAUSE_KEYWORDS if keyword in text]


def _risk_level(summary: Dict[str, int], trusted_count: int) -> tuple[str, int, str]:
    if summary.get("失信", 0) > 0 or summary.get("被执行", 0) >= 2:
        return "high", 45, "建议暂缓授信，需核实执行/失信记录及清偿情况"
    if summary.get("被执行", 0) > 0 or summary.get("行政处罚", 0) > 0 or summary.get("裁判文书", 0) >= 3:
        return "medium", 65, "建议谨慎授信，重点核验涉诉金额、案件状态和处罚整改情况"
    if trusted_count == 0:
        return "medium", 70, "公开搜索未命中高可信来源，建议人工复核司法公开网站"
    return "low", 85, "公开搜索未发现重大司法风险线索，可结合权威网站人工复核"


def build_legal_analysis_report(
    enterprise_name: str,
    search_data: Dict[str, Any],
    authority_probe: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """基于 Tavily 搜索结果生成结构化司法风险报告。"""
    results = search_data.get("results", []) or []
    answer = search_data.get("answer", "")
    normalized_name = search_data.get("enterprise_name") or enterprise_name

    legal_items = []
    summary = {label: 0 for label in RISK_KEYWORDS}
    for item in results:
        text = _collect_text(item)
        if not _is_target_related(text, normalized_name):
            continue
        case_numbers = list(dict.fromkeys(CASE_NO_PATTERN.findall(text)))[:3]
        labels = [label for label in _classify_item(text) if _has_substantive_signal(label, text, case_numbers)]
        causes = _extract_causes(text)
        if not labels and not case_numbers and not causes:
            continue
        for label in labels:
            if label in summary:
                summary[label] += 1
        legal_items.append({
            "title": item.get("title") or "公开司法线索",
            "url": item.get("url"),
            "types": labels,
            "case_numbers": case_numbers,
            "causes": causes,
            "excerpt": text[:260],
            "source": item.get("title") or item.get("url") or "公开搜索结果",
            "trust_level": item.get("trust_level", "low"),
            "confidence": item.get("confidence", 0.55),
        })

    trusted_count = len([item for item in legal_items if item.get("trust_level") in {"high", "medium"}])
    risk_rating, risk_score, recommendation = _risk_level(summary, trusted_count)
    authority_attempts = (authority_probe or {}).get("attempts", [])
    risk_summary = []
    if legal_items:
        if summary.get("失信", 0):
            risk_summary.append("搜索结果出现失信/限高相关线索，需优先到中国执行信息公开网核验主体、案号和履行状态。")
        if summary.get("被执行", 0):
            risk_summary.append("搜索结果出现被执行相关线索，需核验执行标的金额、立案时间和是否已履行完毕。")
        if summary.get("行政处罚", 0):
            risk_summary.append("搜索结果出现行政处罚相关线索，需核验处罚机关、处罚金额和整改情况。")
        if not risk_summary:
            risk_summary.append("公开搜索发现司法相关线索，但未识别到失信、被执行或处罚等高风险关键词。")
    else:
        risk_summary.append("公开搜索未稳定识别裁判文书、被执行、失信或行政处罚记录，建议人工复核权威司法网站。")

    sections = [
        {
            "title": "一、司法风险概览",
            "summary": [
                {"label": "裁判文书线索", "value": summary.get("裁判文书", 0)},
                {"label": "被执行线索", "value": summary.get("被执行", 0)},
                {"label": "失信/限高线索", "value": summary.get("失信", 0)},
                {"label": "行政处罚线索", "value": summary.get("行政处罚", 0)},
                {"label": "开庭公告线索", "value": summary.get("开庭公告", 0)},
            ],
            "analysis": [
                f"本次司法分析基于 Tavily 搜索获取 {len(results)} 条公开结果，形成 {len(legal_items)} 条可读司法风险线索。",
                "权威司法网站无稳定公开结构化 API，搜索结果仅作为线索，正式授信前需人工复核案号、主体和案件状态。",
            ],
        },
        {
            "title": "二、司法线索明细",
            "items": legal_items[:12],
        },
        {
            "title": "三、权威源可用性",
            "attempts": authority_attempts,
        },
        {
            "title": "四、风险提示",
            "risks": risk_summary,
        },
    ]

    evidence = [
        {"label": "司法风险评级", "value": f"{risk_rating}/{risk_score}", "source": "公开搜索线索汇总"},
        {"label": "司法线索", "value": f"{len(legal_items)}条", "source": "Tavily 公开搜索"},
    ]
    if authority_attempts:
        evidence.append({
            "label": "权威源直连",
            "value": "不可用，已回退公开搜索",
            "source": "裁判文书网/执行信息公开网探测",
        })

    return {
        "report_type": "legal_analysis",
        "enterprise_name": normalized_name,
        "generated_from": "Tavily 公开搜索 + 权威司法网站可用性探测",
        "risk_rating": risk_rating,
        "risk_score": risk_score,
        "recommendation": recommendation,
        "summary": summary,
        "legal_items": legal_items,
        "sections": sections,
        "risk_summary": risk_summary,
        "evidence": evidence,
        "raw_answer": answer,
    }
