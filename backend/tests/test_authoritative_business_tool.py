"""权威工商数据工具测试。

该工具已在架构重构中被移除，当前模块为 stub，始终返回结构化失败以便调用方降级。
测试仅验证 stub 的降级行为。
"""

import json

from app.agents.tools import authoritative_business_tool as tool


def test_fetch_authoritative_business_info_returns_stub_failure():
    result = json.loads(tool.fetch_authoritative_business_info._run("欣旺达电子股份有限公司"))
    assert result["success"] is False
    assert "removed" in result["error"] or "stub" in result["error"].lower()
    assert result["basic_info"] == {}


def test_fetch_authoritative_business_info_preserves_enterprise_name():
    # Stub 不依赖具体企业名，但应能接收任意输入并返回一致结构。
    result = json.loads(tool.fetch_authoritative_business_info._run("任意企业名称"))
    assert result["success"] is False
    assert "error" in result
