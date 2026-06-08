"""企业工商分析报告生成器。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import re


FIELD_PATTERNS = {
    "统一社会信用代码": [r"统一社会信用代码(?:为)?[:：\s]*([0-9A-Z]{18})"],
    "法定代表人": [r"法定代表人[:：\s]*([\u4e00-\u9fa5A-Za-z·]{2,8})(?:\s|。|；|;|，|,|$)"],
    "注册资本": [r"注册资本(?:为)?(?:人民币)?[:：\s]*([0-9,.]+\s*[万亿]元(?:人民币)?)", r"注册资本(?:为)?(?:人民币)?[:：\s]*([0-9,.]+\s*万元)"] ,
    "成立日期": [r"成立日期[:：\s]*(\d{4}[-年]\d{1,2}[-月]\d{1,2})", r"成立时间[:：\s]*(\d{4}/\d{1,2}/\d{1,2})"],
    "企业类型": [r"企业类型[:：\s]*([^\n。；;]{2,40})", r"公司为永久存续的([^\n。；;]{2,30})"],
    "注册地址": [r"公司住所[:：\s]*([^\n。；;]{6,120})", r"注册地[:：\s]*([^\n。；;]{6,80})", r"注册地址[:：\s]*([^\n。；;]{6,80})", r"位置[:：\s]*([^\n。；;]{6,80})"],
    "经营范围": [r"(?:主要)?经营范围[:：\s]*(.{20,260}?)(?:控股股东|股票|统一社会信用代码|\n\n|$)"],
    "控股股东/实际控制人": [r"控股股东、实际控制人[:：\s]*([^\n。；;]{2,60})", r"实际控制人[:：\s]*([^\n。；;]{2,60})"],
    "股票代码": [r"股票代码[:：\s]*([0-9]{6})"],
    "股票简称": [r"股票简称[:：\s]*([\u4e00-\u9fa5A-Za-z0-9]{2,20})", r"股票名称[:：\s]*([\u4e00-\u9fa5A-Za-z0-9]{2,20})"],
}

FIELD_BLOCKLIST = {
    "法定代表人": {"签名的", "代表人签", "签名", "公司章", "资格的有效证明"},
}


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_field(text: str, field: str) -> Optional[str]:
    if field == "法定代表人":
        table_match = re.search(r"\|\s*([\u4e00-\u9fa5]{2,4})\s*\|[^\n]{0,160}法定代表人", text)
        if table_match:
            return table_match.group(1).strip()

    for pattern in FIELD_PATTERNS.get(field, []):
        match = re.search(pattern, text, re.S)
        if match:
            value = _clean_text(match.group(1))
            value = value.strip("：: ，,。；;")
            if value in FIELD_BLOCKLIST.get(field, set()):
                continue
            if field == "法定代表人" and any(bad in value for bad in ["证明", "资格", "董事长", "公司", "为"]):
                continue
            return value
    return None


def _is_valid_field_value(field: str, value: str, result: Dict[str, Any]) -> bool:
    title = result.get("title", "") or ""
    url = result.get("url", "") or ""
    if any(keyword in title for keyword in ["是什么", "您真的了解吗"]):
        return False
    if "cods.org.cn" in url and field != "统一社会信用代码":
        return False
    if field in {"经营范围", "企业类型"} and any(keyword in title for keyword in ["增资", "问询函", "交易", "合伙企业"]):
        return False
    if field == "经营范围" and any(keyword in value for keyword in ["未上市企业的投资", "非公开发行股票", "金融产品投资"]):
        return False
    if field == "控股股东/实际控制人" and any(keyword in value for keyword in ["机制", "冻结", "侵占", "清偿", "公司章程", "规范", "汽车电池", "欣瑞恒泰"]):
        return False
    if field == "注册地址" and any(keyword in title for keyword in ["增资", "交易"]) and "公司住所" not in value:
        return False
    return True


def _target_relevance(result: Dict[str, Any], enterprise_name: str) -> float:
    text = f"{result.get('title', '')}\n{result.get('content', '')}\n{result.get('raw_content', '')}"
    if enterprise_name and enterprise_name in text:
        return 0.25
    short_name = enterprise_name.replace("电子股份有限公司", "").replace("股份有限公司", "")
    if len(short_name) >= 2 and short_name in text:
        return 0.12
    return 0


def _field_source(results: List[Dict[str, Any]], field: str, enterprise_name: str) -> Optional[Dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda item: (
            item.get("confidence", 0) + _target_relevance(item, enterprise_name),
            item.get("score", 0),
        ),
        reverse=True,
    )
    fallback: Optional[Dict[str, Any]] = None
    no_low_confidence_fallback_fields = {"经营范围", "控股股东/实际控制人"}
    for result in ranked:
        text = f"{result.get('title', '')}\n{result.get('content', '')}\n{result.get('raw_content', '')}"
        value = _extract_field(text, field)
        if value and _is_valid_field_value(field, value, result):
            source = {
                "value": value,
                "source_name": result.get("title") or "公开搜索结果",
                "source_url": result.get("url"),
                "confidence": result.get("confidence", 0.55),
                "trust_level": result.get("trust_level", "low"),
            }
            if result.get("trust_level") in {"high", "medium"} or enterprise_name in text:
                return source
            if field not in no_low_confidence_fallback_fields and not fallback:
                fallback = source
    return fallback


def _answer_field(answer: str, field: str) -> Optional[str]:
    if field == "统一社会信用代码":
        match = re.search(r"[0-9A-Z]{18}", answer or "")
        return match.group(0) if match else None
    if field == "法定代表人":
        match = re.search(r"legal representative is ([A-Za-z ]+)|法定代表人(?:是|为)?([\u4e00-\u9fa5A-Za-z·]{2,20})", answer or "")
        if match:
            return (match.group(1) or match.group(2) or "").strip()
    if field == "注册资本":
        match = re.search(r"registered capital of ([0-9,.]+\s*(?:million|billion|万|亿)?\s*yuan)|注册资本(?:为)?([0-9,.]+\s*[万亿]?元)", answer or "", re.I)
        if match:
            return (match.group(1) or match.group(2) or "").strip()
    return None


def build_business_analysis_report(enterprise_name: str, search_data: Dict[str, Any]) -> Dict[str, Any]:
    """基于 Tavily 搜索结果生成结构化工商分析报告。"""
    results = search_data.get("results", [])
    answer = search_data.get("answer", "")
    normalized_name = search_data.get("enterprise_name") or enterprise_name
    fields = [
        "统一社会信用代码", "法定代表人", "注册资本", "成立日期", "企业类型",
        "注册地址", "经营范围", "控股股东/实际控制人", "股票代码", "股票简称",
    ]
    basic_info: Dict[str, Dict[str, Any]] = {}
    for field in fields:
        source = _field_source(results, field, normalized_name)
        if not source:
            answer_value = _answer_field(answer, field)
            if answer_value:
                source = {
                    "value": answer_value,
                    "source_name": "Tavily 搜索摘要",
                    "source_url": None,
                    "confidence": 0.6,
                    "trust_level": "low",
                }
        if source:
            basic_info[field] = source

    evidence = []
    for field, item in basic_info.items():
        evidence.append({
            "label": field,
            "value": str(item.get("value", "")),
            "source": item.get("source_name") or item.get("source_url") or "公开搜索结果",
        })

    trusted_sources = [item for item in results if item.get("trust_level") in {"high", "medium"}]
    risk_summary = []
    if "统一社会信用代码" not in basic_info:
        risk_summary.append("未能从公开搜索结果中稳定识别统一社会信用代码，建议通过国家企业信用信息公示系统复核。")
    if "法定代表人" not in basic_info:
        risk_summary.append("法定代表人字段缺失，需补充权威工商登记数据。")
    if not trusted_sources:
        risk_summary.append("本次检索未命中高/中可信度来源，当前工商结论仅可作为辅助参考。")
    if not risk_summary:
        risk_summary.append("已命中高/中可信度公开来源，基础工商字段具备初步可核验性。")

    sections = [
        {
            "title": "一、工商基础信息",
            "rows": [
                {
                    "field": field,
                    "value": basic_info.get(field, {}).get("value", "数据不可用"),
                    "source": basic_info.get(field, {}).get("source_name", "未识别"),
                    "confidence": basic_info.get(field, {}).get("confidence", 0),
                    "trust_level": basic_info.get(field, {}).get("trust_level", "unknown"),
                }
                for field in fields
            ],
            "analysis": [
                f"本次工商分析基于 Tavily 搜索获取 {len(results)} 条公开结果，其中高/中可信来源 {len(trusted_sources)} 条。",
                "字段级结论均保留来源和置信度；搜索摘要字段仅作为兜底参考，后续建议接入权威工商数据 API。",
            ],
        },
        {
            "title": "二、来源可信度",
            "sources": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "trust_level": item.get("trust_level"),
                    "confidence": item.get("confidence"),
                }
                for item in results[:8]
            ],
        },
        {
            "title": "三、风险提示",
            "risks": risk_summary,
        },
    ]

    return {
        "report_type": "business_analysis",
        "enterprise_name": normalized_name,
        "generated_from": "Tavily 公开搜索",
        "basic_info": basic_info,
        "sections": sections,
        "risk_summary": risk_summary,
        "evidence": evidence,
        "raw_answer": answer,
    }


def build_authoritative_business_report(enterprise_name: str, registry_data: Dict[str, Any]) -> Dict[str, Any]:
    """基于企业工商专项 API 返回结果生成结构化工商分析报告。"""
    fields = [
        "企业名称", "统一社会信用代码", "法定代表人", "注册资本", "成立日期", "经营状态",
        "企业类型", "注册地址", "经营范围", "注册号", "组织机构代码", "股票代码", "股票简称",
    ]
    basic_info = registry_data.get("basic_info", {}) or {}
    generated_from = registry_data.get("generated_from") or "企业工商专项 API"
    rows = [
        {
            "field": field,
            "value": basic_info.get(field, {}).get("value", "数据不可用"),
            "source": basic_info.get(field, {}).get("source_name", "未识别"),
            "confidence": basic_info.get(field, {}).get("confidence", 0),
            "trust_level": basic_info.get(field, {}).get("trust_level", "unknown"),
        }
        for field in fields
    ]
    evidence = [
        {
            "label": field,
            "value": str(item.get("value", "")),
            "source": item.get("source_name") or generated_from,
        }
        for field, item in basic_info.items()
    ]
    risk_summary = []
    if "统一社会信用代码" not in basic_info:
        risk_summary.append("专项工商 API 未返回统一社会信用代码，需人工复核工商登记信息。")
    if "经营范围" not in basic_info:
        risk_summary.append("专项工商 API 未返回经营范围，需补充经营范围或营业执照影像材料。")
    if not risk_summary:
        risk_summary.append("已命中企业工商专项 API，基础工商字段具备较高可核验性。")

    return {
        "report_type": "business_analysis",
        "enterprise_name": registry_data.get("enterprise_name") or enterprise_name,
        "generated_from": generated_from,
        "basic_info": basic_info,
        "sections": [
            {
                "title": "一、工商基础信息",
                "rows": rows,
                "analysis": [
                    f"本次工商分析优先采用 {generated_from} 返回的结构化工商数据。",
                    "字段级结论保留来源和置信度；缺失字段不再由低可信搜索结果强行填充。",
                ],
            },
            {
                "title": "二、来源可信度",
                "sources": [
                    {
                        "title": generated_from,
                        "url": next((item.get("source_url") for item in basic_info.values() if item.get("source_url")), None),
                        "trust_level": "high",
                        "confidence": 0.92,
                    }
                ],
            },
            {
                "title": "三、风险提示",
                "risks": risk_summary,
            },
        ],
        "risk_summary": risk_summary,
        "evidence": evidence,
        "raw_record": registry_data.get("raw_record"),
        "provider": registry_data.get("provider"),
    }
