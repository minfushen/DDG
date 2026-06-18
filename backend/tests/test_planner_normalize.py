"""Quick sanity tests for planner normalization."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.research_engine.llm_planner import _normalize_plan


def test_normalize_plan_missing_tasks_returns_empty():
    tasks, metadata = _normalize_plan({"plan_summary": "test"}, "TestCo", 6)
    assert tasks == []
    assert metadata.get("normalize_error") == "planner JSON missing tasks array"


def test_normalize_plan_top_level_list():
    parsed = [
        {"question": "q1", "purpose": "p1", "category": "business", "required_evidence": ["e1"], "tool_hints": ["bocha_search"]},
        {"question": "q2", "purpose": "p2", "category": "financial", "required_evidence": ["e2"], "tool_hints": ["financial_agent"]},
    ]
    tasks, metadata = _normalize_plan(parsed, "TestCo", 6)
    assert len(tasks) == 2
    assert metadata["task_count"] == 2


def test_normalize_plan_wrapped_tasks():
    parsed = {
        "tasks": {
            "tasks": [
                {"question": "q1", "purpose": "p1", "category": "business", "required_evidence": ["e1"], "tool_hints": ["bocha_search"]},
            ]
        }
    }
    tasks, metadata = _normalize_plan(parsed, "TestCo", 6)
    assert len(tasks) == 1
    assert metadata["task_count"] == 1


if __name__ == "__main__":
    test_normalize_plan_missing_tasks_returns_empty()
    test_normalize_plan_top_level_list()
    test_normalize_plan_wrapped_tasks()
    print("All planner normalization tests passed.")
