import os
import sys

# 本地验证用：若运行环境尚未安装 reportlab（requirements 已加入），从 /tmp/rlpkgs 兜底
_RL = "/tmp/rlpkgs"
if os.path.isdir(_RL):
    sys.path.insert(0, _RL)

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    from app.api import tasks as tasks_module

    app = FastAPI()
    app.include_router(tasks_module.router, prefix="/api/v1")
    test_client = TestClient(app)

    tid = "test-task-export-1"
    tasks_module.tasks[tid] = {
        "enterprise_name": "API测试公司",
        "agent_state": "completed",
        "report": {
            "enterprise_name": "API测试公司",
            "risk_rating": "low",
            "recommendation": "建议准入。",
            "evidence": [{"label": "收入", "value": "10亿", "source": "CNINFO"}],
        },
    }
    # 跳过磁盘/快照加载，直接用注入的任务；未知 task_id 仍按真实逻辑返回 False
    monkeypatch.setattr(tasks_module, "ensure_task_loaded", lambda t: t in tasks_module.tasks)
    # 报告文件写入临时目录，避免污染项目 output/ 与快照库
    monkeypatch.setattr(tasks_module.settings, "OUTPUT_DIR", tmp_path)
    return test_client, tid


def test_report_json(client):
    c, tid = client
    r = c.get(f"/api/v1/tasks/{tid}/report")
    assert r.status_code == 200
    assert r.json()["risk_rating"] == "low"


def test_report_pdf(client):
    c, tid = client
    r = c.get(f"/api/v1/tasks/{tid}/report?format=pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 1000


def test_report_docx(client):
    c, tid = client
    r = c.get(f"/api/v1/tasks/{tid}/report?format=docx")
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers["content-type"]
    assert len(r.content) > 1000


def test_report_missing_task(client):
    c, _ = client
    r = c.get("/api/v1/tasks/does-not-exist/report?format=pdf")
    assert r.status_code == 404
