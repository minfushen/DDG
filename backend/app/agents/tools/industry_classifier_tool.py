# ========================================
# 行业分类工具
# 基于国民经济行业四级代码表 + 经营范围/企业名关键词识别目标行业
# ========================================

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json
import re

from app.config import settings
from app.agents.tools.industry_llm_classifier import adjudicate_industry_with_llm
from app.agents.tools.listed_company_tool import resolve_listed_company


class ClassifyIndustryInput(BaseModel):
    """行业分类输入。"""

    enterprise_name: str = Field(description="企业名称或用户输入")
    business_scope: str = Field(default="", description="经营范围或主营业务描述")
    extra_context: str = Field(default="", description="搜索摘要、上市公司资料等补充上下文")


INDUSTRY_CODE_PATH = settings.BASE_DIR / "knowledge_base" / "industry_codes" / "industry_code4.json"


GUIDE_MAP = {
    "new_energy": ["lithium_battery.md", "new_energy.md", "manufacturing.md"],
    "semiconductor": ["technology.md", "manufacturing.md"],
    "construction": ["construction.md"],
    "manufacturing": ["manufacturing.md"],
    "technology": ["technology.md"],
    "internet_saas": ["internet_saas.md", "technology.md"],
    "healthcare": ["healthcare.md"],
    "biopharma": ["biopharma.md", "healthcare.md"],
    "energy": ["energy.md"],
    "real_estate": ["real_estate.md"],
    "retail": ["retail.md"],
    "logistics": ["logistics.md"],
    "agriculture": ["agriculture.md"],
    "education": ["education.md"],
    "hotel_tourism": ["hotel_tourism.md"],
    "trade_import_export": ["trade_import_export.md"],
}


SEMANTIC_RULES = [
    {
        "semantic_industry_id": "semiconductor",
        "semantic_industry_name": "半导体/集成电路产业链",
        "keywords": ["半导体", "集成电路", "芯片", "电子器件", "功率器件", "分立器件", "硅片", "晶圆", "mems", "传感器", "led芯片"],
        "preferred_codes": ["3973", "3972", "3971", "397", "39"],
        "confidence_bonus": 0.22,
    },
    {
        "semantic_industry_id": "new_energy",
        "semantic_industry_name": "新能源/锂电池产业链",
        "keywords": ["锂离子电池", "锂电池", "动力电池", "储能", "电池制造", "电芯", "pack", "bms", "新能源车", "光伏设备"],
        "preferred_codes": ["3841", "384", "3825", "3612"],
        "confidence_bonus": 0.18,
    },
    {
        "semantic_industry_id": "construction",
        "semantic_industry_name": "建筑/工程施工",
        "keywords": ["房屋建筑", "建筑工程", "工程施工", "施工总承包", "市政工程", "土木工程", "工程承包", "建筑装修", "工程管理"],
        "preferred_codes": ["479", "471", "47", "48", "481", "489", "509"],
        "confidence_bonus": 0.16,
    },
    {
        "semantic_industry_id": "internet_saas",
        "semantic_industry_name": "互联网/SaaS/软件服务",
        "keywords": ["软件开发", "saas", "云平台", "信息系统", "互联网", "数据处理", "人工智能", "软件服务"],
        "preferred_codes": ["651", "6511", "6512", "6513", "6519", "64", "65"],
        "confidence_bonus": 0.15,
    },
    {
        "semantic_industry_id": "biopharma",
        "semantic_industry_name": "生物医药",
        "keywords": ["生物药", "医药制造", "药品", "疫苗", "基因工程", "医疗器械", "临床试验"],
        "preferred_codes": ["27", "276", "2761", "2762", "358"],
        "confidence_bonus": 0.15,
    },
    {
        "semantic_industry_id": "real_estate",
        "semantic_industry_name": "房地产",
        "keywords": ["房地产开发", "商品房", "物业管理", "房地产租赁", "土地开发"],
        "preferred_codes": ["70", "701", "7010", "702", "704"],
        "confidence_bonus": 0.15,
    },
    {
        "semantic_industry_id": "logistics",
        "semantic_industry_name": "物流/运输",
        "keywords": ["道路运输", "货物运输", "物流", "仓储", "供应链", "快递", "网络货运"],
        "preferred_codes": ["54", "58", "59", "60"],
        "confidence_bonus": 0.14,
    },
    {
        "semantic_industry_id": "trade_import_export",
        "semantic_industry_name": "贸易/进出口",
        "keywords": ["货物进出口", "技术进出口", "进出口代理", "国际贸易", "批发", "贸易"],
        "preferred_codes": ["51", "52", "518", "519"],
        "confidence_bonus": 0.12,
    },
]

LISTED_COMPANY_INDUSTRY_HINTS = {
    "欣旺达": {
        "extra_keywords": "锂离子电池 动力电池 储能系统 消费类电池 电池制造",
        "semantic_industry_id": "new_energy",
        "semantic_industry_name": "新能源/锂电池产业链",
    },
    "欣旺达电子股份有限公司": {
        "extra_keywords": "锂离子电池 动力电池 储能系统 消费类电池 电池制造",
        "semantic_industry_id": "new_energy",
        "semantic_industry_name": "新能源/锂电池产业链",
    },
    "宁德时代": {
        "extra_keywords": "动力电池 储能 电池制造 新能源",
        "semantic_industry_id": "new_energy",
        "semantic_industry_name": "新能源/锂电池产业链",
    },
    "比亚迪": {
        "extra_keywords": "新能源汽车 动力电池 汽车制造 电池制造",
        "semantic_industry_id": "new_energy",
        "semantic_industry_name": "新能源汽车/动力电池",
    },
    "士兰微": {
        "extra_keywords": "半导体 集成电路 芯片 电子器件 功率器件 分立器件 led芯片 mems传感器",
        "semantic_industry_id": "semiconductor",
        "semantic_industry_name": "半导体/集成电路产业链",
    },
    "杭州士兰微电子股份有限公司": {
        "extra_keywords": "半导体 集成电路 芯片 电子器件 功率器件 分立器件 led芯片 mems传感器",
        "semantic_industry_id": "semiconductor",
        "semantic_industry_name": "半导体/集成电路产业链",
    },
}


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").lower().strip()


def _flatten_nodes(nodes: List[Dict[str, Any]], path: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, Any]]:
    path = path or []
    rows = []
    for node in nodes:
        current = {"name": node.get("text", ""), "code": str(node.get("value", ""))}
        current_path = path + [current]
        children = node.get("children") or []
        row = {
            "code": current["code"],
            "name": current["name"],
            "level": len(current_path),
            "path": [item["name"] for item in current_path],
            "path_codes": [item["code"] for item in current_path],
        }
        rows.append(row)
        if children:
            rows.extend(_flatten_nodes(children, current_path))
    return rows


@lru_cache(maxsize=1)
def load_industry_codes() -> List[Dict[str, Any]]:
    data = json.loads(Path(INDUSTRY_CODE_PATH).read_text(encoding="utf-8"))
    return _flatten_nodes(data)


def _name_tokens(name: str) -> List[str]:
    tokens = [name]
    for suffix in ["制造", "服务", "施工", "开发", "批发", "零售", "经营", "管理", "活动"]:
        if suffix in name and len(name.replace(suffix, "")) >= 2:
            tokens.append(name.replace(suffix, ""))
    return list(dict.fromkeys([item for item in tokens if len(item) >= 2]))


def _score_code(row: Dict[str, Any], context: str) -> tuple[float, List[str]]:
    score = 0.0
    signals = []
    path_text = " ".join(row["path"])
    for name in reversed(row["path"]):
        for token in _name_tokens(name):
            if token and token.lower() in context:
                weight = 0.16 if len(row["code"]) == 4 else 0.08
                if token == row["name"]:
                    weight += 0.08
                score += weight
                signals.append(f"命中行业关键词：{token}（{path_text}）")
    return score, signals[:5]


def _semantic_match(context: str) -> Optional[Dict[str, Any]]:
    candidates = []
    for rule in SEMANTIC_RULES:
        hits = [kw for kw in rule["keywords"] if kw.lower() in context]
        if not hits:
            continue
        score = min(0.35 + len(hits) * 0.08 + rule["confidence_bonus"], 0.92)
        candidate = {**rule, "hits": hits, "score": score}
        candidates.append(candidate)
    if not candidates:
        return None
    dominant_manufacturing = next(
        (item for item in candidates if item["semantic_industry_id"] in {"semiconductor", "new_energy"}),
        None,
    )
    if dominant_manufacturing:
        return dominant_manufacturing
    return max(candidates, key=lambda item: item["score"])


def classify_industry(enterprise_name: str, business_scope: str = "", extra_context: str = "") -> Dict[str, Any]:
    listed_company = resolve_listed_company(enterprise_name)
    listed_hint = None
    for keyword, hint in LISTED_COMPANY_INDUSTRY_HINTS.items():
        if keyword in enterprise_name:
            listed_hint = hint
            break

    context_parts = [enterprise_name, business_scope, extra_context]
    if listed_company:
        context_parts.extend([listed_company.get("security_name", ""), listed_company.get("company_name", "")])
    if listed_hint:
        context_parts.append(listed_hint.get("extra_keywords", ""))
    context = _clean_text(" ".join(context_parts))

    rows = load_industry_codes()
    scored = []
    for row in rows:
        score, signals = _score_code(row, context)
        if score > 0:
            scored.append({**row, "score": score, "signals": signals})

    semantic = _semantic_match(context)
    if semantic:
        for row in rows:
            if row["code"] in semantic["preferred_codes"]:
                code_bonus = 0.08 if row["code"] in {"479", "471", "3841", "3973"} else 0
                scored.append({
                    **row,
                    "score": min(semantic["score"] + code_bonus, 0.95),
                    "signals": [f"命中语义行业：{semantic['semantic_industry_name']}，关键词：{', '.join(semantic['hits'])}"],
                })

    if listed_hint:
        preferred_codes = {"3841", "384", "38", "C"}
        if listed_hint.get("semantic_industry_id") == "semiconductor":
            preferred_codes = {"3973", "3972", "3971", "397", "39", "C"}
        for row in rows:
            if row["code"] in preferred_codes:
                scored.append({
                    **row,
                    "score": 0.9 if listed_hint.get("semantic_industry_id") == "semiconductor" else 0.88,
                    "signals": [f"上市公司映射提示：{listed_hint['semantic_industry_name']}"],
                })

    if not scored:
        return {
            "success": False,
            "enterprise_name": enterprise_name,
            "error": "未能基于企业名称、经营范围或补充上下文识别行业",
            "confidence": 0,
            "candidates": [],
        }

    scored = sorted(scored, key=lambda item: (item["score"], item["level"], len(item["code"])), reverse=True)
    best = scored[0]
    semantic_id = semantic.get("semantic_industry_id") if semantic else None
    semantic_name = semantic.get("semantic_industry_name") if semantic else None
    if listed_hint:
        semantic_id = listed_hint.get("semantic_industry_id") or semantic_id
        semantic_name = listed_hint.get("semantic_industry_name") or semantic_name

    if not semantic_id:
        semantic_id, semantic_name = _semantic_from_code(best)

    candidates = []
    seen = set()
    for item in scored[:12]:
        key = item["code"]
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "code": item["code"],
            "name": item["name"],
            "level": item["level"],
            "path": item["path"],
            "path_codes": item["path_codes"],
            "score": round(min(item["score"], 0.95), 3),
            "signals": item["signals"],
        })

    llm_adjudication: Dict[str, Any] = {"success": False}
    should_use_llm = bool(candidates) and (len(extra_context or "") > 50 or bool(listed_company) or len(candidates) >= 2)
    if should_use_llm:
        llm_adjudication = adjudicate_industry_with_llm(enterprise_name, business_scope, extra_context, candidates)
        if llm_adjudication.get("success"):
            selected_code = llm_adjudication.get("selected_code")
            selected = next((item for item in scored if str(item.get("code")) == str(selected_code)), None)
            if selected:
                best = selected
                if llm_adjudication.get("semantic_industry_id"):
                    semantic_id = llm_adjudication.get("semantic_industry_id")
                if llm_adjudication.get("semantic_industry_name"):
                    semantic_name = llm_adjudication.get("semantic_industry_name")

    confidence = round(min(max(best["score"], 0.35), 0.95), 3)
    if llm_adjudication.get("success") and llm_adjudication.get("confidence"):
        confidence = round(min(max(float(llm_adjudication.get("confidence")), 0.35), 0.99), 3)
    matched_signals = list(best["signals"])
    if llm_adjudication.get("success") and llm_adjudication.get("reason"):
        matched_signals = [f"LLM语义裁判：{llm_adjudication.get('reason')}"] + matched_signals

    return {
        "success": True,
        "enterprise_name": listed_company.get("company_name") if listed_company and listed_company.get("company_name") else enterprise_name,
        "industry_code": best["code"],
        "industry_name": best["name"],
        "industry_path": best["path"],
        "industry_path_codes": best["path_codes"],
        "semantic_industry_id": semantic_id,
        "semantic_industry_name": semantic_name,
        "guide_files": GUIDE_MAP.get(semantic_id, _guide_files_from_code(best)),
        "confidence": confidence,
        "matched_signals": matched_signals,
        "candidates": candidates,
        "classification_source": "llm_adjudicated" if llm_adjudication.get("success") else "rule_fallback",
        "llm_reason": llm_adjudication.get("reason") if llm_adjudication.get("success") else "",
        "ignored_noise": llm_adjudication.get("ignored_noise") if llm_adjudication.get("success") else [],
        "llm_elapsed_ms": llm_adjudication.get("elapsed_ms") if llm_adjudication.get("success") else None,
        "llm_error": llm_adjudication.get("error") if should_use_llm and not llm_adjudication.get("success") else "",
    }


def _semantic_from_code(row: Dict[str, Any]) -> tuple[str, str]:
    code = row["code"]
    path_text = " ".join(row["path"])
    if code.startswith("47") or code.startswith("48") or "建筑" in path_text:
        return "construction", "建筑/工程施工"
    if code.startswith("65") or "软件" in path_text:
        return "internet_saas", "互联网/SaaS/软件服务"
    if code.startswith("27") or "医药" in path_text:
        return "biopharma", "生物医药"
    if code.startswith("70") or "房地产" in path_text:
        return "real_estate", "房地产"
    if code.startswith("54") or code.startswith("58") or code.startswith("59") or "物流" in path_text:
        return "logistics", "物流/运输"
    if row["path_codes"][0] == "A":
        return "agriculture", "农业/养殖业"
    if row["path_codes"][0] == "C":
        return "manufacturing", "制造业"
    return "manufacturing", row["path"][0]


def _guide_files_from_code(row: Dict[str, Any]) -> List[str]:
    semantic_id, _ = _semantic_from_code(row)
    return GUIDE_MAP.get(semantic_id, ["manufacturing.md"])


class ClassifyIndustryTool(BaseTool):
    """行业分类工具。"""

    name: str = "classify_industry"
    description: str = "根据企业名称、经营范围和补充上下文识别国民经济行业四级代码，并映射行业分析知识库。"
    args_schema: Type[BaseModel] = ClassifyIndustryInput

    def _run(self, enterprise_name: str, business_scope: str = "", extra_context: str = "") -> str:
        return json.dumps(classify_industry(enterprise_name, business_scope, extra_context), ensure_ascii=False)


classify_industry_tool = ClassifyIndustryTool()
