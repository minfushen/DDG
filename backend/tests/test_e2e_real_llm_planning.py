# backend/tests/test_e2e_real_llm_planning.py
"""接真实阿里云百炼 LLM 的研究规划链路冒烟测试。

覆盖真实 LLM 段：
  创建任务(真实意图解析 LLM) -> 真实 LLM 研究规划器生成研究计划
  -> 进入计划确认中断(HITL approve_plan)。

设计要点
--------
- **不打桩 LLM**：意图解析与研究规划器均调用真实百炼（qwen3.7-max-2026-06-08 /
  qwen3.7-plus）。
- 仍打桩后台调度与持久化：仅为规避 TestClient 同步事件循环下 call_later/create_task
  的时序不确定性，并保持用例隔离（不落盘 sqlite/json）；不影响真实 LLM 调用。
- 仅覆盖到「计划确认中断」即止，**不触发昂贵的深度研究执行**（单独用例覆盖），
  保证单次运行耗时与成本可控（约 1-2 次真实 LLM 调用）。

为何需要 _load_real_llm_env
--------------------------
``tests/conftest.py`` 在模块顶层把 ``LLM_API_KEY``/``LLM_BASE_URL`` 投毒为
``test_key``/``test.example.com``，作为旧用例防误打真实 LLM 的安全网，且会覆盖
``.env``。本用例必须在 import 任何 app 模块之前，从 ``backend/.env`` 把真实值
重新写回环境变量，否则真实 LLM 调用会发往 test.example.com 而失败。

运行方式（需单独运行，避免被其它用例先导入带投毒 settings 的 app 模块）::

    RUN_REAL_LLM_TESTS=1 venv312/bin/python -m pytest \
        tests/test_e2e_real_llm_planning.py -q -s
"""
import asyncio
import os
from pathlib import Path

# ── 1. 在 import app 之前，从 backend/.env 恢复真实 LLM 配置， defeating conftest 投毒
_REAL_ENV_KEYS = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "RESEARCH_PLANNER_LLM_API_KEY",
    "RESEARCH_PLANNER_LLM_BASE_URL",
    "RESEARCH_PLANNER_LLM_MODEL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_BASE_URL",
)


def _load_real_llm_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key in _REAL_ENV_KEYS:
            os.environ[key] = value.strip()


_load_real_llm_env()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# 真实知名上市公司：意图解析稳定，规划器生成的尽调问题更贴近真实业务
ENTERPRISE = "贵州茅台股份有限公司"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM_TESTS") != "1",
    reason="默认跳过；RUN_REAL_LLM_TESTS=1 显式开启接真实百炼的冒烟（会产生真实调用与费用）",
)


@pytest.fixture
def real_planning_client(monkeypatch):
    # 防御：若 app 已被其它用例以投毒 settings 导入，则跳过，避免假阴性
    import app.api.tasks as tasks_module
    from app.config import settings

    if "test.example.com" in (settings.LLM_BASE_URL or "") or settings.LLM_API_KEY in ("", "test_key"):
        pytest.skip(
            "settings 仍为测试投毒值(test.example.com/test_key)：请单独运行本用例，"
            "RUN_REAL_LLM_TESTS=1 venv312/bin/python -m pytest tests/test_e2e_real_llm_planning.py -q"
        )

    tasks_module.tasks.clear()
    tasks_module.task_events.clear()

    # 仅隔离持久化与后台调度时序；不打桩 LLM
    monkeypatch.setattr(tasks_module, "persist_task", lambda task_id: None)
    monkeypatch.setattr(tasks_module, "export_completed_report", lambda task: None)

    scheduled = []

    def fake_schedule(task_id, delay_seconds=0.0):
        scheduled.append(task_id)

    monkeypatch.setattr(tasks_module, "schedule_task_background", fake_schedule)

    from app.main import app

    return TestClient(app), tasks_module, scheduled


def _drive_background(tasks_module, task_id):
    """显式驱动第一阶段后台协程：真实 LLM 研究规划器生成计划。"""
    asyncio.run(tasks_module.run_deepresearch_task_background(task_id))


def test_real_llm_planning_produces_plan(real_planning_client):
    client, tasks_module, scheduled = real_planning_client

    # 1. 创建任务：真实意图解析(LLM) 同步执行
    resp = client.post("/api/v1/tasks", json={"enterprise_name": ENTERPRISE})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    task_id = body["task_id"]
    assert body["task_state"] == "gathering", body
    assert task_id in scheduled

    # 2. 驱动第一阶段：真实 LLM 研究规划器生成研究计划并进入 HITL 计划确认
    _drive_background(tasks_module, task_id)

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 200, resp.text
    status = resp.json()
    assert status["task_state"] == "under_review", status
    assert status["active_interrupt"]["type"] == "approve_plan", status

    plan = status["plan"]
    assert isinstance(plan, list), plan
    assert len(plan) >= 1, f"真实规划器未生成研究任务: {plan}"

    # 真实计划项应含研究问题与目的（来自真实 LLM 规划输出）。
    # 注意：真实规划器用 ``name`` 字段存研究问题（离线桩用 ``question``），兼容两者。
    first = plan[0]
    assert isinstance(first, dict), first
    question = first.get("name") or first.get("question")
    assert question, f"计划项缺少 name/question: {first}"
    assert first.get("purpose"), f"计划项缺少 purpose: {first}"

    # 打印真实计划摘要（-s 时可见），便于人工确认 LLM 输出质量
    print("\n[真实 LLM 规划] enterprise =", status.get("enterprise_name"))
    for i, t in enumerate(plan, 1):
        q = t.get("name") or t.get("question") or ""
        print(f"  {i}. [{t.get('category', '?')}] {q}")
