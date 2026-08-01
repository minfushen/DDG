"""任务生命周期状态机映射测试。"""

import pytest

from app.api.tasks import derive_task_state


@pytest.mark.parametrize(
    "agent_state,report,pending_report,interrupt_type,expected",
    [
        ("creating_task", None, None, None, "gathering"),
        ("planning", None, None, None, "gathering"),
        ("calling_tools", None, None, None, "gathering"),
        ("calling_financial", None, None, None, "gathering"),
        ("waiting_upload", None, None, None, "gathering"),
        ("analyzing", None, None, None, "analyzing"),
        ("forming_conclusion", None, None, None, "analyzing"),
        ("generating_report", None, None, None, "analyzing"),
        ("waiting_human", None, None, "approve_plan", "under_review"),
        ("waiting_confirm", None, None, "confirm_entity", "under_review"),
        ("completed", {"foo": 1}, None, None, "report_ready"),
        ("completed", None, {"foo": 1}, None, "report_ready"),
        ("completed", None, None, None, "gathering"),
        ("approved", None, None, None, "approved"),
        ("rejected", None, None, None, "rejected"),
        ("archived", None, None, None, "archived"),
    ],
)
def test_derive_task_state(agent_state, report, pending_report, interrupt_type, expected):
    task = {
        "agent_state": agent_state,
        "report": report,
        "pending_report": pending_report,
        "interrupts": [],
        "active_interrupt": None,
    }
    if interrupt_type:
        task["active_interrupt"] = {"type": interrupt_type}
        task["interrupts"] = [{"type": interrupt_type, "status": "pending"}]
    assert derive_task_state(task) == expected
