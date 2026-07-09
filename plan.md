# Agent Memory System 改造计划

> 基于 [Feynman Build Workshop 01](https://github.com/LesterYu0/feynman-build-workshop/tree/main/episodes/01-agent-memory-system) 的七步设计记忆系统，改造当前仓库的 `app.memory` 模块。
> 目标：通过记忆机制缓存搜索 API 和 LLM 调用上下文，显著降低开发测试成本。

---

## 现状

- `short_term.py`：纯内存列表，无持久化，无FTS5，无引用
- `long_term.py`：JSON 文件持久化，无FTS5，无时间戳管理，无引用
- `settings.py`：无记忆开关（只有 `ENABLE_TOOL_CACHE` / `ENABLE_LLM_CACHE`）
- `tasks.py` / `tool_middleware.py`：无记忆接入
- 无测试、无文档
- 已有 `cache_store.py`（SQLite-based 工具缓存+LLM缓存），已接入工具中间件

---

## 设计原则

1. **与现有缓存互补**：`cache_store` 负责**精确缓存命中**（工具结果/LLM响应），`memory` 负责**上下文记忆**（对话历史、企业画像、失败教训）。
2. **SQLite + FTS5 地基**：零额外依赖，trigram 分词器支持中文，精确关键词召回。
3. **三分类**：`persistent`（跨会话）、`session`（当前会话）、`archived`（过时归档）。
4. **时效管理**：`created_at` + `valid_until` + `superseded_by` + `last_accessed` + `access_count`。
5. **Frozen Snapshot**：锁定 3 天内稳定记忆，保护 Prefix Cache，降低 Token 成本。
6. **归纳层**：去重、冲突检测、时效淘汰（保留接口，cron 定时调用）。
7. **配置化**：开发环境可开关，测试环境可灵活控制。

---

## 阶段分解

### Stage 1: 记忆核心模块重写（SQLite + FTS5）

**目标文件**：
- `backend/app/memory/memory_store.py` — 新增：SQLite 连接池 + FTS5 表结构 + 底层CRUD
- `backend/app/memory/short_term.py` — 重写：会话级记忆（对话、工具结果、临时上下文）
- `backend/app/memory/long_term.py` — 重写：企业级知识沉淀（画像、分析结论、偏好）
- `backend/app/memory/__init__.py` — 更新：导出 `MemoryManager`（统一入口）

**技术要点**：
- 单数据库文件：`backend/db/memory/memory.sqlite3`
- FTS5 表：`memory_fts`（trigram 分词器）
- 元数据表：`memory_meta`（category, frozen, created_at, valid_until, superseded_by, last_accessed, access_count, session_id, task_id）
- 三分类自动规则引擎（可扩展为 LLM 分类）
- 短查询自动降级为 LIKE（CJK 1-2字）

### Stage 2: 配置开关 + 任务链路接入

**目标文件**：
- `backend/app/config/settings.py` — 添加：
  - `ENABLE_SHORT_TERM_MEMORY: bool = True`
  - `ENABLE_LONG_TERM_MEMORY: bool = True`
  - `MEMORY_DB_PATH: str = ""`（空=默认路径）
  - `MEMORY_FREEZE_DAYS: int = 3`
  - `MEMORY_CONSOLIDATION_DAYS: int = 7`
  - `MEMORY_STALE_DAYS: int = 30`
- `backend/app/agents/research_engine/tool_middleware.py` — 接入：
  - 工具调用后（成功/失败）写入 `ShortTermMemory`
  - 缓存命中时记录"复用了之前的搜索结果"
  - 支持开关控制
- `backend/app/config/llm_config.py` — 接入：
  - `cached_invoke` 前后写入 `ShortTermMemory`（用户输入、AI回复、缓存命中状态）
  - 支持开关控制
- `backend/app/api/task_store.py` — 接入：
  - 新任务开始时查询 `LongTermMemory` 获取历史企业画像
  - 任务完成后将分析结论写入 `LongTermMemory`
  - 支持开关控制

### Stage 3: 测试

**目标文件**：
- `backend/tests/test_memory_core.py` — 核心功能：
  - 数据库初始化
  - 三分类自动识别
  - FTS5 精确搜索（中文/英文）
  - 短查询 LIKE 降级
  - 时效过滤（过期不返回）
  - Frozen Snapshot（冻结稳定记忆）
  - 替代/归档（superseded_by）
  - 统计信息
- `backend/tests/test_memory_integration.py` — 集成测试：
  - 工具中间件记忆写入
  - LLM 缓存记忆写入
  - 任务开始/结束时记忆查询/写入

### Stage 4: 文档

**目标文件**：
- `docs/sdd/memory-system-spec.md` — 设计规格：架构、表结构、接口、决策树
- `docs/sdd/memory-usage.md` — 使用说明：配置、API、最佳实践
- `docs/sdd/tasks.md` — 更新：添加记忆系统任务条目

---

## 文件变更清单

| 文件 | 动作 | 说明 |
|------|------|------|
| `backend/app/memory/memory_store.py` | 新增 | SQLite + FTS5 核心 |
| `backend/app/memory/short_term.py` | 重写 | 会话级记忆 |
| `backend/app/memory/long_term.py` | 重写 | 企业级知识 |
| `backend/app/memory/__init__.py` | 更新 | 统一导出 |
| `backend/app/config/settings.py` | 编辑 | 添加记忆配置 |
| `backend/app/agents/research_engine/tool_middleware.py` | 编辑 | 工具记忆写入 |
| `backend/app/config/llm_config.py` | 编辑 | LLM 记忆写入 |
| `backend/app/api/task_store.py` | 编辑 | 任务记忆查询/写入 |
| `backend/tests/test_memory_core.py` | 新增 | 核心测试 |
| `backend/tests/test_memory_integration.py` | 新增 | 集成测试 |
| `docs/sdd/memory-system-spec.md` | 新增 | 设计规格 |
| `docs/sdd/memory-usage.md` | 新增 | 使用说明 |
| `docs/sdd/tasks.md` | 编辑 | 添加任务条目 |

---

## 依赖关系

```
Stage 1 (核心模块) → Stage 2 (配置+接入) → Stage 3 (测试) → Stage 4 (文档)
```

Stage 1 和 Stage 2 内部可以并行（独立子 Agent）。
Stage 3 依赖 Stage 1+2 完成。
Stage 4 依赖全部完成。

---

## 验收标准

1. 记忆模块有独立测试且全部通过
2. 全仓库 `grep` 能搜到 `from app.memory import` 的引用（有业务代码使用）
3. `settings.py` 有 `ENABLE_SHORT_TERM_MEMORY` 和 `ENABLE_LONG_TERM_MEMORY`
4. `tool_middleware.py` 在工具调用后写入记忆
5. `task_store.py` 在任务开始时查询长期记忆
6. `docs/sdd/` 下有记忆系统文档
