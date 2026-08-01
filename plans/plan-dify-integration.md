# Dify 集成改造计划

> 目标：将 Dify 作为"轻量入口和问答增强层"，ddg-agent 核心引擎作为"深度研究 + 证据审计 + 质量门"暴露为工具/API，实现解耦拆分和统一编排。

---

## 一、现有架构分析

### 1.1 当前分层

```
┌─────────────────────────────────────────────┐
│  前端 (React + Vite)                           │  ← 自定义开发，需要维护
│  - 任务创建、SSE流、报告展示、HITL交互         │
├─────────────────────────────────────────────┤
│  API 层 (FastAPI)                              │
│  - /api/v1/tasks (任务创建/流式/恢复)          │
│  - /api/v1/tools (工具搜索/工商/法律)          │
│  - /api/v1/upload (财报上传)                   │
│  - /api/v1/report-quality (报告质量评估)       │
├─────────────────────────────────────────────┤
│  核心引擎 (LangGraph + 研究引擎)                │
│  - intent_extractor → 意图解析                │
│  - planner → 研究计划生成                      │
│  - engine/graph_engine → 执行引擎              │
│  - sub_agents (financial/business/legal/industry)│
│  - report_assembler → 报告组装                 │
│  - report_quality_gate → 质量门               │
│  - hitl → 人类在环                            │
│  - evidence → 证据审计链                        │
│  - cache_store → 缓存层                       │
│  - memory → 记忆系统（新）                     │
├─────────────────────────────────────────────┤
│  工具层                                        │
│  - 搜索 (SearxNG/Google)                       │
│  - 工商数据 (Tianyancha)                      │
│  - 法律数据 (Yuandian Law)                    │
│  - 财务数据 (iFinD/Yahoo Finance)             │
│  - 股票数据 (Kimi Finance)                     │
│  - MCP 工具                                    │
└─────────────────────────────────────────────┘
```

### 1.2 关键 API 端点

| 端点 | 方法 | 用途 | Dify 调用方式 |
|------|------|------|--------------|
| `/api/v1/tasks` | POST | 创建尽调任务 | HTTP 工具节点 |
| `/api/v1/tasks/{id}/stream` | GET | SSE 流式状态 | HTTP 流式节点 |
| `/api/v1/tasks/{id}` | GET | 任务状态 | HTTP 工具节点 |
| `/api/v1/tasks/{id}/resume` | POST | 恢复任务 | HTTP 工具节点 |
| `/api/v1/tasks/{id}/interrupts` | GET | 中断查询 | HTTP 工具节点 |
| `/api/v1/tasks/{id}/interrupts/{id}/resume` | POST | 中断恢复 | HTTP 工具节点 |
| `/api/v1/tasks/{id}/report` | GET | 获取报告 | HTTP 工具节点 |
| `/api/v1/tools/search` | POST | 通用搜索 | HTTP 工具节点 |
| `/api/v1/tools/business` | POST | 工商查询 | HTTP 工具节点 |
| `/api/v1/tools/legal` | POST | 法律查询 | HTTP 工具节点 |
| `/api/v1/upload/financial` | POST | 财报上传 | HTTP 工具节点 |
| `/api/v1/report-quality/evaluate` | POST | 质量评估 | HTTP 工具节点 |

---

## 二、目标架构设计

### 2.1 设计原则

1. **Dify 不替代核心引擎**：Dify 只负责"入口 + 编排 + 问答增强"，深度尽调仍由 ddg-agent 核心引擎执行。
2. **证据审计不可丢**：Dify 不存储证据链，证据审计仍由 ddg-agent 核心引擎维护。
3. **HITL 保持独立**：长周期任务的状态恢复和 HITL 仍由 ddg-agent 核心引擎管理，Dify 通过 API 查询和恢复。
4. **数据安全可控**：敏感数据（财报、法诉）通过 ddg-agent 核心引擎处理，不经过 Dify 的 LLM 服务。
5. **避免 vendor lock-in**：Dify 工作流只编排 API 调用，复杂逻辑保留在 ddg-agent 代码中。

### 2.2 目标架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Dify 应用层                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Dify Chatflow / Workflow                                      │   │
│  │  - 用户意图识别（简单问答 vs 深度尽调）                         │   │
│  │  - 简单问答：直接 LLM + 知识库检索                             │   │
│  │  - 深度尽调：调用 ddg-agent API 编排                          │   │
│  │  - 报告展示：调用 ddg-agent /report 获取渲染                   │   │
│  │  - HITL 交互：查询 ddg-agent /interrupts + resume              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  Dify 知识库：行业知识、FAQ、术语库                                  │
│  Dify 变量：task_id, enterprise_name, interrupt_state              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP API
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ddg-agent API 网关层 (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  新增：Dify 适配层                                             │   │
│  │  - /api/v1/dify/invoke          ← Dify 专用入口              │   │
│  │  - /api/v1/dify/status/{task_id} ← 任务状态查询              │   │
│  │  - /api/v1/dify/report/{task_id} ← 报告获取（简化版）         │   │
│  │  - /api/v1/dify/interrupts/{task_id} ← HITL 交互              │   │
│  │  - /api/v1/dify/tools/{tool_name} ← 工具直接调用              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  保留：原有 API 端点（供前端/其他客户端使用）                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ 内部调用
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  ddg-agent 核心引擎（保持独立）                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  研究引擎 (LangGraph)                                         │   │
│  │  - intent_extractor → planner → engine → report_assembler   │   │
│  │  - sub_agents (financial/business/legal/industry)           │   │
│  │  - report_quality_gate → HITL → evidence_audit              │   │
│  │  - cache_store + memory (新)                                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  工具服务层                                                   │   │
│  │  - search_service: 搜索工具                                    │   │
│  │  - business_service: 工商查询                                │   │
│  │  - legal_service: 法律查询                                   │   │
│  │  - financial_service: 财务分析（含财报上传）                   │   │
│  │  - industry_service: 行业分析                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  数据存储层                                                   │   │
│  │  - task_store (SQLite) → 任务状态                              │   │
│  │  - cache_store (SQLite) → 工具/LLM缓存                         │   │
│  │  - memory_store (SQLite+FTS5) → 记忆上下文                   │   │
│  │  - evidence_store → 证据链                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、阶段分解

### Stage 1: Dify 适配层（后端）

**目标文件**：
- `backend/app/api/dify_adapter.py` — 新增：Dify 专用 API 端点
- `backend/app/api/dify_tools.py` — 新增：工具直接调用端点
- `backend/app/main.py` — 编辑：注册新路由

**新增端点**：

```python
# /api/v1/dify/invoke — Dify 主入口
POST /api/v1/dify/invoke
Body: {"action": "create_due_diligence", "enterprise_name": "xxx", "template_name": "full"}
Response: {"task_id": "xxx", "status": "running", "next_action": "stream_status"}

POST /api/v1/dify/invoke
Body: {"action": "query_tool", "tool_name": "searxng", "query": "xxx", "category": "enterprise"}
Response: {"results": [...], "cache_hit": true}

POST /api/v1/dify/invoke
Body: {"action": "get_report", "task_id": "xxx"}
Response: {"report": {...}, "sections": [...], "narrative": {...}}

POST /api/v1/dify/invoke
Body: {"action": "get_interrupts", "task_id": "xxx"}
Response: {"interrupts": [...], "active": {...}}

POST /api/v1/dify/invoke
Body: {"action": "resume_interrupt", "task_id": "xxx", "interrupt_id": "xxx", "inputs": {...}}
Response: {"status": "resumed", "task_id": "xxx"}

# /api/v1/dify/status/{task_id} — 简化状态查询
GET /api/v1/dify/status/{task_id}
Response: {"task_id": "xxx", "status": "running", "agent_state": "researching", "progress": "3/10", "next_expected": "..."}

# /api/v1/dify/tools/{tool_name} — 工具直接调用
POST /api/v1/dify/tools/searxng
POST /api/v1/dify/tools/business
POST /api/v1/dify/tools/legal
POST /api/v1/dify/tools/financial
```

**设计要点**：
- Dify 只通过 `/api/v1/dify/invoke` 一个入口交互，内部路由到不同 action
- 返回 JSON，不含 SSE（Dify 的 HTTP 节点不支持 SSE 流）
- 状态查询走轮询（Dify 条件节点可循环查询）
- HITL 中断通过 `get_interrupts` + `resume_interrupt` 处理

### Stage 2: 工具服务化拆分

**目标文件**：
- `backend/app/services/search_service.py` — 新增：搜索工具服务
- `backend/app/services/business_service.py` — 新增：工商查询服务
- `backend/app/services/legal_service.py` — 新增：法律查询服务
- `backend/app/services/financial_service.py` — 新增：财务分析服务
- `backend/app/services/industry_service.py` — 新增：行业分析服务

**每个服务设计**：

```python
class SearchService:
    """搜索工具服务 — 可被 Dify 直接调用，也可被核心引擎内部调用。"""
    
    async def search(self, query: str, category: str = "enterprise", limit: int = 5) -> List[Dict]:
        ...
    
    async def search_with_cache(self, query: str, category: str = "enterprise", ttl: int = 3600) -> Dict:
        """带缓存的搜索，返回标准格式。"""
        ...

class FinancialService:
    """财务分析服务 — 支持财报上传和财务分析。"""
    
    async def analyze(self, enterprise_name: str, financial_data: Optional[Dict] = None) -> Dict:
        """财务分析入口，支持自动抓取和手动上传。"""
        ...
    
    async def upload_and_analyze(self, task_id: str, files: List[UploadFile]) -> Dict:
        """财报上传并分析。"""
        ...
```

### Stage 3: Dify 工作流设计（JSON 配置）

**目标文件**：
- `integrations/dify/workflows/due_diligence_chatflow.json` — Dify Chatflow 配置
- `integrations/dify/workflows/simple_qa_chatflow.json` — 简单问答 Chatflow 配置

**Chatflow 节点设计**：

```
[开始] → [意图识别 LLM] → [条件分支]
                              │
                    ┌────────┴────────┐
                    │                 │
                [简单问答]        [深度尽调]
                    │                 │
              [知识库检索]      [创建任务] → [轮询状态]
                    │                 │        ↓
              [LLM 回答]        [检查中断] ← [循环]
                    │                 │
                    └────────┬────────┘
                             │
                        [结束/输出]
```

**深度尽调 Chatflow 详细设计**：

1. **开始节点**：接收用户输入（企业名称 + 意图）
2. **意图识别 LLM**：判断是简单问答还是深度尽调
3. **条件分支**：
   - 简单问答 → 知识库检索 → LLM 生成回答 → 结束
   - 深度尽调 → 创建任务（调用 `/api/v1/dify/invoke` action=create_due_diligence）
4. **轮询状态**：循环调用 `/api/v1/dify/status/{task_id}`，直到 completed / waiting_human / failed
5. **检查中断**：
   - 如果 waiting_human → 调用 `/api/v1/dify/invoke` action=get_interrupts → 展示给用户 → 用户输入 → 调用 action=resume_interrupt
   - 如果 completed → 获取报告 → 结束
   - 如果 failed → 错误处理 → 结束
6. **报告展示**：调用 `/api/v1/dify/invoke` action=get_report，将报告内容渲染给用户

### Stage 4: 前端替换（Dify Embed）

**目标文件**：
- `integrations/dify/embed/index.html` — Dify 嵌入页面
- `integrations/dify/embed/README.md` — 部署说明

**方案**：
- 使用 Dify 的 Chatbot Embed 脚本，嵌入到现有域名
- 或直接用 Dify 的 Web App 作为入口
- 现有 React 前端可选择性保留（作为管理员后台/报告详情页）

### Stage 5: 文档和配置

**目标文件**：
- `docs/integration/dify/README.md` — 集成总览
- `docs/integration/dify/api-reference.md` — Dify 适配 API 参考
- `docs/integration/dify/chatflow-setup.md` — Chatflow 配置指南
- `docs/integration/dify/security.md` — 安全/数据合规指南
- `backend/app/config/settings.py` — 添加 Dify 配置项

---

## 四、文件变更清单

| 文件 | 动作 | 说明 |
|------|------|------|
| `backend/app/api/dify_adapter.py` | 新增 | Dify 主入口 API |
| `backend/app/api/dify_tools.py` | 新增 | 工具直接调用 API |
| `backend/app/services/search_service.py` | 新增 | 搜索服务 |
| `backend/app/services/business_service.py` | 新增 | 工商服务 |
| `backend/app/services/legal_service.py` | 新增 | 法律服务 |
| `backend/app/services/financial_service.py` | 新增 | 财务服务 |
| `backend/app/services/industry_service.py` | 新增 | 行业服务 |
| `backend/app/services/__init__.py` | 新增 | 服务导出 |
| `backend/app/main.py` | 编辑 | 注册新路由 |
| `backend/app/config/settings.py` | 编辑 | 添加 Dify 配置 |
| `integrations/dify/workflows/due_diligence_chatflow.json` | 新增 | 深度尽调 Chatflow |
| `integrations/dify/workflows/simple_qa_chatflow.json` | 新增 | 简单问答 Chatflow |
| `integrations/dify/embed/index.html` | 新增 | Dify 嵌入页面 |
| `docs/integration/dify/README.md` | 新增 | 集成文档 |
| `docs/integration/dify/api-reference.md` | 新增 | API 参考 |
| `docs/integration/dify/chatflow-setup.md` | 新增 | Chatflow 配置指南 |
| `docs/integration/dify/security.md` | 新增 | 安全指南 |

---

## 五、Dify 适配层详细设计

### 5.1 /api/v1/dify/invoke — 统一入口

```python
class DifyInvokeRequest(BaseModel):
    action: str  # create_due_diligence | query_tool | get_report | get_interrupts | resume_interrupt
    task_id: Optional[str] = None
    enterprise_name: Optional[str] = None
    template_name: Optional[str] = "full"
    tool_name: Optional[str] = None
    query: Optional[str] = None
    category: Optional[str] = "enterprise"
    inputs: Optional[Dict[str, Any]] = None
    files: Optional[List[str]] = None

class DifyInvokeResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    message: Optional[str] = None
    next_action: Optional[str] = None  # 提示 Dify 下一步该做什么
```

### 5.2 /api/v1/dify/status/{task_id} — 轮询状态

```python
class DifyStatusResponse(BaseModel):
    task_id: str
    status: str  # running | completed | waiting_human | failed
    agent_state: str
    progress: str  # 如 "3/10" 或 " researching → financial_analysis"
    next_expected: str  # 人类可读的下一步预期
    has_interrupt: bool
    interrupt_type: Optional[str] = None
    interrupt_title: Optional[str] = None
    report_ready: bool
    error: Optional[str] = None
```

### 5.3 /api/v1/dify/report/{task_id} — 获取报告（简化版）

```python
class DifyReportResponse(BaseModel):
    task_id: str
    enterprise_name: str
    report_status: str
    executive_summary: str  # 执行摘要
    sections: List[Dict]  # 简化后的章节
    key_metrics: Dict[str, Any]
    risk_level: str
    risk_score: int
    diagnostics: List[Dict]
    evidence_summary: List[str]
    data_gaps: List[str]
    report_url: Optional[str] = None  # 可访问的完整报告链接
```

### 5.4 关键设计：next_action 提示

为了让 Dify 的 Chatflow 能够正确编排，后端 API 返回 `next_action` 字段，提示 Dify 下一步该调用什么：

```python
{
    "success": true,
    "data": {"task_id": "20240101120000abc123", "status": "running"},
    "message": "任务已创建，正在执行深度研究",
    "next_action": "poll_status"  # 提示 Dify 轮询状态
}
```

```python
{
    "success": true,
    "data": {
        "task_id": "20240101120000abc123",
        "status": "waiting_human",
        "interrupt_type": "upload_material",
        "interrupt_title": "上传近三年财务报表"
    },
    "message": "任务中断，需要用户上传财报",
    "next_action": "ask_human"  # 提示 Dify 向用户询问
}
```

```python
{
    "success": true,
    "data": {"task_id": "20240101120000abc123", "status": "completed"},
    "message": "任务已完成",
    "next_action": "show_report"  # 提示 Dify 展示报告
}
```

---

## 六、安全与数据合规

1. **API 认证**：Dify 调用 ddg-agent API 时，通过 `Authorization: Bearer {DDG_API_KEY}` 认证
2. **敏感数据隔离**：财报、法诉数据不经过 Dify 的 LLM，只在 ddg-agent 核心引擎处理
3. **数据出境**：Dify 的 LLM 服务（如 OpenAI）不接触敏感数据，只处理简单问答和编排逻辑
4. **审计日志**：所有 Dify 调用记录到 ddg-agent 的日志系统
5. **任务隔离**：每个任务有独立的 task_id，Dify 只能查询自己创建的任务

---

## 七、依赖关系

```
Stage 1 (Dify 适配层) → Stage 2 (工具服务化) → Stage 3 (Chatflow 配置) → Stage 4 (前端替换) → Stage 5 (文档)
```

Stage 1 和 Stage 2 可以并行开发。
Stage 3 依赖 Stage 1 + 2。
Stage 4 和 Stage 5 可以并行。

---

## 八、验收标准

1. Dify 可以通过 `/api/v1/dify/invoke` 创建尽调任务并获取 task_id
2. Dify 可以通过 `/api/v1/dify/status/{task_id}` 轮询任务状态
3. Dify 可以处理 HITL 中断（查询 + 恢复）
4. Dify 可以获取简化版报告并展示给用户
5. 工具可以直接通过 `/api/v1/dify/tools/{tool_name}` 调用
6. 现有前端和 API 仍然正常工作（向后兼容）
7. 敏感数据不经过 Dify 的 LLM 服务
8. 文档完整，包含 Chatflow 配置指南和 API 参考

---

## 九、风险提醒

1. **证据审计不可丢**：Dify 工作流不存储证据链，证据审计仍由 ddg-agent 核心引擎维护
2. **HITL 状态恢复**：长周期任务（数小时/数天）的状态恢复由 ddg-agent 核心引擎管理，Dify 通过 API 查询和恢复
3. **SSE 不支持**：Dify 的 HTTP 节点不支持 SSE 流，状态更新通过轮询实现
4. **vendor lock-in**：Dify 工作流只编排 API 调用，复杂逻辑保留在 ddg-agent 代码中，便于迁移
