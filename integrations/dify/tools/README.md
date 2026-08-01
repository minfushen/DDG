# Dify 单步工具调用（概念验证）

本目录包含把 `ddg-agent` 的三个轻量工具暴露给 Dify 进行编排的配置文件。

> ⚠️ 这是 **POC 级别** 接入，仅用于验证 Dify 调用 ddg-agent 后端的能力。完整的 DeepResearch 引擎、证据链、HITL、质量门等核心能力仍保留在 ddg-agent 后端。

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `single_tool_workflow.yml` | Dify Workflow DSL，可直接导入 Dify Studio |
| `openapi_tools.json` | 三个工具端点的 OpenAPI  schema，可用于 Dify 自定义工具导入 |
| `README.md` | 本说明文档 |

---

## 前置条件

1. `ddg-agent` 后端已启动（默认 `http://localhost:8000`）。
2. 后端 `.env` 中已配置：
   - `BOCHA_API_KEY`（公开搜索）
   - `YUANDIAN_API_KEY`、`YUANDIAN_COMPANY_MCP_URL`、`YUANDIAN_CASE_MCP_URL`（工商/司法）
3. 若 Dify 以 Docker 运行，请将 YAML 中 `environment_variables.DDG_API_BASE` 的 `localhost` 替换为 `host.docker.internal` 或后端内网 IP。

---

## 后端变更

为支持 Dify 调用，已在后端新增以下文件并注册路由：

- `backend/app/api/tools.py`：三个无状态工具端点
- `backend/app/main.py`：注册 `tools.router`，前缀 `/api/v1`

新增端点：

| 端点 | 说明 | 请求体示例 |
|------|------|-----------|
| `POST /api/v1/tools/search` | Bocha 公开搜索 | `{"query": "华为 年报", "max_results": 5}` |
| `POST /api/v1/tools/business` | 元典企业工商+风险 | `{"enterprise_name": "华为技术有限公司"}` |
| `POST /api/v1/tools/legal` | 元典司法风险 | `{"enterprise_name": "华为技术有限公司", "top_k": 10}` |

---

## 使用方式一：导入 Workflow DSL（推荐）

1. 登录 Dify Studio。
2. 创建空白应用 → 选择 **Workflow**。
3. 点击右上角 **...** → **导入 DSL** → 选择 `single_tool_workflow.yml`。
4. 进入 **环境变量**，将 `DDG_API_BASE` 改为后端实际地址。
5. 在 LLM 路由节点中选择可用的模型（默认 `gpt-4o-mini`，可按需替换为已配置的 Qwen 等）。
6. 点击 **运行** 测试：输入查询内容并选择工具类型。

### Workflow 结构

```
开始（query + tool_type）
  → LLM 路由（自动识别工具）
  → 代码节点（构造 endpoint + payload）
  → HTTP 请求节点（调用 /api/v1/tools/*）
  → 代码节点（把 JSON 渲染为 Markdown）
  → 直接回复
```

---

## 使用方式二：导入自定义工具（Custom Tools）

如果你希望每个工具在 Dify 中表现为独立的 Tool 节点，可按以下步骤操作：

1. Dify Studio → **工具** → **创建自定义工具**。
2. 选择 **导入 OpenAPI schema**，上传 `openapi_tools.json`。
3. 配置 API 鉴权为 **无鉴权**（后端工具端点目前未要求鉴权；生产环境建议加 API Key）。
4. 创建新的 Workflow，拖入三个 Tool 节点，按需组合。

---

## 已知限制

1. **无状态调用**：每个端点只做一次工具调用，不维护任务状态，也不生成证据链。
2. **无 HITL**：不存在计划审批、材料上传、证据缺口确认等流程。
3. **无缓存/限流**：复用了底层工具的现有配置，但未经过 `tool_middleware` 的中间件层。
4. **网络连通性**：Dify Docker 容器必须能访问后端服务地址。
5. **模型依赖**：LLM 路由节点需要模型输出合法 JSON，建议使用 `temperature: 0.1` 并确保模型遵循指令。

---

## 下一步可扩展

- 把 `intent_extractor` 也暴露为 `/tools/intent`，让 Dify 复用项目内部的主体识别逻辑。
- 把 RAG 检索端点 `/tools/rag` 也暴露出来，让 Dify 可以查询内部授信知识库。
- 为工具端点增加 API Key 鉴权，确保生产环境安全。
- 把 Dify Workflow 作为 `ddg-agent` 完整尽调任务的**入口层**，后续通过 `/api/v1/tasks` 触发 DeepResearch 引擎。
