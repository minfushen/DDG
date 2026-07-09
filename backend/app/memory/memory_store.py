# ========================================
# Agent Memory System — 统一存储层
# 基于 SQLite + FTS5 (trigram) 全文索引
# 参考：Feynman Build Workshop 01
# ========================================

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 数据库配置
# ═══════════════════════════════════════════════════════════════

def _get_db_path() -> Path:
    """返回记忆数据库路径。"""
    if settings.MEMORY_DB_PATH:
        return Path(settings.MEMORY_DB_PATH)
    return settings.DB_DIR / "memory" / "memory.sqlite3"


# ═══════════════════════════════════════════════════════════════
# 连接管理
# ═══════════════════════════════════════════════════════════════

@contextmanager
def _get_conn():
    """获取 SQLite 连接，启用 row_factory。"""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 数据库初始化
# ═══════════════════════════════════════════════════════════════

def _has_fts5() -> bool:
    """检查当前 SQLite 是否支持 FTS5。"""
    with _get_conn() as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
        if "memory_fts" in tables:
            return True
        # 尝试创建虚拟表检测
        try:
            conn.execute("CREATE VIRTUAL TABLE _fts5_test USING fts5(content)")
            conn.execute("DROP TABLE _fts5_test")
            return True
        except sqlite3.OperationalError:
            return False


def init_memory_db() -> None:
    """初始化记忆数据库：FTS5 全文索引 + 元数据表。"""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with _get_conn() as conn:
        cur = conn.cursor()

        # FTS5 全文索引 — trigram 分词器支持 CJK 部分匹配
        fts5_available = _has_fts5()
        if fts5_available:
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    content,
                    tokenize='trigram'
                )
            """)
        else:
            # 降级：普通表 + LIKE 搜索
            logger.warning("SQLite 不支持 FTS5，记忆系统将使用 LIKE 降级搜索")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memory_fts (
                    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL
                )
            """)

        # 元数据表
        # 注意：FTS5 虚拟表在某些 SQLite 构建中不支持被外键引用，因此不声明
        # fts_rowid 的外键约束。引用完整性由 memory_add / memory_delete 的代码保证。
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memory_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fts_rowid INTEGER,
                category TEXT NOT NULL DEFAULT 'persistent',
                frozen INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                valid_until TEXT,
                superseded_by INTEGER,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                session_id TEXT,
                task_id TEXT,
                metadata_json TEXT,
                FOREIGN KEY (superseded_by) REFERENCES memory_meta(id)
            )
        """)

        # 索引
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_meta(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_meta(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_valid ON memory_meta(valid_until)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_frozen ON memory_meta(frozen)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_meta(session_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_task ON memory_meta(task_id)")

        logger.info("记忆数据库初始化完成: %s", db_path)


# ═══════════════════════════════════════════════════════════════
# 三分类
# ═══════════════════════════════════════════════════════════════

def classify_memory(content: str) -> str:
    """三分类记忆：persistent / session / archived

    这是整个系统最重要的一步——不是"存什么"，而是"不存什么"。

    persistent: 跨 session 不变的信息（用户偏好、企业画像、技术决策）
    session: 当前 session 有效，结束后可丢弃（临时变量、中间结果、对话）
    archived: 过时或被替代

    生产级可用 LLM 做分类；这里提供最小规则引擎。
    """
    content_lower = content.lower()

    # 该存：用户偏好、企业画像、修复记录、技术决策、系统配置
    persistent_keywords = [
        "偏好", "prefer", "企业画像", "画像", "修复", "fix", "bug", "crash",
        "决策", "选择", "配置", "config", "规则", "rule", "总是", "always",
        "架构", "architecture", "踩坑", "教训", "分析结论", "结论", "画像",
    ]
    # 该缓存：临时、中间结果、单次连接、对话
    session_keywords = [
        "临时", "temp", "中间", "intermediate", "单次", "测试",
        "output:", "result:", "响应:", "response:",
        "用户说", "用户输入", "ai回复", "工具调用", "tool call",
        "搜索", "search", "fetch", "查询", "query",
    ]
    # 归档：已废弃、过时
    archived_keywords = [
        "已废弃", "deprecated", "过时", "obsolete", "不再使用",
    ]

    for kw in archived_keywords:
        if kw in content_lower:
            return "archived"
    for kw in persistent_keywords:
        if kw in content_lower:
            return "persistent"
    for kw in session_keywords:
        if kw in content_lower:
            return "session"
    return "persistent"  # 默认存下来


# ═══════════════════════════════════════════════════════════════
# 底层 CRUD
# ═══════════════════════════════════════════════════════════════

def memory_add(
    content: str,
    category: Optional[str] = None,
    valid_until: Optional[str] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """添加一条记忆。

    Returns:
        meta_id: 新记忆元数据表的 ID
    """
    if category is None:
        category = classify_memory(content)

    now = datetime.now().isoformat()
    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

    with _get_conn() as conn:
        cur = conn.cursor()

        # 写入 FTS5
        cur.execute("INSERT INTO memory_fts (content) VALUES (?)", (content,))
        fts_rowid = cur.lastrowid

        # 写入元数据
        cur.execute(
            """INSERT INTO memory_meta
                (fts_rowid, category, created_at, valid_until,
                 session_id, task_id, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (fts_rowid, category, now, valid_until, session_id, task_id, metadata_json),
        )
        meta_id = cur.lastrowid

        logger.debug("已添加记忆 [%s] id=%s", category, meta_id)
        return meta_id


def memory_search(
    query: str,
    limit: int = 5,
    category: Optional[str] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
    include_expired: bool = False,
    prefer_frozen: bool = True,
) -> List[Dict[str, Any]]:
    """搜索记忆 — FTS5 trigram 宽召回 + 元数据过滤 + LIKE 降级。

    搜索策略：
    1. FTS5 trigram 搜索（3字及以上中文、英文均可命中）
    2. 短查询降级：1-2字中文自动切 LIKE
    3. 元数据过滤：排除过期 + 优先返回冻结项
    4. 返回格式适合直接喂给 LLM 做精排
    """
    now = datetime.now().isoformat()

    # 判断是否需要 LIKE 降级
    use_like = len(query) <= 2 and all("\u4e00" <= c <= "\u9fff" for c in query)

    # 构建过滤条件
    conditions = []
    params: List[Any] = []

    if not include_expired:
        conditions.append("(m.valid_until IS NULL OR m.valid_until > ?)")
        params.append(now)

    if category:
        conditions.append("m.category = ?")
        params.append(category)

    if session_id:
        conditions.append("m.session_id = ?")
        params.append(session_id)

    if task_id:
        conditions.append("m.task_id = ?")
        params.append(task_id)

    conditions.append("m.superseded_by IS NULL")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    order_clause = "m.frozen DESC, rank" if prefer_frozen else "rank"

    with _get_conn() as conn:
        cur = conn.cursor()

        if use_like:
            base_sql = f"""SELECT m.id, f.content, m.category, m.created_at,
                    m.valid_until, m.access_count, m.frozen, m.session_id, m.task_id
                FROM memory_fts f
                JOIN memory_meta m ON f.rowid = m.fts_rowid
                WHERE f.content LIKE ? AND {where_clause}
                ORDER BY {order_clause}
                LIMIT ?"""
            params = [f"%{query}%"] + params + [limit]
        else:
            base_sql = f"""SELECT m.id, f.content, m.category, m.created_at,
                    m.valid_until, m.access_count, m.frozen, m.session_id, m.task_id
                FROM memory_fts f
                JOIN memory_meta m ON f.rowid = m.fts_rowid
                WHERE memory_fts MATCH ? AND {where_clause}
                ORDER BY {order_clause}
                LIMIT ?"""
            params = [query] + params + [limit]

        cur.execute(base_sql, params)
        rows = cur.fetchall()

        results = [dict(row) for row in rows]

        # 更新访问计数
        for r in results:
            cur.execute(
                """UPDATE memory_meta
                    SET last_accessed = ?, access_count = access_count + 1
                    WHERE id = ?""",
                (now, r["id"]),
            )

        return results


def memory_get_recent(
    limit: int = 10,
    category: Optional[str] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """获取最近 N 条记忆。"""
    conditions = ["m.superseded_by IS NULL"]
    params: List[Any] = []

    now = datetime.now().isoformat()
    conditions.append("(m.valid_until IS NULL OR m.valid_until > ?)")
    params.append(now)

    if category:
        conditions.append("m.category = ?")
        params.append(category)
    if session_id:
        conditions.append("m.session_id = ?")
        params.append(session_id)
    if task_id:
        conditions.append("m.task_id = ?")
        params.append(task_id)

    where_clause = " AND ".join(conditions)

    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""SELECT m.id, f.content, m.category, m.created_at,
                    m.valid_until, m.access_count, m.frozen, m.session_id, m.task_id
                FROM memory_fts f
                JOIN memory_meta m ON f.rowid = m.fts_rowid
                WHERE {where_clause}
                ORDER BY m.created_at DESC
                LIMIT ?""",
            params + [limit],
        )
        return [dict(row) for row in cur.fetchall()]


def memory_update_content(meta_id: int, new_content: str) -> None:
    """更新记忆内容（会创建新记忆，旧记忆标记 superseded）。"""
    now = datetime.now().isoformat()

    with _get_conn() as conn:
        cur = conn.cursor()

        # 获取旧记忆信息
        cur.execute(
            "SELECT category, valid_until, session_id, task_id, metadata_json FROM memory_meta WHERE id = ?",
            (meta_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"记忆不存在: {meta_id}")

        old = dict(row)

        # 写入新记忆
        cur.execute("INSERT INTO memory_fts (content) VALUES (?)", (new_content,))
        new_fts_rowid = cur.lastrowid

        cur.execute(
            """INSERT INTO memory_meta
                (fts_rowid, category, created_at, valid_until,
                 session_id, task_id, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                new_fts_rowid,
                old["category"],
                now,
                old["valid_until"],
                old["session_id"],
                old["task_id"],
                old["metadata_json"],
            ),
        )
        new_id = cur.lastrowid

        # 标记旧记忆被替代
        cur.execute(
            """UPDATE memory_meta
                SET superseded_by = ?, valid_until = ?, frozen = 0
                WHERE id = ?""",
            (new_id, now, meta_id),
        )

        logger.debug("记忆 #%s 已被 #%s 替代", meta_id, new_id)


def memory_delete(meta_id: int) -> bool:
    """删除记忆（物理删除 FTS + 元数据）。"""
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT fts_rowid FROM memory_meta WHERE id = ?", (meta_id,))
        row = cur.fetchone()
        if row is None:
            return False

        fts_rowid = row["fts_rowid"]
        cur.execute("DELETE FROM memory_meta WHERE id = ?", (meta_id,))
        cur.execute("DELETE FROM memory_fts WHERE rowid = ?", (fts_rowid,))
        return True


# ═══════════════════════════════════════════════════════════════
# Frozen Snapshot — 保护前缀缓存
# ═══════════════════════════════════════════════════════════════

def freeze_stable_memories(inactivity_days: int = 3) -> int:
    """冻结稳定记忆，保护前缀缓存。

    问题：System Prompt 频繁变动 → Prefix Cache 永远不命中 → Token 账单爆炸
    解法：将 N 天内未变动的核心记忆标记为 frozen
    冻结区属于 Stable Prefix → Cache 命中率回到 80%+

    只冻结 persistent 类且未被 superseded 的记忆。
    """
    cutoff = (datetime.now() - timedelta(days=inactivity_days)).isoformat()

    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE memory_meta SET frozen = 1
                WHERE category = 'persistent'
                AND frozen = 0
                AND superseded_by IS NULL
                AND created_at < ?""",
            (cutoff,),
        )
        count = cur.rowcount

    logger.info("🧊 冻结了 %s 条稳定记忆", count)
    return count


def get_frozen_snapshot(max_entries: int = 50) -> List[Dict[str, Any]]:
    """获取冻结记忆快照，用于注入 System Prompt 的 Stable Prefix。"""
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT m.id, f.content, m.category, m.created_at, m.access_count
                FROM memory_fts f
                JOIN memory_meta m ON f.rowid = m.fts_rowid
                WHERE m.frozen = 1
                AND m.superseded_by IS NULL
                ORDER BY m.access_count DESC, m.created_at DESC
                LIMIT ?""",
            (max_entries,),
        )
        return [dict(row) for row in cur.fetchall()]


# ═══════════════════════════════════════════════════════════════
# 归纳层 — Auto-Dream
# ═══════════════════════════════════════════════════════════════

def mark_superseded(old_id: int, new_id: int) -> None:
    """旧记忆被新记忆替代。调用后旧记忆不再参与主动搜索。"""
    now = datetime.now().isoformat()

    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE memory_meta
                SET superseded_by = ?, valid_until = ?, frozen = 0
                WHERE id = ?""",
            (new_id, now, old_id),
        )

    logger.info("记忆 #%s 已被 #%s 替代", old_id, new_id)


def archive_stale_memories(stale_days: int = 30) -> int:
    """将超过 N 天未引用的 persistent 记录降级为 archived。"""
    now = datetime.now().isoformat()
    cutoff = (datetime.now() - timedelta(days=stale_days)).isoformat()

    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE memory_meta SET category = 'archived', frozen = 0
                WHERE category = 'persistent'
                AND (last_accessed < ? OR last_accessed IS NULL)
                AND created_at < ?
                AND superseded_by IS NULL""",
            (cutoff, cutoff),
        )
        count = cur.rowcount

    logger.info("🗄️ 归档了 %s 条过期记忆", count)
    return count


# ═══════════════════════════════════════════════════════════════
# 统计
# ═══════════════════════════════════════════════════════════════

def memory_stats() -> Dict[str, Any]:
    """数据库统计信息。"""
    with _get_conn() as conn:
        cur = conn.cursor()

        cur.execute("SELECT category, COUNT(*) FROM memory_meta GROUP BY category")
        by_category = dict(cur.fetchall())

        cur.execute("SELECT COUNT(*) FROM memory_meta WHERE superseded_by IS NOT NULL")
        superseded = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM memory_meta WHERE frozen = 1")
        frozen = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM memory_meta")
        total = cur.fetchone()[0]

    return {
        "total": total,
        "by_category": by_category,
        "superseded": superseded,
        "frozen": frozen,
    }
