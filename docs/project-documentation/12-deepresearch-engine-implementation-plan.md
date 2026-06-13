# 12 DeepResearch Engine 实施计划

## 实施原则

1. 不推翻现有四 Agent 链路。
2. 先做可运行的规则版 Research Engine，再接 Sequential Thinking MCP。
3. 先输出后端 JSON，再做前端研究过程展示。
4. 所有 Claim 必须绑定 Evidence。
5. 所有公开搜索结果都必须标记数据边界。

## 阶段 1：代码骨架和规则闭环

目标：新增 `research_engine` 包，实现默认研究计划、工具路由、Evidence 归集、Claim 和 Gap 输出。

新增文件：

```text
backend/app/agents/research_engine/__init__.py
backend/app/agents/research_engine/state.py
backend/app/agents/research_engine/planner.py
backend/app/agents/research_engine/tool_router.py
backend/app/agents/research_engine/claim_builder.py
backend/app/agents/research_engine/gap_reflector.py
backend/app/agents/research_engine/synthesizer.py
backend/app/agents/research_engine/engine.py
```

阶段 1 不新增 API，先通过函数测试：

```python
run_deep_research_due_diligence("士兰微")
```

## 阶段 2：接入 Sequential Thinking MCP

状态：已完成最小接入。

新增：

```text
backend/app/agents/research_engine/mcp_tools.py
```

能力：

- 使用 `langchain_mcp_adapters` 加载 Sequential Thinking MCP。
- MCP 可用时记录研究计划检查点和证据缺口检查点。
- MCP 不可用时回退规则 planner。
- 不把 Sequential Thinking MCP 当成规划 LLM；结构化任务、Claim 和 Gap 仍由项目内规则/LLM/RAG 节点生成。

配置项：

```text
SEQUENTIAL_THINKING_MCP_COMMAND=npx
SEQUENTIAL_THINKING_MCP_ARGS="-y @modelcontextprotocol/server-sequential-thinking"
ENABLE_SEQUENTIAL_THINKING=false
SEQUENTIAL_THINKING_MCP_TIMEOUT_SECONDS=20
```

已接入位置：

- `run_deep_research_due_diligence()` 启动时探测 MCP 可用性。
- 生成默认研究计划后执行 `sequential_plan_review()`。
- 每个任务完成证据采集和规则缺口识别后执行 `sequential_gap_review()`。
- MCP 不可用或调用失败时写入 timeline/errors，不中断主流程。

## 阶段 2.5：LLM Planner 节点

状态：准备实现。

目标：把当前规则默认计划升级为 Plan-Execute 架构中的 LLM Plan 节点。LLM Planner 负责根据企业、目标、部署约束和可用工具生成结构化 `ResearchTask[]`，规则计划仅作为 fallback。

新增文件：

```text
backend/app/agents/research_engine/prompts.py
backend/app/agents/research_engine/llm_planner.py
```

改造文件：

```text
backend/app/agents/research_engine/planner.py
backend/app/agents/research_engine/engine.py
backend/app/config/settings.py
backend/.env.example
```

配置项：

```text
ENABLE_LLM_RESEARCH_PLANNER=true
RESEARCH_PLANNER_TIMEOUT_SECONDS=30
RESEARCH_PLANNER_MAX_TASKS=8
```

执行策略：

1. `planner.py` 保留 `create_default_research_plan()`。
2. 新增 `create_research_plan()`：优先调用 LLM Planner，失败时回退默认规则计划。
3. `llm_planner.py` 负责 prompt 组装、LLM 调用、JSON 解析、任务校验和规范化。
4. `engine.py` 不再直接调用 `create_default_research_plan()`，改用 `create_research_plan()`。
5. Sequential Thinking MCP 继续作为计划检查点，不承担结构化任务生成。

验收标准：

- 未配置 LLM 时仍可跑通默认规则计划。
- 配置 LLM 时，timeline 能看到 `LLM Planner` 成功或降级状态。
- LLM 返回的任务必须包含 `question`、`purpose`、`category`、`required_evidence`、`tool_hints`。
- 若 LLM 返回无效 JSON 或空任务，必须自动 fallback。
- 首页创建任务不得等待 Planner 完成；Planner 只在后台执行阶段运行。

## 阶段 3：API 与前端展示

后端新增：

```text
POST /api/v1/research-tasks
GET /api/v1/research-tasks/{task_id}
GET /api/v1/research-tasks/{task_id}/events
```

前端展示：

- Research Plan。
- 当前任务。
- Evidence 列表。
- Claim-Evidence 表。
- Gap 清单。

## 阶段 4：与完整尽调报告融合

将 `full_due_diligence_report` 支持两种生成模式：

- `classic_agent_pipeline`
- `deepresearch_engine`

完整报告中新增：

- `research_claims`
- `research_gaps`
- `evidence_coverage`
- `source_reliability_summary`

## 阶段 5：生产化能力

- 任务状态持久化。
- 多租户隔离。
- LLM Gateway。
- Data Source Gateway。
- 工具调用成本统计。
- 私有化公网搜索开关。
- 权威工商/司法/行政处罚 API 接入。

## 当前要推进的代码范围

本轮只做阶段 1：

- 默认研究计划。
- 简单工具路由。
- 调用 Bocha/RAG/现有单 Agent 中的轻量工具。
- 输出 research_report。
- 编译验证。
