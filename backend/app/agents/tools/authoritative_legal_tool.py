# ========================================
# 司法权威数据源可用性探测工具
# 裁判文书网/执行信息公开网无稳定公开结构化 API 时只记录放弃原因
# ========================================

from __future__ import annotations

from typing import Any, Dict, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx
import json


class ProbeAuthoritativeLegalInput(BaseModel):
    """司法权威源探测输入。"""

    enterprise_name: str = Field(description="企业名称")


def _probe_url(name: str, url: str) -> Dict[str, Any]:
    try:
        response = httpx.get(url, timeout=8, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        return {"provider": name, "success": False, "reason": str(e)}

    body = response.text[:1000]
    blocked = response.status_code in {401, 403, 412, 418, 429, 521} or any(
        marker in body for marker in ["验证码", "请开启JavaScript", "WAF", "访问受限", "人机验证"]
    )
    if blocked:
        return {
            "provider": name,
            "success": False,
            "status_code": response.status_code,
            "reason": f"{name} 存在访问限制/验证码/反爬机制，未发现稳定公开结构化 API。",
        }

    return {
        "provider": name,
        "success": False,
        "status_code": response.status_code,
        "reason": f"{name} 首页可访问，但未配置可查询企业司法记录的公开结构化 API，放弃直连通道。",
    }


class ProbeAuthoritativeLegalTool(BaseTool):
    """司法权威数据源可用性探测工具。"""

    name: str = "probe_authoritative_legal_sources"
    description: str = "探测裁判文书网、执行信息公开网等权威司法数据源是否存在可用结构化查询通道。"
    args_schema: Type[BaseModel] = ProbeAuthoritativeLegalInput

    def _run(self, enterprise_name: str) -> str:
        attempts = [
            _probe_url("中国裁判文书网", "https://wenshu.court.gov.cn/"),
            _probe_url("中国执行信息公开网", "https://zxgk.court.gov.cn/"),
        ]
        return json.dumps({
            "success": False,
            "enterprise_name": enterprise_name,
            "attempts": attempts,
            "error": "权威司法网站未发现稳定公开结构化 API，已放弃直连方案并回退公开搜索。",
        }, ensure_ascii=False)


probe_authoritative_legal_sources = ProbeAuthoritativeLegalTool()
