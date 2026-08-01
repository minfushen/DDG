"""LangGraph checkpointer for the DeepResearch engine.

为图提供 SQLite 持久化 checkpoint，使 prepare/execute 两次 ainvoke 通过
thread_id 共享状态，且进程重启后可从断点恢复（P0-1）。

设计要点：
- on_update 等不可序列化对象走 RunnableConfig.configurable，不进 state、不被 checkpoint；
- sequential_tools 由节点自行 load_sequential_thinking_tools()，不进 state；
- 落盘路径取 settings.LANGGRAPH_CHECKPOINT_DIR（默认 ./checkpoints）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings

_saver: Optional[AsyncSqliteSaver] = None
_conn = None


async def get_checkpointer() -> AsyncSqliteSaver:
    """惰性创建单例 AsyncSqliteSaver，落到 LANGGRAPH_CHECKPOINT_DIR。"""
    global _saver, _conn
    if _saver is not None:
        return _saver
    cp_dir = Path(settings.LANGGRAPH_CHECKPOINT_DIR)
    # 相对路径相对 backend 工作目录解析
    if not cp_dir.is_absolute():
        cp_dir = Path(__file__).resolve().parents[3] / cp_dir
    cp_dir.mkdir(parents=True, exist_ok=True)
    db_path = cp_dir / "ddg_checkpoints.sqlite3"
    _conn = await aiosqlite.connect(str(db_path))
    _saver = AsyncSqliteSaver(_conn)
    await _saver.setup()
    return _saver


async def close_checkpointer() -> None:
    global _saver, _conn
    if _conn is not None:
        await _conn.close()
    _saver = None
    _conn = None
