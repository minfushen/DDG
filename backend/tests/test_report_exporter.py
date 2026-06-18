import json

from app.api.report_exporter import export_completed_report


def test_export_completed_report_writes_json(tmp_path):
    task = {
        "task_id": "task123",
        "enterprise_name": "药明康德/测试",
        "agent_state": "completed",
        "report": {
            "report_type": "deepresearch_due_diligence",
            "risk_score": 80,
        },
    }

    path = export_completed_report(task, output_dir=tmp_path)

    assert path is not None
    assert path.exists()
    assert path.name == "task123_药明康德_测试_report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["task_id"] == "task123"
    assert data["enterprise_name"] == "药明康德/测试"
    assert data["export_source"] == "ddg_task_auto_export"
    assert task["report_export_path"] == str(path)
    assert task["report_export_hash"]


def test_export_completed_report_is_idempotent_for_same_payload(tmp_path):
    task = {
        "task_id": "task456",
        "enterprise_name": "士兰微",
        "agent_state": "completed",
        "report": {"report_type": "deepresearch_due_diligence", "risk_score": 77},
    }

    first_path = export_completed_report(task, output_dir=tmp_path)
    first_hash = task["report_export_hash"]
    second_path = export_completed_report(task, output_dir=tmp_path)

    assert second_path == first_path
    assert task["report_export_hash"] == first_hash
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_export_completed_report_skips_unfinished_task(tmp_path):
    task = {
        "task_id": "task789",
        "enterprise_name": "蓝思科技",
        "agent_state": "waiting_human",
        "report": {"risk_score": 70},
    }

    assert export_completed_report(task, output_dir=tmp_path) is None
    assert not list(tmp_path.glob("*.json"))
