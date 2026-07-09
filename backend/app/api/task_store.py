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

from app.memory import LongTermMemory
from app.config import settings


DB_PATH = settings.DB_DIR / "ddg_tasks.sqlite3"


def _connect() -> sqlite3.Connection:
    settings.DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        # WAL 提升并发读写能力，降低 "database is locked" 概率
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
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

    # --- long-term memory: save enterprise profile on task completion ---
    if settings.ENABLE_LONG_TERM_MEMORY:
        agent_state = str(task.get("agent_state") or "")
        enterprise = str(task.get("enterprise_name") or "")
        if enterprise and agent_state in ("report_ready", "approved"):
            ltm = LongTermMemory()
            # Extract analysis conclusion from report or timeline
            report = payload.get("report", {}) if isinstance(payload, dict) else {}
            timeline = payload.get("timeline", []) if isinstance(payload, dict) else []
            conclusion_parts = []
            if report:
                conclusion_parts.append(json.dumps(report, ensure_ascii=False, default=str)[:1000])
            if timeline:
                conclusion_parts.append(f"timeline_entries={len(timeline)}")
            if conclusion_parts:
                ltm.add_enterprise_profile(
                    enterprise,
                    f"分析完成 [{agent_state}]: {', '.join(conclusion_parts)}",
                    metadata={"task_id": task.get("task_id"), "agent_state": agent_state},
                )


def load_task_snapshot(task_id: str, include_memory: bool = True) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT payload_json FROM ddg_tasks WHERE task_id = ?", (task_id,)).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):
            return None
    except json.JSONDecodeError:
        return None

    # --- long-term memory: enrich with historical enterprise profile ---
    if include_memory and settings.ENABLE_LONG_TERM_MEMORY:
        enterprise = str(payload.get("enterprise_name") or "")
        if enterprise:
            ltm = LongTermMemory()
            profile = ltm.get_enterprise_profile(enterprise)
            if profile:
                payload["_memory"] = {
                    "enterprise_profile": profile,
                    "profile_id": profile.get("id"),
                }

    return payload


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
