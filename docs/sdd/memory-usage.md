# Agent Memory System 使用说明

> **目标读者**：后端开发者、智能体工程师、运维人员。
>
> **前置条件**：已阅读 `memory-system-spec.md` 了解架构和数据模型。

---

## 1. 快速接入

```python
from app.memory import MemoryManager

# 初始化数据库（应用启动时执行一次）
MemoryManager.init_db()

# 创建记忆管理器
mm = MemoryManager(session_id="sess_001", task_id="task_001")
```

3 行代码完成接入。`mm.short_term` 提供会话级记忆，`mm.long_term` 提供跨会话知识沉淀。

---

## 2. 短期记忆用法

### 2.1 记录对话

```python
stm = mm.short_term

# 记录用户输入
stm.add_user_message("帮我分析腾讯控股的财务风险")

# 记录 AI 回复
stm.add_assistant_message("腾讯控股 2024 年资产负债率为 42.3%，低于行业均值...")
```

### 2.2 记录工具结果

```python
# 正常工具调用
stm.add_tool_result(
    tool_name="searxng",
    result_summary="找到3条关于腾讯控股的新闻",
    success=True,
    cache_hit=False,
)

# 缓存命中（复用了 cache_store 的结果）
stm.add_tool_result(
    tool_name="searxng",
    result_summary="找到3条关于腾讯控股的新闻",
    success=True,
    cache_hit=True,
)

# 工具调用失败
stm.add_tool_result(
    tool_name="cninfo_api",
    result_summary="接口超时，返回 504",
    success=False,
)
```

### 2.3 记录 LLM 缓存命中

```python
stm.add_llm_cache_hit(
    prompt_summary="分析企业偿债能力",
    model="qwen3.7-max-preview",
)
```

### 2.4 获取上下文注入 Prompt

```python
# 获取纯文本上下文（适合直接拼接）
context = stm.get_context(max_entries=20)

# 获取 LangChain 消息格式（适合传给 LangChain/LLM）
messages = stm.to_messages(max_entries=20)
# 返回：[{"role": "human", "content": "..."}, {"role": "ai", "content": "..."}]
```

### 2.5 搜索和清理

```python
# 搜索当前会话的记忆
results = stm.search("腾讯控股", limit=5)

# 清空当前会话（标记为 archived，支持时间旅行）
stm.clear()
```

---

## 3. 长期记忆用法

### 3.1 企业画像

```python
ltm = mm.long_term

# 添加企业画像（如果已存在，自动更新，旧记录标记 superseded）
ltm.add_enterprise_profile(
    enterprise_name="腾讯控股",
    profile="大型互联网科技公司，主营业务包括社交、游戏、金融科技...",
)

# 获取企业画像（最新的一条）
profile = ltm.get_enterprise_profile("腾讯控股")
```

### 3.2 分析结论

```python
# 添加财务分析结论
ltm.add_analysis_conclusion(
    enterprise_name="腾讯控股",
    conclusion="偿债能力良好，资产负债率 42.3% 低于行业均值 55%...",
    analysis_type="financial",
)

# 添加法律风险分析结论
ltm.add_analysis_conclusion(
    enterprise_name="腾讯控股",
    conclusion="近 3 年无重大诉讼记录，司法风险低...",
    analysis_type="legal",
)
```

### 3.3 用户偏好

```python
# 记录用户偏好
ltm.add_user_preference(
    preference="报告优先展示财务风险和法律风险",
    preference_type="report_style",
)

ltm.add_user_preference(
    preference="重点关注制造业和科技企业",
    preference_type="industry_focus",
)
```

### 3.4 踩坑/教训

```python
ltm.add_lesson_learned(
    lesson="巨潮资讯 API 在财报季高峰期（4月/8月/10月）响应极慢，建议提前缓存",
    context="2026-04-15 查询腾讯控股年报时接口超时 3 次",
)
```

### 3.5 搜索长期记忆

```python
# 通用搜索（优先返回 frozen 记忆）
results = ltm.search("腾讯控股 财务风险", limit=5)

# 按类别搜索
results = ltm.search("偿债能力", category="persistent", limit=5)

# 按企业搜索
results = ltm.search_by_enterprise("腾讯控股", limit=10)
```

### 3.6 冻结记忆注入 System Prompt

```python
# 获取冻结记忆上下文，注入 System Prompt 的 Stable Prefix
frozen_context = ltm.get_frozen_context(max_entries=20)

# 示例：构建 Prompt
system_prompt = f"""你是一位专业的银行对公信贷分析师。

以下是已沉淀的企业知识和分析规则（Stable Context）：
{frozen_context}

当前任务：基于用户输入进行尽调分析。
"""
```

---

## 4. 配置最佳实践

### 4.1 开发环境

```env
# .env
ENABLE_SHORT_TERM_MEMORY=True
ENABLE_LONG_TERM_MEMORY=True
MEMORY_DB_PATH=./db/memory/dev_memory.sqlite3
MEMORY_FREEZE_DAYS=1
MEMORY_CONSOLIDATION_DAYS=3
MEMORY_STALE_DAYS=7
```

- `MEMORY_FREEZE_DAYS=1`：开发时频繁重启，快速冻结记忆以测试 Prefix Cache 效果
- `MEMORY_STALE_DAYS=7`：快速验证归档逻辑
- `MEMORY_DB_PATH` 独立：避免污染测试/生产数据

### 4.2 测试环境

```env
ENABLE_SHORT_TERM_MEMORY=True
ENABLE_LONG_TERM_MEMORY=True
MEMORY_DB_PATH=./db/memory/test_memory.sqlite3
MEMORY_FREEZE_DAYS=3
MEMORY_CONSOLIDATION_DAYS=7
MEMORY_STALE_DAYS=14
```

- 配置与生产一致，但 DB 路径独立
- 每次测试运行后可检查 `memory_stats()` 验证记忆沉淀是否符合预期

### 4.3 生产环境

```env
ENABLE_SHORT_TERM_MEMORY=True
ENABLE_LONG_TERM_MEMORY=True
MEMORY_DB_PATH=/data/memory/memory.sqlite3
MEMORY_FREEZE_DAYS=3
MEMORY_CONSOLIDATION_DAYS=7
MEMORY_STALE_DAYS=30
```

- `MEMORY_STALE_DAYS=30`：企业画像 30 天后归档，适合财报季度更新节奏
- `MEMORY_FREEZE_DAYS=3`：3 天内稳定的企业画像和偏好进入 Stable Prefix
- 建议定期备份 `memory.sqlite3`（企业画像属于核心资产）

---

## 5. Frozen Snapshot 调优

### 5.1 查看 Cache 命中率

当前系统通过 `memory_stats()` 和短期记忆的 `add_llm_cache_hit` 记录间接反映 Cache 效果：

```python
from app.memory import memory_stats
from app.api.cache_store import cache_stats

# 记忆统计
mem = memory_stats()
print(f"总记忆: {mem['total']}, 冻结: {mem['frozen']}, 已替代: {mem['superseded']}")

# 精确缓存统计（对比参考）
cache = cache_stats()
print(f"工具缓存: {cache['tool_cache']['total']}, LLM缓存: {cache['llm_cache']['total']}")
```

**Frozen Snapshot 效果评估**：
- 观察 `mem['frozen']` 是否稳定增长
- 如果 `frozen` 始终为 0，说明 `MEMORY_FREEZE_DAYS` 设得过大，或 `persistent` 记忆太少
- 如果 `frozen` 增长过快，说明 `MEMORY_FREEZE_DAYS` 设得太小，Stable Prefix 膨胀

### 5.2 调整 freeze 天数

| 场景 | 建议 | 原因 |
|------|------|------|
| 每日分析新企业 | `MEMORY_FREEZE_DAYS=1` | 快速冻结，尽早享受 Cache 收益 |
| 每周批量更新画像 | `MEMORY_FREEZE_DAYS=3` | 与画像更新周期对齐，避免冻结后立刻更新导致 superseded |
| 企业画像变化缓慢 | `MEMORY_FREEZE_DAYS=7` | 减少冻结-解冻-再冻结的抖动 |
| Token 成本敏感 | `MEMORY_FREEZE_DAYS=1` + 增大 `max_entries` | 尽快冻结，扩大 Stable Prefix |

### 5.3 调优流程

```python
ltm = LongTermMemory()

# 1. 查看当前状态
print(ltm.stats())
# {'enabled': True, 'namespace': 'global', 'total': 150, 'by_category': {...}, 'superseded': 12, 'frozen': 45}

# 2. 手动触发冻结（测试效果）
frozen_count = ltm.freeze(inactivity_days=1)
print(f"本次冻结 {frozen_count} 条")

# 3. 获取冻结上下文长度（估算 Token 数）
context = ltm.get_frozen_context(max_entries=50)
print(f"冻结上下文长度: {len(context)} 字符")
# 粗略估算：中文 1 字符 ≈ 1~1.5 Token，英文 1 单词 ≈ 1~1.3 Token
```

**经验法则**：
- Stable Prefix 控制在 **500~2000 Token** 为宜（太长增加每次请求成本）
- 如果超过 2000 Token，减少 `max_entries` 或收紧 `MEMORY_FREEZE_DAYS`

---

## 6. 归纳操作

### 6.1 手动 consolidate

```python
ltm = LongTermMemory()

# 使用默认配置（MEMORY_CONSOLIDATION_DAYS）
result = ltm.consolidate()
print(f"冻结 {result['frozen']} 条，归档 {result['archived']} 条")

# 自定义天数
result = ltm.consolidate(consolidation_days=3)
```

### 6.2 定时 consolidate（推荐）

在应用启动时或任务链路完成后自动触发：

```python
# 任务完成后归纳
async def after_task_complete(task_id: str):
    mm = MemoryManager(session_id="sess_001", task_id=task_id)
    result = mm.long_term.consolidate()
    logger.info(f"任务 {task_id} 记忆归纳完成: {result}")
```

**建议时机**：
- 每个尽调任务完成后（`report_ready` → `under_review` 时）
- 每日凌晨定时任务（配合 APScheduler/Celery）
- 数据库容量告警时（`total > 阈值`）

### 6.3 单独执行冻结或归档

```python
# 仅冻结（不归档）
ltm.freeze(inactivity_days=3)

# 仅归档（不冻结）
ltm.archive_stale(stale_days=30)
```

---

## 7. 常见问题

### 7.1 记忆不生效（搜索返回空）

**排查步骤**：

1. **检查开关**
   ```python
   from app.config import settings
   print(settings.ENABLE_SHORT_TERM_MEMORY)  # 应为 True
   print(settings.ENABLE_LONG_TERM_MEMORY)     # 应为 True
   ```

2. **检查数据库是否初始化**
   ```python
   from app.memory import MemoryManager
   MemoryManager.init_db()  # 应用启动时执行
   ```

3. **检查分类结果**
   ```python
   from app.memory.memory_store import classify_memory
   print(classify_memory("用户输入：帮我分析腾讯"))  # 可能是 'session'
   print(classify_memory("企业画像：腾讯控股"))      # 应该是 'persistent'
   ```
   如果分类结果不符合预期，手动指定 `category` 参数：
   ```python
   memory_add(content="...", category="persistent")
   ```

4. **检查是否被 superseded**
   ```python
   from app.memory.memory_store import memory_stats
   print(memory_stats())  # 查看 'superseded' 数量
   ```
   被替代的记录不再参与搜索，但物理存在。

### 7.2 搜索结果不对（相关性差）

**排查步骤**：

1. **检查 FTS5 是否可用**
   ```python
   from app.memory.memory_store import _has_fts5
   print(_has_fts5())  # 应为 True
   ```
   如果为 False，系统降级为 LIKE 搜索，短查询（1-2 字中文）可能不准确。

2. **关键词长度**
   - FTS5 trigram 对 **3 字及以上**中文支持最好
   - 2 字及以下中文自动退化为 LIKE，可能漏匹配
   - 建议搜索词 ≥ 3 个字符

3. **检查是否被过滤**
   ```python
   # 默认 exclude_expired=True，过期记录不返回
   results = memory_search("腾讯", include_expired=True)  # 测试时包含过期
   ```

4. **检查 category/session_id/task_id 过滤**
   ```python
   # 如果添加了记忆时指定了 session_id，搜索时也必须指定
   stm = ShortTermMemory(session_id="sess_A")
   stm.add("测试内容")  # 自动带上 session_id="sess_A"
   
   # 用另一个 session 搜索会找不到
   stm2 = ShortTermMemory(session_id="sess_B")
   stm2.search("测试")  # 返回空
   ```

### 7.3 Token 成本没降低

**排查步骤**：

1. **检查 frozen 数量**
   ```python
   from app.memory import memory_stats
   stats = memory_stats()
   print(f"frozen: {stats['frozen']}")
   # 如果为 0，说明没有记忆进入 Stable Prefix
   ```

2. **检查 freeze 阈值**
   ```python
   from app.config import settings
   print(settings.MEMORY_FREEZE_DAYS)  # 默认 3
   ```
   如果记忆都是今天创建的，3 天内不会冻结。开发环境可设为 1 测试。

3. **检查 Prompt 结构**
   Frozen Snapshot 只在 **System Prompt 头部**有效。如果 Prompt 结构是：
   ```
   用户输入 + 动态检索 + 系统指令   ❌ 前缀不稳定
   ```
   而不是：
   ```
   系统指令（含 frozen 记忆）+ 用户输入  ✅ 前缀稳定
   ```
   需要调整 Prompt 拼接顺序。

4. **检查记忆更新频率**
   如果 `persistent` 记忆频繁被 `update()`（产生 superseded），冻结的记忆会被解除冻结。减少不必要的更新，或延长 `MEMORY_FREEZE_DAYS`。

### 7.4 数据库文件膨胀

**排查步骤**：

1. **查看统计**
   ```python
   from app.memory import memory_stats
   print(memory_stats())
   ```

2. **运行归档**
   ```python
   ltm = LongTermMemory()
   ltm.archive_stale(stale_days=14)  # 缩短归档周期
   ```

3. **物理清理（谨慎）**
   如果需要释放空间，手动删除 `archived` 和 `superseded` 记录：
   ```python
   from app.memory.memory_store import _get_conn
   with _get_conn() as conn:
       cur = conn.cursor()
       # 获取待删除的 fts_rowid
       cur.execute("SELECT fts_rowid FROM memory_meta WHERE category='archived'")
       # ... 依次删除 memory_meta 和 memory_fts
   ```
   建议先备份数据库。

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-06-19 | 首版，覆盖快速接入、短期/长期记忆用法、配置最佳实践、Frozen Snapshot 调优、归纳操作、常见问题 |
