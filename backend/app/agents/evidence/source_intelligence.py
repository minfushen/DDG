"""Source grading and lightweight field extraction for public evidence."""

from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urlparse


AUTHORITY_DOMAINS = {
    "gsxt.gov.cn": ("official_business_registry", "high"),
    "samr.gov.cn": ("official_business_registry", "high"),
    "creditchina.gov.cn": ("official_credit_publicity", "high"),
    "court.gov.cn": ("official_judicial_source", "high"),
    "zxgk.court.gov.cn": ("official_judicial_source", "high"),
    "wenshu.court.gov.cn": ("official_judicial_source", "high"),
    "cninfo.com.cn": ("exchange_announcement", "high"),
    "sse.com.cn": ("exchange_announcement", "high"),
    "szse.cn": ("exchange_announcement", "high"),
    "eastmoney.com": ("financial_market_data", "medium"),
    "qcc.com": ("commercial_business_data", "medium"),
    "tianyancha.com": ("commercial_business_data", "medium"),
}

BUSINESS_FIELD_PATTERNS = {
    "统一社会信用代码": [r"统一社会信用代码(?:为)?[:：\s]*([0-9A-Z]{18})"],
    "法定代表人": [r"法定代表人(?:为)?[:：\s]*([\u4e00-\u9fa5A-Za-z·]{2,20})"],
    "注册资本": [r"注册资本(?:为)?(?:人民币)?[:：\s]*([0-9,.]+\s*[万亿]?元(?:人民币)?)"],
    "成立日期": [r"成立(?:日期|时间)[:：\s]*(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})"],
    "经营状态": [r"经营状态[:：\s]*([^\n。；;，,]{2,30})"],
    "注册地址": [r"(?:住所|注册地址|注册地)[:：\s]*([^\n。；;]{6,120})"],
    "经营范围": [r"经营范围[:：\s]*(.{20,300}?)(?:统一社会信用代码|法定代表人|注册资本|\n\n|$)"],
}

BUSINESS_SOURCE_HINTS = [
    "国家企业信用", "企业信用信息", "信用中国", "工商", "营业执照", "登记信息",
    "天眼查", "企查查", "爱企查", "启信宝", "建设库", "水滴信用", "信用视界",
]

BUSINESS_SOURCE_NOISE_HINTS = [
    "股东研究", "财务分析", "行情", "证券信息", "发行日期", "上市日期", "公司公告",
    "个股", "研报", "新闻", "问询函", "债券", "分红", "十大股东", "东方财富", "同花顺",
]

BUSINESS_VALUE_NOISE_HINTS = [
    "证券信息", "发行日期", "上市日期", "上市交易所", "证券类型", "流通股本", "总股本",
    "主承销商", "发行价", "市盈率", "换手率", "特别处理", "退市", "联系方式",
    "公司章程", "更新时间", "基础信息", "所属概念", "所属地域",
]

CASE_NO_PATTERN = re.compile(r"[（(]?\d{4}[）)]?[\u4e00-\u9fa5]{0,8}\d{1,8}[\u4e00-\u9fa5]{1,5}\d+号")
LEGAL_SIGNAL_PATTERNS = {
    "裁判文书": ["裁判文书", "民事判决", "民事裁定", "判决书", "裁定书", "案号"],
    "被执行": ["被执行人", "执行标的", "执行法院", "立案时间"],
    "失信限高": ["失信被执行", "限制高消费", "限高", "履行情况"],
    "行政处罚": ["行政处罚", "处罚决定", "罚款", "处罚机关", "违法行为"],
    "重大诉讼公告": ["重大诉讼", "仲裁公告", "诉讼公告", "累计诉讼"],
}

INDUSTRY_ANCHOR_KEYWORDS = {
    "行业定位": ["主营业务", "行业地位", "市场地位", "龙头", "细分领域", "所属行业"],
    "周期判断": ["周期", "景气", "复苏", "下行", "去库存", "产能利用率", "需求疲软"],
    "竞争格局": ["竞争格局", "市场份额", "CR", "集中度", "同行", "龙头企业", "价格竞争"],
    "政策环境": ["政策", "监管", "补贴", "准入", "限制", "鼓励", "产业政策"],
    "授信关注点": ["风险", "应收", "回款", "现金流", "客户集中", "供应商", "产能", "担保", "质押"],
}


def collect_result_text(item: Dict[str, Any]) -> str:
    return re.sub(
        r"\s+",
        " ",
        "\n".join(str(item.get(key) or "") for key in ["title", "content", "snippet", "summary", "raw_content", "value", "claim"]),
    ).strip()


def grade_source(url: str | None = None, title: str | None = None, source: str | None = None) -> Dict[str, Any]:
    raw = " ".join([url or "", title or "", source or ""]).lower()
    host = urlparse(url or "").netloc.lower().replace("www.", "")
    for domain, (source_type, trust) in AUTHORITY_DOMAINS.items():
        if domain in host or domain in raw:
            return {
                "source_type": source_type,
                "trust_level": trust,
                "confidence": 0.9 if trust == "high" else 0.74,
                "authority_label": domain,
            }
    if any(keyword in raw for keyword in ["国家企业信用", "信用中国", "裁判文书", "中国执行信息公开"]):
        return {"source_type": "official_named_source", "trust_level": "high", "confidence": 0.86, "authority_label": "named_authority"}
    if any(keyword in raw for keyword in ["公告", "年报", "交易所", "巨潮"]):
        return {"source_type": "public_disclosure", "trust_level": "high", "confidence": 0.84, "authority_label": "public_disclosure"}
    if any(keyword in raw for keyword in ["证券", "财经", "新闻", "研报", "东方财富", "同花顺"]):
        return {"source_type": "commercial_or_media_public_source", "trust_level": "medium", "confidence": 0.68, "authority_label": "public_media"}
    return {"source_type": "public_web_search_clue", "trust_level": "low", "confidence": 0.5, "authority_label": "web_clue"}


def _looks_like_business_source(text: str, grade: Dict[str, Any]) -> bool:
    source_type = grade.get("source_type")
    if source_type in {"official_business_registry", "official_credit_publicity", "commercial_business_data", "official_named_source"}:
        return True
    if any(keyword in text for keyword in BUSINESS_SOURCE_NOISE_HINTS):
        return False
    return any(keyword in text for keyword in BUSINESS_SOURCE_HINTS)


def _valid_business_value(field: str, value: str) -> bool:
    if not value:
        return False
    if field == "统一社会信用代码":
        return bool(re.fullmatch(r"[0-9A-Z]{18}", value))
    if field == "法定代表人":
        if value in {"统一社会信用代码", "法定代表人", "注册资本"}:
            return False
        if re.search(r"[0-9A-Z]{6,}|代码|信用|注册|资本|公司|证券|信息|日期", value):
            return False
        return bool(re.fullmatch(r"[\u4e00-\u9fa5A-Za-z·]{2,12}", value))
    if field == "注册资本":
        return bool(re.search(r"\d", value)) and not any(keyword in value for keyword in ["发行价", "市盈率", "换手率"])
    if field == "经营范围":
        if any(keyword in value for keyword in BUSINESS_VALUE_NOISE_HINTS):
            return False
        return any(keyword in value for keyword in ["研发", "生产", "制造", "销售", "技术", "服务", "经营", "进出口", "许可"])
    if field in {"经营状态", "成立日期", "注册地址"}:
        return not any(keyword in value for keyword in BUSINESS_VALUE_NOISE_HINTS)
    return True


def extract_business_fields(text: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for field, patterns in BUSINESS_FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.S)
            if not match:
                continue
            value = re.sub(r"\s+", " ", match.group(1)).strip(" ：:，,。；;")
            if value and len(value) <= 320 and _valid_business_value(field, value):
                fields[field] = value
                break
    return fields


def extract_legal_signals(text: str) -> Dict[str, Any]:
    case_numbers = list(dict.fromkeys(CASE_NO_PATTERN.findall(text)))[:8]
    signal_types: List[str] = []
    for label, keywords in LEGAL_SIGNAL_PATTERNS.items():
        if any(keyword in text for keyword in keywords):
            signal_types.append(label)
    amounts = list(dict.fromkeys(re.findall(r"[0-9,.]+\s*(?:万元|亿元|元|万欧元|万美元)", text)))[:6]
    return {"signal_types": signal_types, "case_numbers": case_numbers, "amounts": amounts}


def _sentences(text: str) -> List[str]:
    return [item.strip() for item in re.split(r"[。！？!?\n]", text or "") if len(item.strip()) >= 12]


def extract_industry_anchors(text: str) -> Dict[str, List[str]]:
    sentences = _sentences(text)
    anchors: Dict[str, List[str]] = {}
    for label, keywords in INDUSTRY_ANCHOR_KEYWORDS.items():
        hits = []
        for sentence in sentences:
            if any(keyword in sentence for keyword in keywords):
                hits.append(sentence[:220])
            if len(hits) >= 3:
                break
        if hits:
            anchors[label] = hits
    return anchors


def enrich_public_result(item: Dict[str, Any], category: str) -> Dict[str, Any]:
    text = collect_result_text(item)
    grade = grade_source(item.get("url") or item.get("source_url"), item.get("title") or item.get("label"), item.get("source") or item.get("source_name"))
    extracted: Dict[str, Any] = {}
    if category == "business":
        source_probe = " ".join(str(item.get(key) or "") for key in ["url", "source_url", "title", "label", "source", "source_name", "site_name", "content", "snippet"])
        extracted["business_fields"] = extract_business_fields(text) if _looks_like_business_source(source_probe, grade) else {}
    if category == "legal":
        extracted["legal_signals"] = extract_legal_signals(text)
    if category == "industry":
        extracted["industry_anchors"] = extract_industry_anchors(text)
    return {**grade, "extracted_fields": extracted, "text_excerpt": text[:500]}


def summarize_extracted_fields(evidence: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    refs: Dict[str, str] = {}
    for item in evidence:
        fields = (((item.get("metadata") or {}).get("extracted_fields") or {}).get(key) or {})
        for field, value in fields.items():
            if field not in merged and value:
                merged[field] = value
                refs[field] = item.get("id") or ""
    return {"fields": merged, "refs": refs}
