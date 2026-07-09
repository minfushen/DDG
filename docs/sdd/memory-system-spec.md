# Agent Memory System 设计规格

> **定位**：本规范描述 `backend/app/memory/` 下记忆系统的架构、数据模型、接口与配置，是记忆模块接入任务链路的工程契约。
>
> **参考**：Feynman Build Workshop 01 — Agent Memory System；现有 `cache_store.py` 精确缓存层。

---

## 1. 设计目标

| 目标 | 度量 | 当前基线 |
|------|------|---------|
| 降低重复搜索成本 | 同一企业 30 天内重复搜索次数 | 3~5 次 |
| 降低重复 LLM 调用成本 | 相同提示复用率 | 0%（无记忆） |
| 复用历史企业画像 | 已有画像的企业再次尽调时直接复用 | 0% |
| 降低 Token 账单 | Prefix Cache 命中率 | 不稳定（频繁变动） |

**核心假设**：银行对公尽调中，同一企业可能被多次查询（贷前尽调 → 贷中审批 → 贷后预警），且企业画像（工商/财务/司法）在 30~90 天内变化缓慢。记忆系统将这些沉淀复用，避免每次都走“采集 → 分析 → 生成”的完整链路。

---

## 2. 架构全景

记忆系统采用 **4 层架构**，从下到上依次为：

```
┌──────────────────────────────────────────────────────────────┐
│  L4: 向量库 / 知识图谱（预留）                                 │
│      未来接入向量检索（Chroma/Milvus）和知识图谱，实现语义匹配   │
│      当前：预留接口，不阻塞主线                                │
└──────────────────────────────────────────────────────────────┘
                              ▲
                              │ 语义索引（预留）
┌──────────────────────────────────────────────────────────────┐
│  L3: 归纳层（Auto-Dream）                                    │
│      - 去重：相同/相似内容合并                                 │
│      - 冲突检测：新旧记忆矛盾时标记人工审核                     │
│      - 归档：过期记忆降级为 archived                           │
│      - 接口：mark_superseded / archive_stale_memories        │
└──────────────────────────────────────────────────────────────┘
                              ▲
                              │ 定期 consolidate
┌──────────────────────────────────────────────────────────────┐
│  L2: Frozen Snapshot（冻结快照）                               │
│      - 保护 Prefix Cache：System Prompt 头部放置稳定记忆          │
│      - 冻结区属于 Stable Prefix → Cache 命中率回到 80%+        │
│      - 触发：freeze_stable_memories(inactivity_days=3)        │
│      - 读取：get_frozen_snapshot(max_entries=50)              │
└──────────────────────────────────────────────────────────────┘
                              ▲
                              │ 冻结 + 搜索
┌──────────────────────────────────────────────────────────────┐
│  L1: SQLite + FTS5 (trigram) 全文索引                         │
│      - memory_fts: FTS5 虚拟表，content 字段 trigram 分词      │
│      - memory_meta: 元数据表，管理分类/时效/冻结/访问统计       │
│      - 降级：无 FTS5 时自动回退到 LIKE 搜索                    │
└──────────────────────────────────────────────────────────────┘
```

**设计哲学**：
- **L1 必须自给自足**：不依赖外部服务（向量库、Redis），单机 SQLite 即可运行。
- **L2 是成本优化**：Frozen Snapshot 不增加功能，专门降低 Token 成本。
- **L3 是质量保障**：归纳层保证记忆不膨胀、不冲突、不过期。
- **L4 是未来扩展**：语义检索和知识图谱作为预留，当前不实现但接口兼容。

---

## 3. 数据模型

### 3.1 表结构

#### `memory_fts` — FTS5 全文索引表

| 字段 | 类型 | 说明 |
|------|------|------|
| `rowid` | INTEGER | FTS5 隐式主键，与 `memory_meta.fts_rowid` 外键关联 |
| `content` | TEXT | 记忆全文内容，trigram 分词索引 |

- 创建语句：`CREATE VIRTUAL TABLE memory_fts USING fts5(content, tokenize='trigram')`
- trigram 分词器支持 CJK 部分匹配（3 字及以上中文、英文均可命中）
- 降级方案：无 FTS5 时创建普通表 `CREATE TABLE memory_fts(rowid PRIMARY KEY, content TEXT)`，搜索退化为 `LIKE '%query%'`

#### `memory_meta` — 元数据表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | 元数据主键 |
| `fts_rowid` | INTEGER | FK → memory_fts(rowid) | 关联全文表 |
| `category` | TEXT | NOT NULL, DEFAULT 'persistent' | 三分类：persistent / session / archived |
| `frozen` | INTEGER | NOT NULL, DEFAULT 0 | 0=普通, 1=冻结（Stable Prefix） |
| `created_at` | TEXT | NOT NULL | ISO 8601 创建时间 |
| `valid_until` | TEXT | NULLABLE | ISO 8601 过期时间，NULL=永久有效 |
| `superseded_by` | INTEGER | FK → memory_meta(id) | 被新记忆替代，替代后不再参与主动搜索 |
| `last_accessed` | TEXT | NULLABLE | 最后一次访问时间 |
| `access_count` | INTEGER | DEFAULT 0 | 累计访问次数 |
| `session_id` | TEXT | NULLABLE | 会话隔离标识（短期记忆用） |
| `task_id` | TEXT | NULLABLE | 任务隔离标识（短期记忆用） |
| `metadata_json` | TEXT | NULLABLE | JSON 扩展字段（enterprise, title, preference_type 等） |

### 3.2 索引

```sql
CREATE INDEX idx_memory_category ON memory_meta(category);
CREATE INDEX idx_memory_created   ON memory_meta(created_at);
CREATE INDEX idx_memory_valid     ON memory_meta(valid_until);
CREATE INDEX idx_memory_frozen    ON memory_meta(frozen);
CREATE INDEX idx_memory_session   ON memory_meta(session_id);
CREATE INDEX idx_memory_task      ON memory_meta(task_id);
```

### 3.3 实体关系图

```
memory_fts (1) ──────── (N) memory_meta
   rowid                    fts_rowid (FK)
   content                  category / frozen / created_at
                            valid_until / superseded_by / last_accessed
                            access_count / session_id / task_id / metadata_json
```

---

## 4. 三分类机制

### 4.1 分类定义

| 分类 | 标识 | 生命周期 | 典型内容 | 冻结策略 |
|------|------|---------|---------|---------|
| **persistent** | 跨会话持久 | 默认永久，可设 valid_until | 企业画像、分析结论、用户偏好、踩坑教训、技术决策 | 可冻结（freeze_stable_memories） |
| **session** | 当前会话 | 会话结束可丢弃 | 用户对话、工具结果、LLM 缓存命中记录、临时上下文 | 不冻结 |
| **archived** | 归档 | 不再参与主动搜索，但可时间旅行查询 | 被替代的旧记忆、过期记忆、手动归档内容 | 不冻结 |

### 4.2 自动分类规则

`classify_memory(content: str)` 函数基于关键词规则引擎自动分类（生产级可替换为 LLM 分类器）：

```python
# 规则优先级：archived > persistent > session > default(persistent)

# archived 关键词（最高优先级）
已废弃, deprecated, 过时, obsolete, 不再使用

# persistent 关键词
偏好, prefer, 企业画像, 画像, 修复, fix, bug, crash,
决策, 选择, 配置, config, 规则, rule, 总是, always,
架构, architecture, 踩坑, 教训, 分析结论, 结论, 画像

# session 关键词
临时, temp, 中间, intermediate, 单次, 测试,
output:, result:, 响应:, response:,
用户说, 用户输入, ai回复, 工具调用, tool call,
搜索, search, fetch, 查询, query
```

**默认策略**：未命中任何关键词时，保守分类为 `persistent`（宁可存错，不可漏存）。

---

## 5. 时效管理

每条记忆携带 5 个时间维度字段，形成完整的生命周期管理：

| 字段 | 语义 | 使用场景 |
|------|------|---------|
| `created_at` | 创建时间 | 排序、冻结阈值计算、归档阈值计算 |
| `valid_until` | 过期时间 | 搜索时自动排除（`include_expired=False`）；NULL = 永久 |
| `superseded_by` | 被替代者 ID | 内容更新时，旧记录标记 superseded，新记录创建；替代后旧记录不再参与搜索 |
| `last_accessed` | 最后访问时间 | 归档判断：N 天未访问 → archived |
| `access_count` | 访问次数 | 冻结排序：高访问记忆优先放入 Stable Prefix；命中统计 |

### 5.1 生命周期流转

```
创建 (created_at)
   │
   ├─► 正常访问 ──► 更新 access_count + last_accessed
   │
   ├─► 被更新 ──► 新记录创建，旧记录 superseded_by = new_id
   │                旧记录 valid_until = now, frozen = 0
   │
   ├─► 冻结 (freeze_stable_memories) ──► frozen = 1
   │      条件：persistent + superseded_by IS NULL + created_at <  cutoff
   │
   ├─► 过期 (valid_until < now) ──► 搜索时自动排除
   │
   └─► 归档 (archive_stale_memories) ──► category = 'archived', frozen = 0
          条件：persistent + (last_accessed < cutoff OR NULL) + created_at < cutoff
```

---

## 6. Frozen Snapshot

### 6.1 问题定义

LLM 推理成本中，**System Prompt（前缀）**的 Token 每次请求都要重新计算。如果 System Prompt 频繁变动（如动态插入最新记忆），则 **Prefix Cache 永远不命中**，导致：
- 同样的前缀内容被重复编码
- Token 账单膨胀（尤其长 System Prompt 场景）

### 6.2 解决方案

将 **N 天内未变动的核心记忆**标记为 `frozen = 1`，这些冻结记忆构成 **Stable Prefix**：

```
Prompt 结构：
┌─────────────────────────────────────┐
│  Stable Prefix（frozen 记忆）        │  ← 变动极少 → Prefix Cache 命中
│  ─────────────────────────────────  │
│  动态上下文（session 记忆 + 新检索）   │  ← 每次请求不同 → Cache  miss 仅影响尾部
│  ─────────────────────────────────  │
│  用户输入                            │
└─────────────────────────────────────┘
```

**预期效果**：冻结区属于 Stable Prefix → Cache 命中率回到 **80%+**。

### 6.3 冻结规则

- 仅冻结 `category = 'persistent'` 的记录
- 排除已被 `superseded` 的记录
- 冻结阈值天数：`inactivity_days`（默认 3 天）
- 冻结后记忆仍可被搜索，但优先在 `prefer_frozen=True` 时排在前面

### 6.4 读取接口

`get_frozen_snapshot(max_entries=50)` 按 `access_count DESC, created_at DESC` 排序，选取最稳定的 Top N 记忆，用于注入 System Prompt。

---

## 7. 归纳层

归纳层负责记忆的“质量控制”，防止记忆膨胀、冲突和过期。提供以下接口：

### 7.1 标记替代（mark_superseded）

```python
def mark_superseded(old_id: int, new_id: int) -> None
```

- 旧记忆被新记忆替代后，旧记录标记 `superseded_by = new_id`
- 替代后旧记忆 `frozen = 0`，不再参与主动搜索
- 物理记录保留，支持“时间旅行”查询历史版本

### 7.2 归档过期（archive_stale_memories）

```python
def archive_stale_memories(stale_days: int = 30) -> int
```

- 将超过 `stale_days` 天未引用的 `persistent` 记录降级为 `archived`
- 判断条件：`(last_accessed < cutoff OR last_accessed IS NULL) AND created_at < cutoff`
- 归档时 `frozen = 0`，释放 Stable Prefix 空间
- 返回归档记录数

### 7.3 统一归纳（consolidate）

`LongTermMemory.consolidate()` 将上述操作打包：

```python
def consolidate(consolidation_days: Optional[int] = None) -> Dict[str, int]:
    # 1. 冻结稳定记忆（inactivity_days = consolidation_days）
    # 2. 归档过期记忆（stale_days = consolidation_days * 2）
    return {"frozen": frozen_count, "archived": archived_count}
```

**建议频率**：每天定时运行一次（如凌晨 3 点），或每次任务完成后手动触发。

---

## 8. 与现有缓存的关系

### 8.1 分工对比

| 维度 | `cache_store`（精确缓存） | `memory`（上下文记忆） |
|------|------------------------|----------------------|
| **定位** | 精确匹配，减少重复外部 API / LLM 调用 | 模糊检索，复用历史上下文 |
| **匹配方式** | SHA256 哈希（tool_name + args / model + prompt） | FTS5 trigram 全文搜索（关键词/语义） |
| **存储内容** | 工具结果 JSON、LLM 响应 JSON | 企业画像、分析结论、对话历史、偏好 |
| **时效** | TTL 精确控制（秒级） | 有效期管理（天/月/永久） |
| **生命周期** | 命中即复用，过期即删除 | 被替代后保留历史（superseded），支持时间旅行 |
| **成本优化** | 减少外部 API 调用费和 LLM 推理费 | 减少重复搜索和 Token 前缀编码费 |
| **数据层** | `ddg_cache.sqlite3`（tool_cache + llm_cache） | `memory.sqlite3`（memory_fts + memory_meta） |

### 8.2 协作模式

```
用户请求
   │
   ▼
[1] cache_store.get_tool_cache(cache_key) ──► 精确命中？直接返回（无 LLM 调用）
   │                                         未命中 → 继续
   ▼
[2] memory.search(query) ──► 找到历史企业画像/分析结论？直接复用（无搜索）
   │                         未命中 → 继续
   ▼
[3] 执行真实搜索 / LLM 调用
   │
   ▼
[4] cache_store.set_tool_cache(...) ──► 缓存精确结果（短期）
   │
   ▼
[5] memory.add(...) ──► 沉淀记忆（长期）
```

**关键区别**：
- `cache_store` 是 **“同一请求的重复执行”** → 精确匹配，完全复用
- `memory` 是 **“相似请求的历史沉淀”** → 模糊匹配，提供上下文

---

## 9. 配置项

所有配置集中在 `backend/app/config/settings.py`：

| 配置项 | 类型 | 默认值 | 环境变量 | 说明 |
|--------|------|--------|---------|------|
| `ENABLE_SHORT_TERM_MEMORY` | bool | `True` | `ENABLE_SHORT_TERM_MEMORY` | 短期记忆总开关 |
| `ENABLE_LONG_TERM_MEMORY` | bool | `True` | `ENABLE_LONG_TERM_MEMORY` | 长期记忆总开关 |
| `MEMORY_DB_PATH` | str | `""` | `MEMORY_DB_PATH` | 记忆数据库路径；空 = 默认路径 `db/memory/memory.sqlite3` |
| `MEMORY_FREEZE_DAYS` | int | `3` | `MEMORY_FREEZE_DAYS` | 冻结阈值：N 天内未变动的 persistent 记忆标记为 frozen |
| `MEMORY_CONSOLIDATION_DAYS` | int | `7` | `MEMORY_CONSOLIDATION_DAYS` | 归纳阈值：consolidate 时冻结超过 N 天的稳定记忆 |
| `MEMORY_STALE_DAYS` | int | `30` | `MEMORY_STALE_DAYS` | 归档阈值：超过 N 天未访问的 persistent 记忆降级为 archived |

### 9.1 配置依赖关系

```
consolidate 执行时：
  freeze_stable_memories(inactivity_days = MEMORY_CONSOLIDATION_DAYS)     # 默认 7 天
  archive_stale_memories(stale_days = MEMORY_CONSOLIDATION_DAYS * 2)      # 默认 14 天

手动 freeze 时：
  freeze_stable_memories(inactivity_days = MEMORY_FREEZE_DAYS)            # 默认 3 天
```

---

## 10. 接口清单

### 10.1 ShortTermMemory（`backend/app/memory/short_term.py`）

**初始化**

```python
class ShortTermMemory:
    def __init__(self, session_id: str, task_id: Optional[str] = None)
```

- `session_id`: 会话 ID（如用户会话、WebSocket 连接）
- `task_id`: 可选任务 ID（如研究任务 ID），用于进一步隔离

**写入接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `add` | `add(content, role=None, metadata=None) -> Optional[int]` | 通用添加 |
| `add_user_message` | `add_user_message(message, metadata=None) -> Optional[int]` | 记录用户输入 |
| `add_assistant_message` | `add_assistant_message(message, metadata=None) -> Optional[int]` | 记录 AI 回复 |
| `add_tool_result` | `add_tool_result(tool_name, result_summary, success=True, cache_hit=False, metadata=None) -> Optional[int]` | 记录工具调用结果 |
| `add_llm_cache_hit` | `add_llm_cache_hit(prompt_summary, model, metadata=None) -> Optional[int]` | 记录 LLM 缓存命中 |
| `add_system_event` | `add_system_event(event, metadata=None) -> Optional[int]` | 记录系统事件 |

**读取接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `get_recent` | `get_recent(n=10) -> List[Dict]` | 最近 N 条记忆 |
| `get_by_role` | `get_by_role(role, n=10) -> List[Dict]` | 按角色过滤最近 N 条 |
| `search` | `search(query, limit=5) -> List[Dict]` | 全文搜索 |
| `get_context` | `get_context(max_entries=20) -> str` | 获取上下文文本，适合注入 Prompt |
| `to_messages` | `to_messages(max_entries=20) -> List[Dict[str, str]]` | 转 LangChain 消息格式 |

**管理接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `clear` | `clear() -> None` | 清空当前会话短期记忆（标记为 archived，不物理删除） |
| `stats` | `stats() -> Dict[str, Any]` | 返回统计信息 |

### 10.2 LongTermMemory（`backend/app/memory/long_term.py`）

**初始化**

```python
class LongTermMemory:
    def __init__(self, namespace: Optional[str] = None)
```

- `namespace`: 命名空间，用于隔离不同租户/环境的数据；默认 `"global"`

**写入接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `add` | `add(content, title=None, category='persistent', enterprise=None, valid_days=None, metadata=None) -> Optional[int]` | 通用添加 |
| `add_enterprise_profile` | `add_enterprise_profile(enterprise_name, profile, metadata=None) -> Optional[int]` | 添加/更新企业画像（自动 superseded） |
| `add_analysis_conclusion` | `add_analysis_conclusion(enterprise_name, conclusion, analysis_type='general', metadata=None) -> Optional[int]` | 添加分析结论 |
| `add_user_preference` | `add_user_preference(preference, preference_type='general', metadata=None) -> Optional[int]` | 添加用户偏好 |
| `add_lesson_learned` | `add_lesson_learned(lesson, context=None, metadata=None) -> Optional[int]` | 记录踩坑/教训 |

**读取接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `search` | `search(query, category=None, enterprise=None, limit=10) -> List[Dict]` | 全文搜索（优先 frozen） |
| `search_by_enterprise` | `search_by_enterprise(enterprise_name, limit=10) -> List[Dict]` | 搜索某企业所有记忆 |
| `get_enterprise_profile` | `get_enterprise_profile(enterprise_name) -> Optional[Dict]` | 获取最新企业画像 |
| `get_recent` | `get_recent(n=10) -> List[Dict]` | 最近 N 条长期记忆 |
| `get_frozen_context` | `get_frozen_context(max_entries=20) -> str` | 获取冻结记忆上下文，用于 System Prompt |

**更新接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `update` | `update(meta_id, new_content, metadata=None) -> Optional[int]` | 更新内容（创建新记录，旧记录 superseded） |

**管理接口**

| 方法 | 签名 | 用途 |
|------|------|------|
| `freeze` | `freeze(inactivity_days=None) -> int` | 冻结稳定记忆（默认 MEMORY_FREEZE_DAYS） |
| `archive_stale` | `archive_stale(stale_days=None) -> int` | 归档过期记忆（默认 MEMORY_STALE_DAYS） |
| `consolidate` | `consolidate(consolidation_days=None) -> Dict[str, int]` | 运行归纳：冻结 + 归档 |
| `stats` | `stats() -> Dict[str, Any]` | 返回统计信息 |

### 10.3 MemoryManager（统一入口）

```python
class MemoryManager:
    def __init__(self, session_id: str, task_id: Optional[str] = None)
    # 属性：self.short_term: ShortTermMemory
    #       self.long_term: LongTermMemory

    @staticmethod
    def init_db() -> None
```

### 10.4 底层存储 API（`memory_store.py`）

| 函数 | 签名 | 用途 |
|------|------|------|
| `init_memory_db` | `init_memory_db() -> None` | 初始化数据库（FTS5 + 元数据表 + 索引） |
| `memory_add` | `memory_add(content, category=None, valid_until=None, session_id=None, task_id=None, metadata=None) -> int` | 添加记忆 |
| `memory_search` | `memory_search(query, limit=5, category=None, session_id=None, task_id=None, include_expired=False, prefer_frozen=True) -> List[Dict]` | 搜索 |
| `memory_get_recent` | `memory_get_recent(limit=10, category=None, session_id=None, task_id=None) -> List[Dict]` | 最近记忆 |
| `memory_update_content` | `memory_update_content(meta_id, new_content) -> None` | 更新内容（superseded） |
| `memory_delete` | `memory_delete(meta_id) -> bool` | 物理删除 |
| `freeze_stable_memories` | `freeze_stable_memories(inactivity_days=3) -> int` | 冻结稳定记忆 |
| `get_frozen_snapshot` | `get_frozen_snapshot(max_entries=50) -> List[Dict]` | 获取冻结快照 |
| `mark_superseded` | `mark_superseded(old_id, new_id) -> None` | 标记替代 |
| `archive_stale_memories` | `archive_stale_memories(stale_days=30) -> int` | 归档过期记忆 |
| `memory_stats` | `memory_stats() -> Dict[str, Any]` | 统计信息 |
| `classify_memory` | `classify_memory(content: str) -> str` | 三分类规则引擎 |

---

## 11. 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-19 | 首版，覆盖架构、数据模型、三分类、时效管理、Frozen Snapshot、归纳层、缓存关系、配置项、接口清单 |
