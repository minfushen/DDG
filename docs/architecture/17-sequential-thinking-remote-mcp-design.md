# 17 Sequential Thinking Remote MCP 设计文档

## 背景

当前 DeepResearch Engine 已经具备 LangGraph shell、LLM Planner、Evidence Store、二轮补证和报告合成能力，但 Sequential Thinking MCP 的接入仍偏轻量：它主要作为 `plan review` 和 `gap review` 检查点存在，没有真正体现研究智能体的“分步思考、动态扩展、自我修订”状态管理能力。

本轮改造目标是把 Sequential Thinking 从可选复核器升级为 DeepResearch plan 节点的研究思考状态机：先用 Sequential Thinking 记录和管理研究思考链，再由 LLM Planner 基于这些公开化的研究步骤生成结构化任务计划。

## 产品定位

Sequential Thinking 不用于展示模型私密思维链，也不直接替代 LLM 生成报告内容。它在产品中承担三类可展示、可审计的研究过程对象：

1. **研究启动思考**：确认尽调目标、主体边界、核心风险域和数据边界。
2. **研究计划扩展**：当初始研究问题不足时，允许增加思考步数和补充研究方向。
3. **研究修订记录**：当发现主体混淆、行业识别错误、证据不足时，记录对前序步骤的修正。

前端执行页可以展示这些摘要化步骤，例如“确认主体边界”“拆分财务/行业/司法证据需求”“修订行业子赛道判断”，但不展示模型内部不可审计的长链路推理。

## 目标架构

官方 Sequential Thinking MCP server 默认通过 stdio 工作，更适合本地 MCP Client 启动和接管进程。在私有化和多 Agent 协同场景下，需要一个可远程访问的 Streamable HTTP MCP wrapper。

```text
DDG-Agent Backend
  -> LangChain MCP Adapter
    -> Streamable HTTP MCP Wrapper
      -> sequentialthinking tool
        -> Official Sequential Thinking MCP Server via stdio
```

MVP 中 wrapper 以独立服务运行，默认监听：

```text
http://127.0.0.1:38001/mcp
```

后续私有化部署时可以放入 Docker Compose，与 backend、frontend、SearXNG、数据库和知识库服务一起交付。

## Wrapper 设计

服务目录：

```text
infra/sequential-thinking/
├── server.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

职责边界：

- 对外暴露 Streamable HTTP MCP endpoint。
- 对外工具名保持 `sequentialthinking`。
- 工具参数兼容官方 Sequential Thinking MCP：`thought`、`thoughtNumber`、`totalThoughts`、`nextThoughtNeeded`、`isRevision`、`revisesThought`、`branchFromThought`、`branchId`、`needsMoreThoughts`。
- 内部优先通过 stdio MCP client 调用官方 server。
- 如果官方 stdio server 不可用，MVP 可退化为本地状态记录器，返回同构 JSON，保证 DDG-Agent 主链路不阻塞。

MVP 不在每次请求时 `docker run` 官方 server。每次请求启动容器会导致延迟高、状态不可复用、并发难控。更稳妥的方式是 wrapper 长驻，后续再扩展为按 `session_id` 隔离不同任务的思考历史。

## DDG-Agent 配置

新增配置：

```text
ENABLE_SEQUENTIAL_THINKING=true
SEQUENTIAL_THINKING_TRANSPORT=streamable_http
SEQUENTIAL_THINKING_REMOTE_URL=http://127.0.0.1:38001/mcp
SEQUENTIAL_THINKING_MCP_TIMEOUT_SECONDS=20
```

保留本地 stdio 配置作为开发 fallback：

```text
SEQUENTIAL_THINKING_TRANSPORT=stdio
SEQUENTIAL_THINKING_MCP_COMMAND=npx
SEQUENTIAL_THINKING_MCP_ARGS="-y @modelcontextprotocol/server-sequential-thinking"
```

## DeepResearch Plan 节点改造

原流程：

```text
规则默认任务 -> LLM Planner 生成结构化计划 -> Sequential Thinking plan review
```

目标流程：

```text
规则默认任务
-> Sequential Thinking thought loop
-> LLM Planner 基于 thought loop 摘要生成结构化计划
-> 规则校验和 fallback
```

thought loop MVP 固定执行 3 步：

| 步骤 | 目的 | nextThoughtNeeded |
| --- | --- | --- |
| 1 | 确认尽调目标、主体边界、数据边界 | true |
| 2 | 拆分主体、财务、司法、行业、授信证据需求 | true |
| 3 | 形成计划生成提示，标记高风险缺口和人工确认点 | false |

当 LLM Planner 失败时，仍回退规则计划；当 Sequential Thinking 不可用时，仍使用 LLM Planner 或规则计划。失败信息写入 `timeline` 和 `state.sequential_thinking`，不阻塞创建任务。

## 数据结构

DeepResearch state 增加：

```json
{
  "sequential_thinking": {
    "enabled": true,
    "transport": "streamable_http",
    "tool_names": ["sequentialthinking"],
    "error": ""
  },
  "sequential_thought_loop": {
    "success": true,
    "steps": [
      {
        "thoughtNumber": 1,
        "totalThoughts": 3,
        "nextThoughtNeeded": true,
        "summary": "确认主体边界和数据边界",
        "raw": {}
      }
    ],
    "plan_context": "供 LLM Planner 使用的摘要化研究上下文"
  }
}
```

## 验收标准

1. 可本地启动 wrapper：`http://127.0.0.1:38001/mcp`。
2. 后端支持 `SEQUENTIAL_THINKING_TRANSPORT=streamable_http`。
3. DeepResearch plan 节点 timeline 中能看到“启动研究思考链”和“完成研究思考链”。
4. LLM Planner prompt 能收到 thought loop 摘要，而不是只基于默认任务生成计划。
5. Sequential Thinking 服务失败时，任务创建不阻塞，并显示清晰降级原因。

## 后续演进

- 增加 `session_id`，按 task/tenant 隔离思考历史。
- 把 gap review 和二轮补证也迁移到 thought loop，而不是单次检查点。
- 在前端执行页增加“研究思考链”折叠区，只展示摘要化步骤和修订记录。
- 私有化部署时把 wrapper 纳入统一 Docker Compose 和运维健康检查。
