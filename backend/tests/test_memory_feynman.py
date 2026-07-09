"""Feynman-style memory system verification tests.

These tests validate the two most critical properties of the Agent Memory System:
1. Precise recall: short-term tool traces are findable by keyword.
2. Timeliness: expired long-term memories are excluded from active search.

Run directly with:
    python3 backend/tests/test_memory_feynman.py
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.memory.memory_store as memory_store
from app.memory import LongTermMemory, ShortTermMemory


def _fresh_temp_db() -> Path:
    """Return a clean temporary SQLite path and monkey-patch the memory store."""
    db_path = Path(tempfile.gettempdir()) / f"test_memory_{datetime.now().timestamp():.6f}.sqlite3"
    db_path.unlink(missing_ok=True)
    for ext in ("-journal", "-wal", "-shm"):
        Path(str(db_path) + ext).unlink(missing_ok=True)
    memory_store._get_db_path = lambda: db_path
    memory_store.init_memory_db()
    return db_path


def test_stm_precise_recall():
    """Feynman Test 1: exact keyword recall from short-term memory.

    A tool result written to STM must be retrievable as the top result when
    searching with a keyword that appears in its content.
    """
    db_path = _fresh_temp_db()
    try:
        stm = ShortTermMemory(session_id="feynman_test_session", task_id="feynman_test_task")
        stm.add_tool_result(
            tool_name="cninfo_webapi_financial",
            result_summary="贵州茅台 2024 年营业收入 1505.60 亿元，同比增长 17.76%",
            success=True,
            cache_hit=False,
        )

        results = stm.search("营业收入")
        assert len(results) >= 1, "Expected at least one STM result for keyword '营业收入'"
        top = results[0]
        assert "1505.60" in top["content"], f"Top result missing expected value: {top['content']}"
        assert top["session_id"] == "feynman_test_session"
        assert top["task_id"] == "feynman_test_task"
        print("✅ test_stm_precise_recall passed")
    finally:
        _cleanup(db_path)


def test_ltm_timeliness():
    """Feynman Test 2: expired long-term memories must not pollute active search.

    When an old enterprise profile has passed its valid_until and a newer one
    exists, search must return only the newer record.
    """
    db_path = _fresh_temp_db()
    try:
        ltm = LongTermMemory(namespace="feynman_test")
        enterprise = "测试科技股份公司"
        now = datetime.now()

        # Old record: expired yesterday
        memory_store.memory_add(
            content=f"[企业画像: {enterprise}] 项目当前使用 Framework A",
            category="enterprise",
            valid_until=(now - timedelta(days=1)).isoformat(),
            metadata={"enterprise": enterprise},
        )

        # New record: valid for the next 30 days
        memory_store.memory_add(
            content=f"[企业画像: {enterprise}] 项目已迁移到 Framework B",
            category="enterprise",
            valid_until=(now + timedelta(days=30)).isoformat(),
            metadata={"enterprise": enterprise},
        )

        results = ltm.search_by_enterprise(enterprise)
        assert len(results) == 1, f"Expected exactly one active result, got {len(results)}"
        assert "Framework B" in results[0]["content"], f"Unexpected active result: {results[0]['content']}"
        assert "Framework A" not in results[0]["content"]
        print("✅ test_ltm_timeliness passed")
    finally:
        _cleanup(db_path)


def _cleanup(db_path: Path) -> None:
    """Remove temp database files."""
    db_path.unlink(missing_ok=True)
    for ext in ("-journal", "-wal", "-shm"):
        Path(str(db_path) + ext).unlink(missing_ok=True)


if __name__ == "__main__":
    test_stm_precise_recall()
    test_ltm_timeliness()
    print("All Feynman memory tests passed.")
