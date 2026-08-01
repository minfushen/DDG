# DDG Agent L1 私有交付实施计划

> 依据：`docs/product/PRD-V1.0.0-DDG-Agent-企业化改造-L1私有交付.html`  
> 对库现状：`backend/` 与 `frontend/`（截至 2026-07-10）  
> 关联文档：`docs/product/20-agent-capability-layer-v1-roadmap.md`

---

## 1. 背景与目标

PRD V1.0.0 定义了面向银行对公信贷的 L1 单租户私有化交付目标：单笔尽调 ≤6 小时、报告自动化率 ≥80%、8 章结构化授信报告、可审计证据链、JWT/PostgreSQL/可观测等企业级能力。

当前代码已完成 DeepResearch 引擎核心闭环、四专项 Agent、Evidence Store、HITL 中断、报告质量门、前端 3 页演示。但企业级底座（JWT、PostgreSQL、限流、可观测）、四阶段财报 PDF 管道、风险问答、批量定时任务等仍未落地。

本计划按「先稳核心 → 再补企业级 → 再做深度研究增强 → 最后封装交付」四阶段推进，尽量复用现有代码，避免重写。

---

## 1.5 重点修正：上市公司财务数据获取路径

DDG Agent 的核心产品亮点之一是**对非结构化文档（年报 PDF）的布局分析 + 内容解析 + RAG 检索**。因此，上市公司财务数据获取路径必须从当前「结构化接口（东方财富/AKShare）为主、PDF 年报为辅」切换为：

```text
上市公司识别
    ↓
CNINFO 年报公告检索 → 下载近 3 年年报 PDF
    ↓
四阶段 PDF 解析管道（MinerU → MiniCPM-V → 23 条勾稽 → qwen3.7 视觉兜底）
    ↓
结构化三大表（与 Excel 上传同 schema）
    ↓
Rebecca 规则引擎
    ↓
报告 + Evidence（source_url 指向巨潮年报 PDF）
```

东方财富 / AKShare 降为**交叉校验源**：
- 当年报解析失败或关键字段缺失时，用结构化接口补字段；
- 当年报解析成功时，用结构化接口做差异校验，差异过大则标记人工复核。

这一切换直接影响 Phase 1 的任务范围和优先级，具体见下文章节。

现有参考文档：
- `docs/architecture/listed-company-financial-data-integration-design.md`
- `docs/architecture/21-document-intelligence-and-rag-design.md`
- `docs/guides/annual_report_parsing_lessons.md`

---

## 2. PRD 需求 × 代码现状对照表

| # | 需求 | 状态 | 关键缺口 | 关键文件 |
|---|------|------|----------|----------|
| 1 | 尽调任务全生命周期 + 8 态状态机 + SSE | 部分 | 状态是临时字符串，未显式建模为 `gathering/analyzing/report_ready/under_review/approved/rejected/archived` | `backend/app/api/tasks.py` |
| 2 | DeepResearch 引擎 | 部分 | 缺 native checkpoint/resume、递归树研究、章节级 Reviewer/Reviser | `backend/app/agents/research_engine/` |
| 3 | 财务分析能力 | 部分 | 当前上市公司走东方财富/AKShare 结构化接口；需切换为 **CNINFO 年报 PDF 四阶段解析** 为主数据源，结构化接口降为交叉校验 | `backend/app/agents/sub_agents/financial_agent.py`、`backend/app/agents/tools/cninfo_announcement_tool.py` |
| 4 | 行业分析能力 | 部分 | Chroma 向量 + 关键词兜底已做；缺 BM25 + RRF + Rerank | `backend/app/rag/knowledge_retrieval_service.py` |
| 5 | 工商/司法分析 | 部分 | 元典 MCP/Tavily 已接；business agent 仍调用废弃 stub，legal agent 有死代码 | `backend/app/agents/sub_agents/business_agent.py`、`legal_agent.py` |
| 6 | 8 章结构化授信报告 | 高 | `synthesizer.py` 已输出 9 章；需银行级排版导出 | `backend/app/agents/research_engine/synthesizer.py` |
| 7 | 可审计证据链 | 高 | Evidence Store、Claim 绑定、source_url、可信度分级已完成 | `backend/app/agents/evidence/evidence_store.py`、`claim_builder.py` |
| 8 | HITL 人工在环 | 部分 | 4 类中断 + resume 已通；缺三处联动勾稽核验 UI | `backend/app/agents/hitl.py`、`frontend/src/pages/AgentWorkbench/ExecutionWorkspace.tsx` |
| 9 | 报告质量门 | 部分 | 9 维规则评测已做；缺 RAGAS 技术轨、递归回退、LLM-as-Judge 二评 | `backend/app/agents/research_engine/report_quality_*.py` |
| 10 | 财报上传与解析 | 部分 | 上传接口、Excel 解析已做；PDF 四阶段管道未闭环 | `backend/app/api/upload.py` |
| 11 | JWT 认证与权限 | 缺失 | 无 auth 路由、无登录页、无路由守卫 | — |
| 12 | 任务持久化与恢复 | 缺失 | 当前 SQLite 快照；无 PostgreSQL + Alembic | `backend/app/api/task_store.py` |
| 13 | API 限流 | 缺失 | 无 slowapi | — |
| 14 | 全链路可观测 | 缺失 | 只有 LangSmith env；无 Langfuse/Prometheus/Grafana/结构化日志 | `backend/app/config/settings.py` |
| 15 | 记忆双轨 | 部分 | SQLite+FTS5 已做；pgvector 可选路径未实现 | `backend/app/memory/memory_store.py` |
| 16 | 批量尽调定时任务 | 缺失 | 无 APScheduler | — |
| 17 | 前端登录鉴权与 API 分层 | 缺失 | 无登录页、auth store、token 拦截器 | `frontend/src/App.tsx`、`frontend/src/services/agentApi.ts` |
| 18 | 风险问答（AG-UI） | 缺失 | 无该功能 | — |

---

## 3. 实施阶段

### Phase 1：核心闭环稳定化（2–3 周）

目标：让现有代码可稳定演示、可测试，堵住明显的死代码和导出缺口，为后续企业级改造奠基。

| 任务 | 文件 | 说明 | 状态 |
|------|------|------|------|
| 1.1 清理司法 Agent 死代码 | `backend/app/agents/sub_agents/legal_agent.py` | 删除未调用的 `_build_legacy_mock_report`；修复 `_build_unavailable_legal_report` 中第二个 unreachable `return` | 已完成 |
| 1.2 清理工商 Agent 废弃 fallback | `backend/app/agents/sub_agents/business_agent.py` | 移除对 `authoritative_business_tool` 的调用，直接以 Tavily/Yuandian 结果生成证据 | 已完成 |
| 1.3 显式任务状态机 | `backend/app/agents/state.py`、`backend/app/api/tasks.py` | 新增 `TaskLifecycleState` 枚举：`gathering`、`analyzing`、`report_ready`、`under_review`、`approved`、`rejected`、`archived`；旧 `agent_state` 做映射兼容 | 已完成 |
| 1.4 关闭质量门回退循环 | `backend/app/agents/research_engine/report_quality_gate.py`、`graph_engine.py` | 质量分不达标时自动生成 gaps 并进入 `plan_followups` → `execute_followups`，最多 2 轮 | 已完成 |
| 1.5 增加 Markdown 导出 | `backend/app/engines/rebecca/report_generator.py`、`backend/app/api/tasks.py` | 支持 `format=md` | 已完成 |
| 1.6 前端导出按钮接线 | `frontend/src/pages/Report/index.tsx`、`frontend/src/services/agentApi.ts` | 点击「导出 PDF/DOCX/Markdown」实际调用 `GET /tasks/{id}/report?format=...` | 已完成 |
| 1.7 移除 crawl4ai 悬空引用 | `backend/app/agents/research_engine/public_search_pipeline.py` | 实现 `crawl4ai_reader_tool.py` 或删除引用并加降级提示 | 已完成（已降级为可选 ImportError） |
| 1.8 上市公司年报 PDF 主链路切换 | `backend/app/agents/sub_agents/financial_agent.py` | 改 `run_financial_agent`：识别上市公司后优先下载 CNINFO 年报 PDF，四阶段解析出三大表，再输入 Rebecca；东方财富/AKShare 降为交叉校验 | 已完成 |
| 1.9 四阶段 PDF 解析管道串接 | 新增 `backend/app/engines/rebecca/parsers/financial_pdf_pipeline.py` | 封装 MinerU → MiniCPM-V → 23 条会计恒等式勾稽 → qwen3.7 视觉兜底；输出与 Excel 上传同 schema 的标准化三大表 | 已完成 |
| 1.10 年报 PDF 证据链与 RAG 入库 | `backend/app/agents/tools/cninfo_announcement_tool.py`、`backend/app/rag/pdf_knowledge_ingestion.py` | 下载年报 PDF 同时生成高可信 evidence（标题、披露日期、PDF URL、页码）；并将年报全文切片入库，支持后续风险问答与正文级引用 | 已完成 |

**验收**：
- `pytest backend/tests/test_report_quality_*.py` 通过
- 端到端：创建任务 → 计划确认 → 生成报告 → 导出 PDF/DOCX/MD
- 工商/司法 Agent 不再出现空 source 或死代码路径
- 上市公司（如三安光电/欣旺达）财务 Agent 的三大表来源为年报 PDF，evidence 绑定巨潮 PDF URL

---

### Phase 2：企业级底座（3–4 周）

目标：满足 L1 私有化对安全、持久化、可观测、限流的要求。

| 任务 | 文件 | 说明 |
|------|------|------|
| 2.1 JWT 认证后端 | 新增 `backend/app/api/auth.py`、`backend/app/models/user.py` | `POST /api/v1/auth/login`、`/refresh`、`/me`；`python-jose` + `passlib` |
| 2.2 认证依赖注入 | 新增 `backend/app/api/deps.py`，修改 `backend/app/api/tasks.py`、`upload.py`、`report_quality.py`、`dify_adapter.py` | 所有受保护路由加 `Depends(get_current_user)`；`user_id` 写入 task 记录 |
| 2.3 PostgreSQL + SQLAlchemy | 新增 `backend/app/db/`、`backend/app/models/task.py`、`backend/app/models/user.py` | 异步 `AsyncSession`；任务、用户、批量任务、审计日志表 |
| 2.4 Alembic 迁移 | 新增 `backend/alembic.ini`、`backend/alembic/versions/` | 初始 migration |
| 2.5 任务恢复 | `backend/app/main.py` | 启动时恢复 `agent_state` 为 `gathering/analyzing/report_ready/waiting_human` 的任务 |
| 2.6 API 限流 | 新增 `backend/app/middleware/rate_limit.py`，修改 `backend/app/main.py`、`requirements.txt` | `slowapi`：按路由 + IP 限流，超限时返回 429 |
| 2.7 Langfuse 追踪 | 新增 `backend/app/observability/langfuse_client.py` | 包装 LLM 调用和研究任务 span |
| 2.8 Prometheus 指标 | 新增 `backend/app/observability/metrics.py` | `/metrics` 暴露任务状态计数、LLM 延迟、工具成功率 |
| 2.9 结构化日志 | 新增 `backend/app/observability/logging.py` | JSON 日志带 `request_id`/`user_id`/`task_id` |
| 2.10 Grafana 看板 | 新增 `infra/grafana/dashboards/ddg-agent.json` | 导入任务生命周期、LLM 延迟、数据源健康度看板 |

**验收**：
- 未登录访问 `/api/v1/tasks` 返回 401
- `alembic upgrade head` 成功
- 服务重启后进行中任务可恢复
- `/metrics` 有输出；单 IP 超阈值返回 429

---

### Phase 3：深度研究与 RAG 增强（3–4 周）

目标：实现 PRD 级别的 DeepResearch 与行业 RAG 能力。

| 任务 | 文件 | 说明 |
|------|------|------|
| 3.1 LangGraph native checkpoint/resume | `backend/app/agents/research_engine/graph_engine.py`、`state.py` | 接入 `MemorySaver` 或 PostgreSQL checkpointer；用原生 `interrupt` 替代内存中断对象 |
| 3.2 Tool Manifest 主路由 | `backend/app/agents/tools/manifest.py`、`backend/app/agents/research_engine/tool_router.py` | Planner 输出 manifest tool_id；router 按 manifest 解析，不再硬编码 category |
| 3.3 章节级 Reviewer/Reviser | 新增 `backend/app/agents/research_engine/section_reviewer.py`、`section_reviser.py` | 每章按 9 维评分评审，低分则重写，最多 2 轮 |
| 3.4 递归深度研究 | 新增 `backend/app/agents/research_engine/tree_search.py` | 对关键 gaps 按 `breadth/depth`（depth≤2）分支并行探索 |
| 3.5 BM25 + RRF + Rerank | 新增 `backend/app/rag/bm25_index.py`、`backend/app/rag/reranker.py`；修改 `knowledge_retrieval_service.py` | 向量与 BM25 并行召回，RRF 融合，轻量 cross-encoder/rule rerank |
| 3.6 Publisher Agent 专业导出 | 新增 `backend/app/engines/rebecca/publisher_agent.py` | 银行授信风格 DOCX/PDF：封面、目录、章节样式、证据脚注 |
| 3.7 RAGAS 技术轨 | 新增 `backend/app/evaluation/ragas_eval.py` | 计算 ContextPrecision/Recall/Faithfulness/ResponseRelevancy |

**验收**：
- 10 家上市公司回归样例平均分 ≥75
- RAGAS Faithfulness ≥0.90，ContextRecall ≥0.75
- 中断后恢复状态正确
- DOCX 导出含封面与脚注

---

### Phase 4：封装与 P1 能力补齐（2–3 周）

目标：完成 P1 需求，形成一键 Docker Compose 私有化交付包。

| 任务 | 文件 | 说明 |
|------|------|------|
| 4.1 pgvector 可选记忆后端 | 新增 `backend/app/memory/pgvector_store.py` | `MemoryBackend` 抽象；`MEMORY_BACKEND=pgvector` 时切换 |
| 4.2 跨任务记忆注入 | `backend/app/agents/research_engine/planner.py`、各专项 Agent | 通过 `CapabilityContextBuilder` 注入用户偏好与公司历史 |
| 4.3 APScheduler 批量尽调 | 新增 `backend/app/jobs/batch_diligence.py` | 每日 02:00 读取 watchlist 表，批量创建任务并记录 `batch_jobs` |
| 4.4 前端登录与鉴权 | 新增 `frontend/src/pages/Login/Login.tsx`、`frontend/src/store/authStore.ts`；修改 `App.tsx`、`agentApi.ts` | 登录页、Zustand auth store、路由守卫、token 拦截器 |
| 4.5 风险问答 AG-UI | 新增 `backend/app/api/risk_qa.py`、`frontend/src/components/RiskChat/` | 基于报告 + evidence 流式回答，置信度 <70% 提示人工确认 |
| 4.6 四阶段财报 PDF 管道（非上市公司） | 新增 `backend/app/engines/rebecca/parsers/financial_pdf_pipeline.py` | 非上市 PDF 上传走 MinerU → MiniCPM-V → 23 条勾稽 → qwen3.7 视觉兜底；上市公司已走 CNINFO 年报链路，本管道为其兜底/复用实现 |
| 4.7 三处联动勾稽核验 UI | 新增 `frontend/src/pages/Reconciliation/Reconciliation.tsx` | 左 PDF 着色 + 右上核验队列 + 右下结构化报表 |
| 4.8 Docker Compose 私有化交付 | 新增 `docker-compose.yml`、`infra/postgres/`、`infra/grafana/` | 一键启动 backend/frontend/postgres/grafana/sequential-thinking |

**验收**：
- 登录后刷新保持认证；未认证访问跳转 `/login`
- 批量任务在 02:00 触发并写入日志
- 风险问答返回带引用答案，低置信有提示
- `docker compose up` 能完整启动并跑通一例尽调

---

## 4. 与现有 Roadmap 的关系

现有 `docs/product/20-agent-capability-layer-v1-roadmap.md` 提出：

```
M1 Skill-aware Planner → M2 Specialist Skill Injection → M3 MemoryService → M4 Enhanced RAG → LangGraph 迁移 → 容器化
```

本计划将其调整为 L1 交付导向：

```
Phase 1 核心稳定（含 M1/M2 收尾）
Phase 2 L1 企业级底座（新增：JWT/PostgreSQL/Alembic/限流/可观测）
Phase 3 深度研究与 RAG 增强（M4 + LangGraph checkpoint + Reviewer/Reviser + 递归研究）
Phase 4 封装与 P1 补齐（pgvector、批量任务、登录、风险问答、PDF 管道、Docker Compose）
```

建议更新 `20-agent-capability-layer-v1-roadmap.md`，在 M2 与 M4 之间插入 **M2.5 L1 Enterprise Hardening**。

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| JWT + PostgreSQL 改动触及所有 API 路由 | 高 | 先建 `deps.get_current_user`，逐路由迁移；开发环境保留 SQLite 回退 |
| LangGraph native interrupt 改变 HITL 契约 | 中 | Phase 3 实施，保持 REST resume 端点向后兼容 |
| MinerU/MiniCPM-V 在银行内网不可用 | 高 | 四阶段管道每阶段可独立降级；最终 fallback 为人工上传 Excel |
| pgvector 需 PostgreSQL extension | 低 | 默认 SQLite+FTS5，pgvector 为可选 |
| Rerank 模型部署成本 | 中 | 先用 rule-based rerank，cross-encoder 作为增强项 |
| Prompt 因 Skill/Memory/RAG 注入过长 | 中 | `CapabilityContextBuilder` 做相关性排序与上下文预算裁剪 |

---

## 6. 首周 Sprint 建议

为快速降低风险并建立节奏：

1. **清理 legal/business agent 死代码**，跑通一例完整尽调。
2. **接入报告导出按钮**（PDF/DOCX/MD），补齐前端最后一块可用性缺口。
3. **新增 JWT auth 骨架**（`auth.py`、`deps.py`、user model），用 feature flag 控制，不影响现有路由。
4. **设计 PostgreSQL `tasks`/`users` 表**，先在 `task_store.py` 中 dual-write，保留 SQLite 回退。
5. **修复 crawl4ai 悬空引用**（删除或实现）。
6. **CNINFO 年报 PDF 解析已跑通并接入主链路**：财务 Agent 对上市公司默认解析近 3 年年报 PDF，与东方财富/AKShare 做交叉校验，同步生成 evidence 并写入企业知识库。可继续用 `scripts/evaluate_annual_report_pipeline.py` 在真实样本上回归。

---

## 7. 关键文件清单

- `backend/app/api/tasks.py`
- `backend/app/api/auth.py`（新增）
- `backend/app/api/deps.py`（新增）
- `backend/app/agents/state.py`
- `backend/app/agents/research_engine/graph_engine.py`
- `backend/app/agents/research_engine/section_reviewer.py`（新增）
- `backend/app/agents/research_engine/section_reviser.py`（新增）
- `backend/app/agents/sub_agents/legal_agent.py`
- `backend/app/agents/sub_agents/business_agent.py`
- `backend/app/rag/knowledge_retrieval_service.py`
- `backend/app/engines/rebecca/report_generator.py`
- `backend/app/engines/rebecca/parsers/financial_pdf_pipeline.py`（新增）
- `backend/app/jobs/batch_diligence.py`（新增）
- `backend/app/db/`（新增）
- `backend/app/observability/`（新增）
- `frontend/src/pages/Login/Login.tsx`（新增）
- `frontend/src/store/authStore.ts`（新增）
- `frontend/src/pages/Report/index.tsx`
- `frontend/src/pages/Reconciliation/Reconciliation.tsx`（新增）
- `docker-compose.yml`（新增）
