# backend/tests/test_analysis_api.py
"""应用基础接口测试。"""
from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "running"


def test_health_check(client: TestClient):
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data


def test_removed_legacy_analysis_api(client: TestClient):
    """旧版分析接口已下线，避免后续误用历史 API。"""
    response = client.post("/api/v1/analysis/analyze", json={})
    assert response.status_code == 404
