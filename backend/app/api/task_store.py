"""SQLite-backed task snapshot store.

This is intentionally small: the in-memory task dict remains the runtime cache,
while SQLite stores JSON snapshots so reports and HITL states survive backend
restarts during PoC and local trials.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings


DB_PATH = settings.DB_DIR / "ddg_tasks.sqlite3"


def _connect() -> sqlite3.Connection:
    settings.DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_task_store() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ddg_tasks (
                task_id TEXT PRIMARY KEY,
                enterprise_name TEXT NOT NULL,
                agent_state TEXT NOT NULL,
                engine_mode TEXT,
                created_at TEXT,
                updated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ddg_tasks_updated_at ON ddg_tasks(updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ddg_tasks_agent_state ON ddg_tasks(agent_state)")


def _json_default(value: Any) -> str:
    return str(value)


def save_task_snapshot(task: Dict[str, Any]) -> None:
    if not task.get("task_id"):
        return
    now = datetime.now().isoformat()
    payload = dict(task)
    payload["updated_at"] = now
    task["updated_at"] = now
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ddg_tasks (task_id, enterprise_name, agent_state, engine_mode, created_at, updated_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                enterprise_name = excluded.enterprise_name,
                agent_state = excluded.agent_state,
                engine_mode = excluded.engine_mode,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (
                str(task.get("task_id")),
                str(task.get("enterprise_name") or ""),
                str(task.get("agent_state") or "unknown"),
                str(task.get("engine_mode") or ""),
                str(task.get("created_at") or now),
                now,
                json.dumps(payload, ensure_ascii=False, default=_json_default),
            ),
        )


def load_task_snapshot(task_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT payload_json FROM ddg_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["payload_json"])
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def load_recent_task_snapshots(limit: int = 200) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM ddg_tasks ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    tasks: List[Dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("task_id"):
            tasks.append(payload)
    return tasks


def task_store_path() -> Path:
    return DB_PATH
