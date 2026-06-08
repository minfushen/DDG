"""权威工商数据工具测试。"""

import json

from app.agents.tools import authoritative_business_tool as tool


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 521:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_fetch_tianyancha_success(monkeypatch):
    monkeypatch.setattr(tool.settings, "BUSINESS_REGISTRY_PROVIDER", "tianyancha")
    monkeypatch.setattr(tool.settings, "TIANYANCHA_API_TOKEN", "fake-token")

    def fake_get(*args, **kwargs):
        return FakeResponse(payload={
            "error_code": 0,
            "result": {
                "name": "欣旺达电子股份有限公司",
                "creditCode": "91440300279446850J",
                "legalPersonName": "王威",
                "regCapital": "157379.9571 万元人民币",
                "estiblishTime": 881251200000,
                "regStatus": "存续",
                "companyOrgType": "股份有限公司（上市）",
                "regLocation": "深圳市宝安区石岩街道石龙社区颐和路2号",
                "businessScope": "一般经营项目是：锂离子电池、电子产品的研发、生产和销售。",
            },
        })

    monkeypatch.setattr(tool.httpx, "get", fake_get)
    result = json.loads(tool.fetch_authoritative_business_info._run("分析欣旺达的工商信息"))

    assert result["success"] is True
    assert result["provider"] == "tianyancha"
    assert result["basic_info"]["统一社会信用代码"]["value"] == "91440300279446850J"
    assert result["basic_info"]["股票代码"]["value"] == "300207"


def test_gsxt_probe_abandons_unstable_channel(monkeypatch):
    monkeypatch.setattr(tool.settings, "BUSINESS_REGISTRY_PROVIDER", "gsxt")

    def fake_get(*args, **kwargs):
        return FakeResponse(status_code=521, text="<script>document.cookie='__jsl_clearance_s=...'</script>")

    monkeypatch.setattr(tool.httpx, "get", fake_get)
    result = json.loads(tool.fetch_authoritative_business_info._run("欣旺达电子股份有限公司"))

    assert result["success"] is False
    assert result["attempts"][0]["provider"] == "gsxt"
    assert "放弃直连通道" in result["attempts"][0]["reason"]
