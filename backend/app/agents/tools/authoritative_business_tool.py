# ========================================
# 权威/专项工商数据工具
# 优先接企业工商专项 API；国家企业信用信息公示系统仅做可用性探测
# ========================================

from __future__ import annotations

from typing import Any, Dict, Optional, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from datetime import datetime
import hashlib
import httpx
import json
import time

from app.config import settings
from app.agents.tools.listed_company_tool import resolve_listed_company


class FetchAuthoritativeBusinessInput(BaseModel):
    """获取权威工商信息输入。"""

    enterprise_name: str = Field(description="企业名称")


FIELD_ALIASES = {
    "企业名称": ["name", "companyName", "Name", "entName"],
    "统一社会信用代码": ["creditCode", "creditNo", "CreditCode", "socialCreditCode", "regNumber"],
    "法定代表人": ["legalPersonName", "legalPerson", "operName", "frName", "LegalPersonName"],
    "注册资本": ["regCapital", "registCapi", "regCap", "RegCapital"],
    "成立日期": ["estiblishTime", "startDate", "setupDate", "EstablishDate"],
    "经营状态": ["regStatus", "status", "corpStatusString", "Status"],
    "企业类型": ["companyOrgType", "econKind", "companyType", "Type"],
    "注册地址": ["regLocation", "address", "Address", "dom"],
    "经营范围": ["businessScope", "scope", "Scope", "opscope"],
    "注册号": ["regNumber", "regNo", "No"],
    "组织机构代码": ["orgNumber", "orgNo", "OrgNo"],
}


def _normalize_enterprise_name(enterprise_name: str) -> str:
    listed_company = resolve_listed_company(enterprise_name)
    if listed_company and listed_company.get("company_name"):
        return listed_company["company_name"]
    return enterprise_name.strip()


def _pick(data: Dict[str, Any], aliases: list[str]) -> Optional[Any]:
    for key in aliases:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        # 天眼查部分时间字段是毫秒时间戳。
        if value > 10_000_000_000:
            return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d")
        return str(value)
    return str(value).strip()


def _normalize_business_payload(
    enterprise_name: str,
    provider: str,
    raw_record: Dict[str, Any],
    source_name: str,
    source_url: Optional[str],
) -> Dict[str, Any]:
    basic_info: Dict[str, Dict[str, Any]] = {}
    for field, aliases in FIELD_ALIASES.items():
        value = _format_value(_pick(raw_record, aliases))
        if value:
            basic_info[field] = {
                "value": value,
                "source_name": source_name,
                "source_url": source_url,
                "confidence": 0.92,
                "trust_level": "high",
            }

    listed_company = resolve_listed_company(enterprise_name)
    if listed_company:
        if "股票代码" not in basic_info:
            basic_info["股票代码"] = {
                "value": listed_company.get("stock_code", ""),
                "source_name": "本地上市公司映射",
                "source_url": None,
                "confidence": 0.85,
                "trust_level": "medium",
            }
        if "股票简称" not in basic_info:
            basic_info["股票简称"] = {
                "value": listed_company.get("security_name", ""),
                "source_name": "本地上市公司映射",
                "source_url": None,
                "confidence": 0.85,
                "trust_level": "medium",
            }

    return {
        "success": True,
        "enterprise_name": basic_info.get("企业名称", {}).get("value") or enterprise_name,
        "provider": provider,
        "generated_from": source_name,
        "basic_info": basic_info,
        "raw_record": raw_record,
    }


def _unwrap_tianyancha_result(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0]
    return None


def _unwrap_qichacha_result(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    result = payload.get("Result") or payload.get("result")
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return result[0]
    return None


def _fetch_from_tianyancha(enterprise_name: str) -> Dict[str, Any]:
    if not settings.TIANYANCHA_API_TOKEN:
        return {"success": False, "reason": "未配置 TIANYANCHA_API_TOKEN"}

    response = httpx.get(
        "https://open.api.tianyancha.com/services/open/ic/baseinfo/2.0",
        params={"keyword": enterprise_name},
        headers={"Authorization": settings.TIANYANCHA_API_TOKEN},
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error_code") not in (0, "0", None) and payload.get("reason"):
        return {"success": False, "reason": f"天眼查 API 返回失败：{payload.get('reason')}"}

    record = _unwrap_tianyancha_result(payload)
    if not record:
        return {"success": False, "reason": "天眼查 API 未返回工商记录"}
    return _normalize_business_payload(
        enterprise_name=enterprise_name,
        provider="tianyancha",
        raw_record=record,
        source_name="天眼查开放平台",
        source_url="https://open.tianyancha.com/",
    )


def _fetch_from_qichacha(enterprise_name: str) -> Dict[str, Any]:
    if not settings.QICHACHA_API_KEY or not settings.QICHACHA_API_SECRET:
        return {"success": False, "reason": "未配置 QICHACHA_API_KEY/QICHACHA_API_SECRET"}

    timestamp = str(int(time.time()))
    token = hashlib.md5(
        f"{settings.QICHACHA_API_KEY}{timestamp}{settings.QICHACHA_API_SECRET}".encode("utf-8")
    ).hexdigest().upper()
    response = httpx.get(
        "https://api.qichacha.com/ECIV4/GetBasicDetailsByName",
        params={"key": settings.QICHACHA_API_KEY, "keyword": enterprise_name},
        headers={"Token": token, "Timespan": timestamp},
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    status = str(payload.get("Status") or payload.get("status") or "")
    if status and status not in {"200", "0"}:
        return {"success": False, "reason": f"企查查 API 返回失败：{payload.get('Message') or payload.get('message') or status}"}

    record = _unwrap_qichacha_result(payload)
    if not record:
        return {"success": False, "reason": "企查查 API 未返回工商记录"}
    return _normalize_business_payload(
        enterprise_name=enterprise_name,
        provider="qichacha",
        raw_record=record,
        source_name="企查查开放平台",
        source_url="https://openapi.qcc.com/",
    )


def _probe_gsxt() -> Dict[str, Any]:
    try:
        response = httpx.get("https://www.gsxt.gov.cn/index.html", timeout=8, follow_redirects=True)
    except Exception as e:
        return {"success": False, "reason": f"国家企业信用信息公示系统探测失败：{str(e)}"}

    body = response.text[:500]
    if response.status_code in {403, 412, 418, 429, 521} or "__jsl_clearance" in body or "验证码" in body:
        return {
            "success": False,
            "reason": "国家企业信用信息公示系统存在 JS 校验/验证码/反爬限制，未发现稳定公开后端 API，本次放弃直连通道。",
            "status_code": response.status_code,
        }
    return {
        "success": False,
        "reason": "国家企业信用信息公示系统未配置可解析的公开 API 适配器，放弃直连通道。",
        "status_code": response.status_code,
    }


class FetchAuthoritativeBusinessTool(BaseTool):
    """获取权威/专项工商信息工具。"""

    name: str = "fetch_authoritative_business_info"
    description: str = "优先从企业工商专项 API 获取基础工商信息；不可用时返回失败原因供上层回退。"
    args_schema: Type[BaseModel] = FetchAuthoritativeBusinessInput

    def _run(self, enterprise_name: str) -> str:
        normalized_name = _normalize_enterprise_name(enterprise_name)
        provider = (settings.BUSINESS_REGISTRY_PROVIDER or "auto").lower()
        if provider == "none":
            return json.dumps({
                "success": False,
                "enterprise_name": normalized_name,
                "attempts": [{"provider": "none", "reason": "BUSINESS_REGISTRY_PROVIDER=none"}],
            }, ensure_ascii=False)

        provider_order = [provider] if provider in {"tianyancha", "qichacha", "gsxt"} else ["tianyancha", "qichacha", "gsxt"]
        attempts = []
        for item in provider_order:
            try:
                if item == "tianyancha":
                    result = _fetch_from_tianyancha(normalized_name)
                elif item == "qichacha":
                    result = _fetch_from_qichacha(normalized_name)
                elif item == "gsxt":
                    result = _probe_gsxt()
                else:
                    result = {"success": False, "reason": f"未知工商数据 provider：{item}"}
            except Exception as e:
                result = {"success": False, "reason": str(e)}

            if result.get("success"):
                result["attempts"] = attempts + [{"provider": item, "success": True}]
                return json.dumps(result, ensure_ascii=False)
            attempts.append({"provider": item, "success": False, "reason": result.get("reason"), "status_code": result.get("status_code")})

        return json.dumps({
            "success": False,
            "enterprise_name": normalized_name,
            "attempts": attempts,
            "error": "企业工商专项 API/国家企业信用信息公示系统通道均不可用，已放弃权威直连方案。",
        }, ensure_ascii=False)


fetch_authoritative_business_info = FetchAuthoritativeBusinessTool()
