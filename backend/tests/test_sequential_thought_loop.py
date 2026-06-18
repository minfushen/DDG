import asyncio

from app.agents.research_engine import mcp_tools
from app.agents.research_engine.mcp_tools import run_sequential_thought_loop
from app.agents.research_engine.planner import create_default_research_plan
from app.agents.research_engine.prompts import build_research_planner_prompt


def test_run_sequential_thought_loop_records_three_steps(monkeypatch):
    async def fake_call(payload, tools=None):
        return {
            "success": True,
            "json": {
                "thoughtNumber": payload["thoughtNumber"],
                "totalThoughts": max(payload["totalThoughts"], payload["thoughtNumber"]),
                "nextThoughtNeeded": payload["nextThoughtNeeded"],
                "thoughtHistoryLength": payload["thoughtNumber"],
            },
        }

    monkeypatch.setattr(mcp_tools.settings, "ENABLE_SEQUENTIAL_THINKING", True)
    monkeypatch.setattr(mcp_tools, "call_sequential_thinking_step", fake_call)

    tasks = create_default_research_plan("欣旺达", "完整贷前尽调")
    result = asyncio.run(run_sequential_thought_loop("欣旺达", "完整贷前尽调", tasks, session_id="task-1"))

    assert result["success"] is True
    assert len(result["steps"]) == 3
    assert "研究思考链步骤1" in result["plan_context"]
    assert "覆盖风险域" in result["plan_context"]


def test_research_planner_prompt_includes_thought_loop_context():
    tasks = create_default_research_plan("士兰微", "完整贷前尽调")
    prompt = build_research_planner_prompt(
        "士兰微",
        "完整贷前尽调",
        tasks,
        max_tasks=6,
        thought_loop_context="研究思考链步骤1：先确认半导体上市主体和数据边界。",
    )

    assert "研究思考链上下文" in prompt
    assert "先确认半导体上市主体和数据边界" in prompt
    assert "不要复述推理过程" in prompt
