"""Standalone sanity tests for planner normalization without crewai dependency."""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

# Avoid importing the full research_engine package which pulls in crewai.
# Import only the llm_planner module by exec'ing it with a stub settings object.
import importlib.util
import types

# Stub settings so we don't need full app config
stub_settings = types.SimpleNamespace(
    ENABLE_LLM_RESEARCH_PLANNER=True,
    RESEARCH_PLANNER_LLM_API_KEY="",
    RESEARCH_PLANNER_LLM_BASE_URL="",
    RESEARCH_PLANNER_LLM_MODEL="",
    LLM_API_KEY="",
    LLM_BASE_URL="",
    LLM_MODEL="",
    RESEARCH_PLANNER_MAX_TASKS=6,
    RESEARCH_PLANNER_TIMEOUT_SECONDS=90,
)

# Create a minimal app.config.settings stub
app_pkg = types.ModuleType("app")
config_mod = types.ModuleType("app.config")
config_mod.settings = stub_settings
app_pkg.config = config_mod
sys.modules["app"] = app_pkg
sys.modules["app.config"] = config_mod

# Stub prompts and state to avoid importing the full package
prompts_mod = types.ModuleType("app.agents.research_engine.prompts")
prompts_mod.ALLOWED_RESEARCH_CATEGORIES = ["business", "financial", "legal", "industry", "credit", "general"]
prompts_mod.ALLOWED_TOOL_HINTS = [
    "listed_company", "business_agent", "financial_agent", "legal_agent",
    "industry_agent", "uploaded_files", "bocha_search", "rag",
]
prompts_mod.build_research_planner_prompt = lambda *args, **kwargs: ""
sys.modules["app.agents"] = types.ModuleType("app.agents")
sys.modules["app.agents.research_engine"] = types.ModuleType("app.agents.research_engine")
sys.modules["app.agents.research_engine.prompts"] = prompts_mod

state_mod = types.ModuleType("app.agents.research_engine.state")
state_mod.ResearchTask = dict
_counter = 0
def _stable_id(prefix, *args):
    global _counter
    _counter += 1
    return f"{prefix}_test_{_counter}"
state_mod.stable_id = _stable_id
sys.modules["app.agents.research_engine.state"] = state_mod

# Load llm_planner directly
spec = importlib.util.spec_from_file_location(
    "app.agents.research_engine.llm_planner",
    backend_dir / "app" / "agents" / "research_engine" / "llm_planner.py",
)
llm_planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_planner)


def test_normalize_plan_missing_tasks_returns_empty():
    tasks, metadata = llm_planner._normalize_plan({"plan_summary": "test"}, "TestCo", 6)
    assert tasks == [], tasks
    assert metadata.get("normalize_error") == "planner JSON missing tasks array", metadata


def test_normalize_plan_top_level_list():
    parsed = [
        {"question": "q1", "purpose": "p1", "category": "business", "required_evidence": ["e1"], "tool_hints": ["bocha_search"]},
        {"question": "q2", "purpose": "p2", "category": "financial", "required_evidence": ["e2"], "tool_hints": ["financial_agent"]},
    ]
    tasks, metadata = llm_planner._normalize_plan(parsed, "TestCo", 6)
    assert len(tasks) == 2, tasks
    assert metadata["task_count"] == 2, metadata


def test_normalize_plan_wrapped_tasks():
    parsed = {
        "tasks": {
            "tasks": [
                {"question": "q1", "purpose": "p1", "category": "business", "required_evidence": ["e1"], "tool_hints": ["bocha_search"]},
            ]
        }
    }
    tasks, metadata = llm_planner._normalize_plan(parsed, "TestCo", 6)
    assert len(tasks) == 1, tasks
    assert metadata["task_count"] == 1, metadata


def test_json_from_text_variants():
    assert llm_planner._json_from_text('{"tasks":[]}') == {"tasks": []}
    assert llm_planner._json_from_text('```json\n{"tasks":[]}\n```') == {"tasks": []}
    assert llm_planner._json_from_text('prefix {"tasks":[]} suffix') == {"tasks": []}
    assert llm_planner._json_from_text('') == {}


if __name__ == "__main__":
    test_normalize_plan_missing_tasks_returns_empty()
    test_normalize_plan_top_level_list()
    test_normalize_plan_wrapped_tasks()
    test_json_from_text_variants()
    print("All standalone planner normalization tests passed.")
