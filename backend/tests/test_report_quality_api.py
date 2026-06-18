from fastapi.testclient import TestClient

from app.main import app


def test_report_quality_evaluate_api():
    client = TestClient(app)
    report = {
        "enterprise_name": "分析一下士兰微这个上市公司",
        "risk_score": 79,
        "risk_rating": "medium",
        "credit_decision": {"suggestion": "建议采纳"},
        "report_chapters": [{"id": "overview", "summary": ["报告专项待补充"]}],
        "evidence": [],
    }

    response = client.post("/api/v1/report-quality/evaluate", json={"report": report})

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False
    assert any(issue["severity"] == "P0" for issue in data["issues"])
