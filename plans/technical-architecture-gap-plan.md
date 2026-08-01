# 技术架构功能项开发计划

> 基于 `docs/architecture/ddg-technical-architecture.yaml` 架构图，经代码逐项核实后产出。
> 核实方式：对每个标注"规划中/部分实现/已实现雏形"的组件，定位真实代码文件，确认实际实现程度。

---

## 一、核实结论：架构图标注与代码不符

架构图上 13 个非"已实现"组件，经代码核实，**6 个实际已实现（仅有缺口）**，标注需修正。修正前后的对比：

| 组件 | 架构图原标注 | 真实状态 | 主要缺口 |
|---|---|---|---|
| 多跳推理引擎 Multi-Hop | 规划中 ★ | **已实现（递归树）** | gap 检测是规则引擎、深度上限固定、缺语义依赖编排 |
| Memory Service | 规划中 M3 | **已实现** | 无 summarize、无向量检索、无抽象接口 |
| 多源数据可信度取舍 | 规划中 ★ | **已实现** | 无加权融合算法，仅冲突检测+高可信优先 |
| Runtime Skill Registry | 部分实现 | **已实现** | 无动态注册 API、无版本管理、选择硬编码 |
| 跨源一致性校验 | 已实现雏形 | **已实现** | 仅双源比对，缺多源交叉和语义校验 |
| LangGraph 状态机 | 已实现 shell | **已实现** | 未用 checkpoint/resume，prepare-execute 分两次调用 |
| Enhanced RAG | 规划中 M4 | **部分实现** | 缺 Query Rewrite/Rerank，Hybrid 仅 fallback |
| Skill-aware Planner | 部分实现 | **已实现** | skill 选择为硬编码关键词，无语义匹配 |
| Evidence Store | 已实现 | 已实现 | 无持久化（仅 in-memory）、无生命周期管理 |
| Capability Context Builder | 规划中 | **未实现** | 唯一真正未实现的组件 |
| 持久化 | 部分实现 | 部分实现 | 仅 SQLite，无 PostgreSQL/SQLAlchemy/Alembic |
| 可观测 | 部分实现 M2.5 | 部分实现 | 仅 logging，无 Langfuse/Prometheus |
| T+1 数据前置机 | 规划·私有化 | 部分实现 | 仅 schema 校验函数，无 ETL 管道 |

**真正未实现的只有 1 个：Capability Context Builder。** 其余均为"已实现但有缺口"或"部分实现"。

---

## 二、优先级分级原则

- **P0 端到端阻塞**：不修则链路不可交付或核心卖点失效（可审计性、中断恢复）
- **P1 核心能力增强**：直接提升尽调报告质量/专业度
- **P2 工程化/私有化前提**：生产部署、多租户、可观测所需
- **P3 长期演进**：不影响当前交付，按需推进

---

## 三、功能项开发清单

### P0 — 端到端阻塞（必须先做）

#### P0-1 LangGraph checkpoint/resume 原生化
- **现状**：`graph_engine.py` 已用 `StateGraph`（7 节点+条件路由），但 `prepare_plan` 后直接连 `END`，prepare 和 execute 是两次独立 `ainvoke`。`LANGGRAPH_CHECKPOINT_DIR` 配置存在但代码未接 checkpointer。HITL 中断后重启会丢状态。
- **缺口**：接入 `MemorySaver`/`SqliteSaver` checkpointer；prepare→execute 改为同一图的中断-恢复；HITL interrupt 用 LangGraph 原生 `interrupt()` 而非自定义 `active_interrupt`。
- **工作量**：2-3 天
- **依赖**：无
- **文件**：`app/agents/research_engine/graph_engine.py`、`app/api/tasks.py`

#### P0-2 Evidence Store 持久化
- **现状**：`EvidenceStore` 仅 in-memory 收集去重，任务结束即失。无法审计、无法复盘、无法跨任务引用。
- **缺口**：evidence 落 SQLite（复用 task_store 模式）；claim-evidence 关系表；evidence 生命周期（active/superseded/archived）。
- **工作量**：1-2 天
- **依赖**：无
- **文件**：`app/agents/evidence/evidence_store.py`、`app/api/task_store.py`

---

### P1 — 核心能力增强

#### P1-1 Capability Context Builder（唯一未实现组件）
- **现状**：无独立模块。上下文组装散落在 `llm_planner.py` 的 `_recent_stm_context()` 和 `skill_loader.py` 的文本拼接，是简单字符串拼接，无 token 预算裁剪。
- **缺口**：独立 `CapabilityContextBuilder`；聚合 skill/memory/rag/task_state；按优先级排序；token 预算裁剪（超长时摘要/去重/截断）。
- **工作量**：2-3 天
- **依赖**：P0-2（evidence 持久化后 context 更完整）
- **文件**：新建 `app/agents/capability/context_builder.py`

#### P1-2 Enhanced RAG 补齐 Query Rewrite + Rule Rerank
- **现状**：`knowledge_retrieval_service.py` 有向量检索+关键词降级+editable_knowledge 三路召回，Domain Isolation 已实现。但 Query Rewrite 未实现（直接用原始 query），Hybrid 是 fallback 非 score fusion，无 Rule Rerank。
- **缺口**：按任务类型改写检索 query；向量+关键词 score fusion（RRF）；按领域/标题/source_type/新鲜度规则重排。
- **工作量**：2-3 天
- **依赖**：无
- **文件**：`app/rag/knowledge_retrieval_service.py`、`app/rag/retriever.py`

#### P1-3 多源数据可信度加权融合
- **现状**：`evidence_consistency.py` 的 `detect_field_conflicts` 检测冲突并按 trust_level 裁定（高可信优先），但无加权融合算法（不做多源值加权平均）。
- **缺口**：多源同字段的加权融合（按 source_reliability × recency × confidence）；冲突 >2 源时的仲裁策略。
- **工作量**：2 天
- **依赖**：无
- **文件**：`app/agents/research_engine/evidence_consistency.py`、`app/agents/evidence/source_intelligence.py`

#### P1-4 跨源一致性多源交叉 + 语义校验
- **现状**：`reconcile_financial_providers` 对财报 17 项做双源逐项差异校验（阈值 1%/100万），`detect_field_conflicts` 对工商/司法字段做双源比对。
- **缺口**：>2 源交叉校验；非数值字段（经营范围、法人、地址）的语义一致性校验。
- **工作量**：2 天
- **依赖**：P1-3
- **文件**：`app/agents/research_engine/evidence_consistency.py`、`app/agents/tools/financial_provider_reconciliation.py`

#### P1-5 Memory Service 抽象接口 + summarize
- **现状**：`memory_store.py` + `short_term.py` + `long_term.py` 已实现 STM+LTM+MemoryManager，底层 SQLite+FTS5。`consolidate` 只做 freeze+archive。
- **缺口**：抽象 `MemoryService` 接口（write/search/summarize），底层可替换（mem0/PG/向量库）；`summarize` 方法（对同 subject 多条记忆归纳摘要）；向量检索（当前仅 FTS5 关键词）。
- **工作量**：2 天
- **依赖**：无
- **文件**：`app/memory/`

#### P1-6 多跳推理语义深度决策
- **现状**：`_route_after_followups` 基于 `current_depth < max_depth && _followups_produced_new_gaps` 做树状递归（max_depth 默认 2 可配）。`gap_reflector.py` 按 category 硬编码缺什么。
- **缺口**：基于语义的动态深度决策（gap 严重度/证据覆盖率驱动）；跨任务图式依赖编排；gap 检测从规则升级为 LLM 辅助。
- **工作量**：3-5 天
- **依赖**：P1-1
- **文件**：`app/agents/research_engine/follow_up_planner.py`、`gap_reflector.py`、`graph_engine.py`

---

### P2 — 工程化/私有化前提

#### P2-1 持久化升级 PostgreSQL + SQLAlchemy + Alembic
- **现状**：task_store/memory 全 SQLite，代码中 `postgres|sqlalchemy|alembic` 零匹配。
- **缺口**：SQLAlchemy 2.0 async ORM；Alembic 迁移；PostgreSQL 部署；连接池；多租户隔离（tenant_id/user_id）。
- **工作量**：3-5 天
- **依赖**：P0-2
- **文件**：`app/api/task_store.py`、`app/memory/memory_store.py`、新建 `alembic/`

#### P2-2 可观测接入 Langfuse + Prometheus
- **现状**：仅 Python `logging` 标准库，`langfuse|prometheus|opentelemetry` 零匹配。
- **缺口**：Langfuse LLM 调用追踪；Prometheus `/metrics`（任务状态/LLM延迟/工具成功率）；结构化 JSON 日志（request/user/task/session ID）；Grafana 看板。
- **工作量**：2-3 天
- **依赖**：无
- **文件**：新建 `app/observability/`，改 `app/main.py`

#### P2-3 Runtime Skill Registry 动态注册 + 版本管理
- **现状**：`load_skills_for_task` + `select_skill_ids_for_task` 已实现，从 SKILL.md frontmatter 加载，lru_cache 缓存。
- **缺口**：运行时动态注册/注销 skill 的 API；skill 版本管理；`select_skill_ids_for_task` 从硬编码关键词升级为语义匹配。
- **工作量**：2 天
- **依赖**：P1-1
- **文件**：`app/agents/skills/skill_loader.py`、新建 `app/api/skills.py`

#### P2-4 Skill-aware Planner 语义匹配选择
- **现状**：`select_skill_ids_for_task` 按 intent/objective 关键词硬编码匹配。
- **缺口**：基于 embedding 的语义匹配；skill 适用场景声明（frontmatter 已有字段，未用于匹配）。
- **工作量**：2 天
- **依赖**：P2-3
- **文件**：`app/agents/skills/skill_loader.py`

---

### P3 — 长期演进

#### P3-1 T+1 数据前置机 ETL 管道
- **现状**：`t1_package_tools.py` 的 `validate_t1_data_package` 仅做 schema 校验（必填字段/domain白名单/日期新鲜度/checksum），不产生也不存储数据。
- **缺口**：raw/standardized/index 三层存储；T+1 定时采集调度；ETL 管道（清洗/标准化/索引）；数据血缘。
- **工作量**：5-7 天
- **依赖**：P2-1
- **文件**：新建 `app/data_gateway/`
- **说明**：仅私有化交付需要，SaaS 可延后。

---

## 四、建议执行顺序

```
第1周：P0-1 LangGraph checkpoint/resume  +  P0-2 Evidence 持久化
       （端到端可审计、可中断恢复 —— 当前最大短板）
第2周：P1-1 Capability Context Builder  +  P1-2 Enhanced RAG 补齐
       （报告质量与 prompt 可控性）
第3周：P1-3 可信度加权融合  +  P1-4 多源交叉  +  P1-5 Memory 抽象
       （证据层专业化）
第4周：P1-6 多跳语义深度  +  P2-1 PostgreSQL  +  P2-2 可观测
       （工程化 + 推理增强，为私有化铺路）
按需：P2-3/P2-4 Skill 动态化  →  P3-1 T+1 前置机
```

**最小可交付集**：P0-1 + P0-2 + P1-1 + P1-2（约 8-11 天）即可让"已实现组件"形成闭环、报告质量显著提升。

---

## 五、与端到端测试的关系

端到端测试发现的 `parsed_intent` bug 已修复（`planner.py:63` 加 `parsed_intent` 参数）。修复后链路应能越过 planning 进入 execute。但 P0-1（checkpoint/resume）缺失意味着 HITL 中断后重启会丢状态——这是端到端长流程测试的潜在风险点，建议 P0-1 优先做。

---

## 附：架构图标注修正

本计划产出同时修正了 `ddg-technical-architecture.yaml` 中 9 处标注，让图反映代码真实状态（详见架构图更新）。修正后"规划中 ★"仅保留在标题层作分类提示，节点标注改为"已实现 缺X"形式。
