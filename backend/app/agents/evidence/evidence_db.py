"""SQLite-backed evidence persistence for cross-task audit and lifecycle.

evidence 表 + claims 表 + claim_evidence 关系表，支持：
- 按 task_id / enterprise_name / agent / source_type 跨任务查询证据
- claim ↔ evidence 双向关系追溯
- evidence 生命周期（active / superseded / archived）

与 task_store 的关系：task payload_json 仍含 evidence list（兼容现有读取），
本表是"权威索引"，便于审计查询和生命周期管理，不替代 task snapshot。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import settings

DB_PATH = settings.DB_DIR / "ddg_evidence.sqlite3"


def _connect() -> sqlite3.Connection:
    settings.DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def init_evidence_db() -> None:
    """建表（幂等）。在 main.py lifespan 启动时调用。"""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                enterprise_name TEXT,
                agent TEXT,
                domain TEXT,
                label TEXT,
                value TEXT,
                source TEXT,
                source_type TEXT,
                confidence REAL,
                trust_level TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                retrieved_at TEXT,
                saved_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_enterprise ON evidence(enterprise_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_agent ON evidence(agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence(status)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                enterprise_name TEXT,
                text TEXT,
                confidence REAL,
                risk_level TEXT,
                requires_review INTEGER,
                payload_json TEXT NOT NULL,
                saved_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_task ON claims(task_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_enterprise ON claims(enterprise_name)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS claim_evidence (
                claim_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                PRIMARY KEY (claim_id, evidence_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claim_evidence_evidence ON claim_evidence(evidence_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claim_evidence_task ON claim_evidence(task_id)")


def _json_default(value: Any) -> str:
    return str(value)


def _safe_json(s: Any) -> Any:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def save_evidence_batch(task_id: str, enterprise_name: str, evidence_list: List[Dict[str, Any]]) -> int:
    """批量 upsert evidence。

    已存在的 evidence_id 保留原 status（避免覆盖 superseded/archived 状态），
    其余字段更新；新记录默认 status=active。
    """
    if not evidence_list:
        return 0
    now = datetime.now().isoformat()
    with _connect() as conn:
        for ev in evidence_list:
            ev_id = str(ev.get("id") or "")
            if not ev_id:
                continue
            existing = conn.execute("SELECT status FROM evidence WHERE evidence_id = ?", (ev_id,)).fetchone()
            status = existing["status"] if existing else str(ev.get("status") or "active")
            conn.execute(
                """
                INSERT INTO evidence (evidence_id, task_id, enterprise_name, agent, domain, label, value, source, source_type, confidence, trust_level, status, retrieved_at, saved_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    task_id = excluded.task_id,
                    enterprise_name = excluded.enterprise_name,
                    agent = excluded.agent,
                    domain = excluded.domain,
                    label = excluded.label,
                    value = excluded.value,
                    source = excluded.source,
                    source_type = excluded.source_type,
                    confidence = excluded.confidence,
                    trust_level = excluded.trust_level,
                    retrieved_at = excluded.retrieved_at,
                    saved_at = excluded.saved_at,
                    payload_json = excluded.payload_json
                """,
                (
                    ev_id, task_id, str(enterprise_name or ""),
                    str(ev.get("agent") or ""), str(ev.get("domain") or ""),
                    str(ev.get("label") or "")[:500], str(ev.get("value") or "")[:2000],
                    str(ev.get("source") or "")[:500], str(ev.get("source_type") or ""),
                    float(ev.get("confidence") or 0), str(ev.get("trust_level") or ""),
                    status, str(ev.get("retrieved_at") or ""), now,
                    json.dumps(ev, ensure_ascii=False, default=_json_default),
                ),
            )
    return len(evidence_list)


def save_claims_batch(task_id: str, enterprise_name: str, claims: List[Dict[str, Any]]) -> int:
    """批量 upsert claims + claim_evidence 关系。"""
    if not claims:
        return 0
    now = datetime.now().isoformat()
    with _connect() as conn:
        for claim in claims:
            claim_id = str(claim.get("id") or "")
            if not claim_id:
                continue
            conn.execute(
                """
                INSERT INTO claims (claim_id, task_id, enterprise_name, text, confidence, risk_level, requires_review, payload_json, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    task_id = excluded.task_id,
                    enterprise_name = excluded.enterprise_name,
                    text = excluded.text,
                    confidence = excluded.confidence,
                    risk_level = excluded.risk_level,
                    requires_review = excluded.requires_review,
                    payload_json = excluded.payload_json,
                    saved_at = excluded.saved_at
                """,
                (
                    claim_id, task_id, str(enterprise_name or ""),
                    str(claim.get("text") or "")[:2000],
                    float(claim.get("confidence") or 0),
                    str(claim.get("risk_level") or ""),
                    1 if claim.get("requires_manual_review") else 0,
                    json.dumps(claim, ensure_ascii=False, default=_json_default),
                    now,
                ),
            )
            for ev_id in (claim.get("evidence_ids") or []):
                ev_id = str(ev_id)
                if ev_id:
                    conn.execute(
                        "INSERT OR IGNORE INTO claim_evidence (claim_id, evidence_id, task_id) VALUES (?, ?, ?)",
                        (claim_id, ev_id, task_id),
                    )
    return len(claims)


def load_evidence_for_task(task_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM evidence WHERE task_id = ? ORDER BY retrieved_at", (task_id,)
        ).fetchall()
    return [r for r in (_safe_json(row["payload_json"]) for row in rows) if isinstance(r, dict)]


def load_claims_for_task(task_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM claims WHERE task_id = ?", (task_id,)
        ).fetchall()
    return [r for r in (_safe_json(row["payload_json"]) for row in rows) if isinstance(r, dict)]


def query_evidence(
    enterprise_name: Optional[str] = None,
    agent: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = "active",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """跨任务查询证据（审计/复盘用）。默认只返回 active 证据。"""
    clauses: List[str] = []
    params: List[Any] = []
    if enterprise_name:
        clauses.append("enterprise_name = ?")
        params.append(enterprise_name)
    if agent:
        clauses.append("agent = ?")
        params.append(agent)
    if source_type:
        clauses.append("source_type = ?")
        params.append(source_type)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT payload_json FROM evidence{where} ORDER BY saved_at DESC LIMIT ?", params
        ).fetchall()
    return [r for r in (_safe_json(row["payload_json"]) for row in rows) if isinstance(r, dict)]


def query_claims_for_evidence(evidence_id: str) -> List[Dict[str, Any]]:
    """反向查询：某证据被哪些 claim 引用（审计追溯用）。"""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.payload_json FROM claims c
            JOIN claim_evidence ce ON c.claim_id = ce.claim_id
            WHERE ce.evidence_id = ?
            """,
            (evidence_id,),
        ).fetchall()
    return [r for r in (_safe_json(row["payload_json"]) for row in rows) if isinstance(r, dict)]


def supersede_evidence(evidence_id: str, by_evidence_id: Optional[str] = None, reason: str = "") -> bool:
    """标记证据被取代（生命周期管理）：status active → superseded。

    by_evidence_id/reason 记录到 payload_json 的 superseded_by 字段，便于追溯。
    """
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE evidence SET status = 'superseded' WHERE evidence_id = ? AND status = 'active'",
            (evidence_id,),
        )
        if cur.rowcount > 0 and (by_evidence_id or reason):
            row = conn.execute("SELECT payload_json FROM evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            if row:
                payload = _safe_json(row["payload_json"]) or {}
                payload["superseded_by"] = by_evidence_id
                payload["supersede_reason"] = reason
                payload["superseded_at"] = datetime.now().isoformat()
                conn.execute(
                    "UPDATE evidence SET payload_json = ? WHERE evidence_id = ?",
                    (json.dumps(payload, ensure_ascii=False, default=_json_default), evidence_id),
                )
        return cur.rowcount > 0


def archive_evidence(evidence_id: str) -> bool:
    """归档证据（不再参与报告，但保留审计记录）。"""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE evidence SET status = 'archived' WHERE evidence_id = ?", (evidence_id,)
        )
        return cur.rowcount > 0
