"""SQLite-backed cache store for tool results and LLM responses.

Designed to reduce redundant external API calls and LLM invocations during
development, testing, and repeated due-diligence runs. Follows the same
lightweight pattern as ``task_store.py``.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings


DB_PATH: Path = Path(settings.CACHE_DB_PATH) if settings.CACHE_DB_PATH else settings.DB_DIR / "ddg_cache.sqlite3"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _json_default(value: Any) -> str:
    return str(value)


def _iso_now() -> str:
    return datetime.now().isoformat()


def _iso_expire(seconds: int) -> str:
    return (datetime.now() + timedelta(seconds=seconds)).isoformat()


def init_cache_store() -> None:
    """Create cache tables if they do not exist."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_cache (
                cache_key TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                arg_hash TEXT NOT NULL,
                arg_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_cache_expires ON tool_cache(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tool_cache_tool ON tool_cache(tool_name)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                prompt_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_cache_expires ON llm_cache(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_llm_cache_model ON llm_cache(model_name)"
        )


def tool_cache_key(tool_name: str, args: Dict[str, Any]) -> str:
    """Build a deterministic cache key for a tool call.

    Runtime identifiers such as ``research_task_id`` or ``trace`` must be
    excluded from ``args`` before calling this function, otherwise identical
    queries across different tasks will not share cache entries.
    """
    payload = json.dumps(
        {"tool": tool_name, "args": _sortable_args(args)},
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def llm_cache_key(model_name: str, temperature: Optional[float], prompt: Any) -> str:
    """Build a deterministic cache key for an LLM call."""
    payload = json.dumps(
        {
            "model": model_name,
            "temperature": temperature,
            "prompt": prompt if isinstance(prompt, str) else _normalize_messages(prompt),
        },
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _sortable_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return a JSON-serializable, sorted copy of tool arguments."""
    cleaned: Dict[str, Any] = {}
    for key, value in sorted(args.items()):
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            cleaned[key] = sorted(str(v) for v in value if v is not None)
        elif isinstance(value, dict):
            cleaned[key] = _sortable_args(value)
        else:
            cleaned[key] = value
    return cleaned


def _normalize_messages(messages: Any) -> Any:
    """Normalize LangChain-style message lists for hashing."""
    if not isinstance(messages, list):
        return messages
    normalized: List[Dict[str, Any]] = []
    for msg in messages:
        if hasattr(msg, "type") and hasattr(msg, "content"):
            normalized.append({"type": getattr(msg, "type"), "content": getattr(msg, "content")})
        elif isinstance(msg, dict):
            normalized.append(
                {k: v for k, v in sorted(msg.items()) if k in {"type", "content", "role"}}
            )
        else:
            normalized.append(str(msg))
    return normalized


def get_tool_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Return a cached tool result if it exists and has not expired.

    Increments ``hit_count`` on cache hit.
    """
    now = _iso_now()
    with _connect() as conn:
        row = conn.execute(
            """SELECT cache_key, result_json, expires_at
               FROM tool_cache
               WHERE cache_key = ?
                 AND (expires_at IS NULL OR expires_at > ?)""",
            (cache_key, now),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE tool_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
            (cache_key,),
        )
    try:
        result = json.loads(row["result_json"])
    except json.JSONDecodeError:
        return None
    return {"cache_key": row["cache_key"], "result": result, "expires_at": row["expires_at"]}


def set_tool_cache(
    cache_key: str,
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
    ttl_seconds: int,
) -> None:
    """Store a tool result in the cache."""
    arg_json = json.dumps(args, ensure_ascii=False, default=_json_default)
    arg_hash = hashlib.sha256(arg_json.encode("utf-8")).hexdigest()
    result_json = json.dumps(result, ensure_ascii=False, default=_json_default)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO tool_cache
                (cache_key, tool_name, arg_hash, arg_json, result_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                result_json = excluded.result_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at,
                hit_count = tool_cache.hit_count
            """,
            (
                cache_key,
                tool_name,
                arg_hash,
                arg_json,
                result_json,
                _iso_now(),
                _iso_expire(ttl_seconds),
            ),
        )


def get_llm_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Return a cached LLM response if it exists and has not expired."""
    now = _iso_now()
    with _connect() as conn:
        row = conn.execute(
            """SELECT cache_key, response_json, expires_at
               FROM llm_cache
               WHERE cache_key = ?
                 AND (expires_at IS NULL OR expires_at > ?)""",
            (cache_key, now),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE llm_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
            (cache_key,),
        )
    try:
        response = json.loads(row["response_json"])
    except json.JSONDecodeError:
        return None
    return {"cache_key": row["cache_key"], "response": response, "expires_at": row["expires_at"]}


def set_llm_cache(
    cache_key: str,
    model_name: str,
    prompt: Any,
    response: Dict[str, Any],
    ttl_seconds: int,
) -> None:
    """Store an LLM response in the cache."""
    prompt_json = json.dumps(prompt, ensure_ascii=False, default=_json_default)
    prompt_hash = hashlib.sha256(prompt_json.encode("utf-8")).hexdigest()
    response_json = json.dumps(response, ensure_ascii=False, default=_json_default)

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO llm_cache
                (cache_key, model_name, prompt_hash, prompt_json, response_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                response_json = excluded.response_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at,
                hit_count = llm_cache.hit_count
            """,
            (
                cache_key,
                model_name,
                prompt_hash,
                prompt_json,
                response_json,
                _iso_now(),
                _iso_expire(ttl_seconds),
            ),
        )


def clear_cache(prefix: Optional[str] = None) -> int:
    """Delete cache entries. If ``prefix`` is given, only delete keys starting with it.

    Returns the number of deleted rows.
    """
    with _connect() as conn:
        if prefix:
            like = f"{prefix}%"
            tool_rows = conn.execute(
                "DELETE FROM tool_cache WHERE cache_key LIKE ?", (like,)
            ).rowcount
            llm_rows = conn.execute(
                "DELETE FROM llm_cache WHERE cache_key LIKE ?", (like,)
            ).rowcount
        else:
            tool_rows = conn.execute("DELETE FROM tool_cache").rowcount
            llm_rows = conn.execute("DELETE FROM llm_cache").rowcount
    return tool_rows + llm_rows


def cache_stats() -> Dict[str, Any]:
    """Return cache statistics."""
    now = _iso_now()
    with _connect() as conn:
        tool_total = conn.execute("SELECT COUNT(*) FROM tool_cache").fetchone()[0]
        tool_expired = conn.execute(
            "SELECT COUNT(*) FROM tool_cache WHERE expires_at <= ?", (now,)
        ).fetchone()[0]
        tool_by_name = dict(
            conn.execute(
                "SELECT tool_name, COUNT(*) FROM tool_cache GROUP BY tool_name"
            ).fetchall()
        )

        llm_total = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
        llm_expired = conn.execute(
            "SELECT COUNT(*) FROM llm_cache WHERE expires_at <= ?", (now,)
        ).fetchone()[0]
        llm_by_model = dict(
            conn.execute(
                "SELECT model_name, COUNT(*) FROM llm_cache GROUP BY model_name"
            ).fetchall()
        )

    return {
        "tool_cache": {
            "total": tool_total,
            "expired": tool_expired,
            "by_tool": tool_by_name,
        },
        "llm_cache": {
            "total": llm_total,
            "expired": llm_expired,
            "by_model": llm_by_model,
        },
    }
