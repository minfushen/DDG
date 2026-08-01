# backend/tests/test_e2e_task_pipeline.py
"""任务全链路 API 级端到端测试。

覆盖真实 HTTP 端点的完整编排链路：
  创建任务 -> 生成研究计划并进入计划确认中断(HITL) -> 人工确认计划
  -> 执行研究生成报告 -> 读取结构化报告。

仅对「LLM 研究规划器」和「深度研究执行」两个引擎入口打桩，
其余(意图解析、HITL 状态机、任务生命周期映射、报告读取)均走真实代码，
使该用例可完全离线、确定性运行，适合纳入 CI 回归。
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

# 使用一个不含任务话术、且不在快速识别表内的名称，保证不会触发主体确认中断，
# 也保证 enterprise_name 不会被规则改写，便于稳定断言。
ENTERPRISE = "宏远材料股份有限公司"


@pytest.fixture
def e2e(monkeypatch):
    import app.api.tasks as tasks_module

    # 隔离运行时任务表，避免跨用例串扰
    tasks_module.tasks.clear()
    tasks_module.task_events.clear()

    # 打桩持久化与报告导出：E2E 只验证内存编排链路，不落盘(不写 sqlite / json)
    monkeypatch.setattr(tasks_module, "persist_task", lambda task_id: None)
    monkeypatch.setattr(tasks_module, "export_completed_report", lambda task: None)

    # 打桩后台调度：记录待运行 task_id，由测试显式驱动，
    # 规避 TestClient 同步事件循环下 call_later/create_task 的时序不确定性。
    scheduled = []

    def fake_schedule(task_id, delay_seconds=0.0):
        scheduled.append(task_id)

    monkeypatch.setattr(tasks_module, "schedule_task_background", fake_schedule)

    # 打桩 LLM 研究规划器：返回确定性研究计划
    async def fake_prepare(*, enterprise_name, objective="", max_iterations=6, on_update=None, **kwargs):
        research_state = {
            "enterprise_name": enterprise_name,
            "objective": objective,
            "tasks": [
                {
                    "id": "rt_1",
                    "question": f"{enterprise_name}的偿债能力如何？",
                    "purpose": "评估短期与长期偿债风险",
                    "category": "financial",
                    "status": "pending",
                    "required_evidence": [],
                    "tool_hints": [],
                },
                {
                    "id": "rt_2",
                    "question": f"{enterprise_name}所处行业景气度如何？",
                    "purpose": "判断行业周期与政策环境",
                    "category": "industry",
                    "status": "pending",
                    "required_evidence": [],
                    "tool_hints": [],
                },
            ],
            "timeline": [],
            "planner": {"source": "stub"},
        }
        return {"success": True, "research_state": research_state}

    monkeypatch.setattr(tasks_module, "prepare_deep_research_plan", fake_prepare)

    # 打桩深度研究执行：返回确定性报告(不含证据缺口，保证一次性生成报告)
    async def fake_run(*, enterprise_name, objective="", max_iterations=6, approved_state=None, **kwargs):
        report = {
            "enterprise_name": enterprise_name,
            "risk_rating": "low",
            "recommendation": "建议准入，关注行业周期波动。",
            "evidence": [{"label": "营业收入", "value": "120亿", "source": "CNINFO"}],
            "claims": [],
            "gaps": [],
            "research_plan": (approved_state or {}).get("tasks", []),
        }
        research_state = {
            **(approved_state or {}),
            "evidence": report["evidence"],
            "claims": [],
            "gaps": [],
            "tool_traces": [],
            "follow_up_tasks": [],
        }
        return {"success": True, "research_state": research_state, "report": report}

    monkeypatch.setattr(tasks_module, "run_deep_research_due_diligence", fake_run)

    from app.main import app

    return TestClient(app), tasks_module, scheduled


def _drive_background(tasks_module, task_id):
    """显式驱动一次后台研究协程(桩化引擎，立即返回)。"""
    asyncio.run(tasks_module.run_deepresearch_task_background(task_id))


def test_full_pipeline_create_to_report(e2e):
    client, tasks_module, scheduled = e2e

    # 1. 创建任务：应快速返回 task_id 且进入 gathering，同时调度后台阶段
    resp = client.post("/api/v1/tasks", json={"enterprise_name": ENTERPRISE})
    assert resp.status_code == 200
    body = resp.json()
    task_id = body["task_id"]
    # 意图解析会对企业名做规范化，以返回值为后续断言基准，与规范化规则解耦
    actual_name = body["enterprise_name"]
    assert "宏远材料" in actual_name
    assert body["task_state"] == "gathering"
    assert task_id in scheduled

    # 报告此时尚未生成
    assert client.get(f"/api/v1/tasks/{task_id}/report").status_code == 404

    # 2. 驱动第一阶段：生成研究计划并进入计划确认中断(HITL)
    _drive_background(tasks_module, task_id)

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    status = resp.json()
    assert status["task_state"] == "under_review"
    assert status["active_interrupt"]["type"] == "approve_plan"
    assert len(status["plan"]) >= 1

    # 3. 人工确认研究计划
    resp = client.post(
        f"/api/v1/tasks/{task_id}/interrupts/active/resume",
        json={"resolution": {"action": "approve_plan"}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resuming"
    assert scheduled.count(task_id) == 2  # 确认后再次调度执行阶段

    # 4. 驱动第二阶段：执行研究并生成报告
    _drive_background(tasks_module, task_id)

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200
    status = resp.json()
    assert status["task_state"] == "report_ready"
    assert status["report"] is not None
    assert status["report"]["risk_rating"] == "low"

    # 5. 读取结构化报告(JSON)
    resp = client.get(f"/api/v1/tasks/{task_id}/report")
    assert resp.status_code == 200
    report = resp.json()
    assert report["enterprise_name"] == actual_name
    assert report["risk_rating"] == "low"
    assert report["evidence"][0]["source"] == "CNINFO"


def test_cancel_plan_stops_pipeline(e2e):
    """负路径：计划确认阶段选择暂不执行，任务不应生成报告。"""
    client, tasks_module, scheduled = e2e

    resp = client.post("/api/v1/tasks", json={"enterprise_name": ENTERPRISE})
    task_id = resp.json()["task_id"]

    _drive_background(tasks_module, task_id)  # 进入 approve_plan 中断

    resp = client.post(
        f"/api/v1/tasks/{task_id}/interrupts/active/resume",
        json={"resolution": {"action": "cancel_task"}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # 未生成报告
    assert client.get(f"/api/v1/tasks/{task_id}/report").status_code == 404
