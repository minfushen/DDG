# Dify 适配层 API 参考

> Dify 专用 API 端点，所有操作通过 `/api/v1/dify/invoke` 统一入口，或直接使用辅助端点。

---

## 认证

所有 Dify 适配层 API 请求需要在 Header 中携带认证令牌：

```
Authorization: Bearer {DIFY_AUTH_TOKEN}
```

`DIFY_AUTH_TOKEN` 在 `backend/app/config/settings.py` 中配置，通过环境变量 `DIFY_AUTH_TOKEN` 设置。

---

## 1. POST /api/v1/dify/invoke — 统一入口

**所有 Dify 操作通过这一个端点完成**，通过 `action` 参数路由。

### 请求

```bash
curl -X POST http://localhost:8000/api/v1/dify/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-token" \
  -d '{
    "action": "create_due_diligence",
    "enterprise_name": "华为技术有限公司",
    "template_name": "full"
  }'
```

### 响应

```json
{
  "success": true,
  "data": {
    "task_id": "20240101120000abc123",
    "enterprise_name": "华为技术有限公司",
    "status": "running"
  },
  "message": "已创建尽调任务: 华为技术有限公司。任务ID: 20240101120000abc123",
  "next_action": "poll_status"
}
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | ✅ | 操作类型 |
| task_id | string | 条件 | 任务ID（get_status/get_report/get_interrupts/resume_interrupt 时需要） |
| enterprise_name | string | 条件 | 企业名称（create_due_diligence 时需要） |
| template_name | string | 否 | 尽调模板，默认 "full" |
| tool_name | string | 条件 | 工具名称（query_tool 时需要） |
| query | string | 条件 | 查询关键词（query_tool/simple_qa 时需要） |
| category | string | 否 | 查询类别，默认 "enterprise" |
| inputs | object | 否 | 用户输入（resume_interrupt 时需要） |
| interrupt_id | string | 条件 | 中断ID（resume_interrupt 时需要） |
| action_choice | string | 条件 | 用户选择的动作（resume_interrupt 时需要） |
| max_results | int | 否 | 返回结果数量，默认 8 |

### action 列表

| action | 用途 | 必填参数 |
|--------|------|----------|
| `create_due_diligence` | 创建深度尽调任务 | `enterprise_name` |
| `get_status` | 查询任务状态 | `task_id` |
| `get_report` | 获取任务报告 | `task_id` |
| `get_interrupts` | 查询任务中断 | `task_id` |
| `resume_interrupt` | 恢复中断任务 | `task_id`, `interrupt_id`, `action_choice` |
| `query_tool` | 直接调用工具 | `tool_name`, `query` |
| `simple_qa` | 简单问答 | `query` |

---

## 2. GET /api/v1/dify/status/{task_id}

**简化版状态查询**，供 Dify 轮询使用。

### 请求

```bash
curl http://localhost:8000/api/v1/dify/status/20240101120000abc123 \
  -H "Authorization: Bearer sk-your-token"
```

### 响应

```json
{
  "task_id": "20240101120000abc123",
  "status": "running",
  "agent_state": "researching",
  "progress": "3/10",
  "next_expected": "正在执行深度研究，请等待",
  "has_interrupt": false,
  "interrupt_type": null,
  "interrupt_title": null,
  "report_ready": false,
  "error": null
}
```

### 状态说明

| status | agent_state | 含义 | Dify 下一步 |
|--------|-------------|------|-------------|
| `running` | `researching` / `analyzing` / `reporting` | 任务执行中 | 继续轮询 |
| `completed` | `completed` | 任务完成 | 获取报告 |
| `waiting_human` | `waiting_human` | HITL 中断 | 获取中断信息，询问用户 |
| `failed` | `failed` | 任务失败 | 错误处理 |

---

## 3. GET /api/v1/dify/report/{task_id}

**获取任务报告（简化版）**，返回结构化数据供 Dify 展示。

### 请求

```bash
curl http://localhost:8000/api/v1/dify/report/20240101120000abc123 \
  -H "Authorization: Bearer sk-your-token"
```

### 响应

```json
{
  "task_id": "20240101120000abc123",
  "enterprise_name": "华为技术有限公司",
  "report_status": "completed",
  "executive_summary": "华为技术有限公司是全球领先的信息与通信技术（ICT）解决方案供应商...",
  "sections": [
    {
      "title": "三、财务状况与偿债能力",
      "subsections": [
        {
          "title": "3.1 收入与利润分析",
          "table": {...},
          "analysis": [...],
          "risk提示": "..."
        }
      ]
    }
  ],
  "key_metrics": {
    "revenue": {...},
    "debt_ratio": {...}
  },
  "risk_level": "中低风险",
  "risk_score": 35,
  "diagnostics": [...],
  "evidence_summary": [...],
  "data_gaps": [...],
  "report_url": "/api/v1/tasks/20240101120000abc123/report"
}
```

---

## 4. GET /api/v1/dify/interrupts/{task_id}

**查询任务中断信息**。

### 请求

```bash
curl http://localhost:8000/api/v1/dify/interrupts/20240101120000abc123 \
  -H "Authorization: Bearer sk-your-token"
```

### 响应

```json
{
  "task_id": "20240101120000abc123",
  "has_interrupt": true,
  "interrupts": [
    {
      "id": "int_001",
      "type": "upload_material",
      "title": "上传近三年财务报表",
      "message": "完整尽调需要补充近三年财务报表...",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "active": {
    "id": "int_001",
    "type": "upload_material",
    "title": "上传近三年财务报表",
    "message": "完整尽调需要补充近三年财务报表...",
    "options": [
      {"action": "upload_and_resume", "label": "上传并继续"},
      {"action": "continue_public_pre_dd", "label": "先按公开资料预尽调"}
    ]
  }
}
```

---

## 5. POST /api/v1/dify/interrupts/{task_id}/resume

**恢复中断任务**。

### 请求

```bash
curl -X POST "http://localhost:8000/api/v1/dify/interrupts/20240101120000abc123/resume?interrupt_id=int_001&action=continue_public_pre_dd" \
  -H "Authorization: Bearer sk-your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {"comment": "先按公开资料做预尽调"}
  }'
```

### 响应

```json
{
  "success": true,
  "data": {
    "task_id": "20240101120000abc123",
    "status": "resumed"
  },
  "message": "任务已恢复",
  "next_action": "poll_status"
}
```

---

## 6. POST /api/v1/dify/tools/{tool_name}

**直接调用工具**，不走尽调引擎。

### 支持的工具

| tool_name | 用途 | 请求参数 |
|-----------|------|----------|
| `searxng` | 网页搜索 | `query`, `max_results` |
| `business` | 工商查询 | `query` (企业名称) |
| `legal` | 法律查询 | `query` (企业名称) |
| `financial` | 财务分析 | `query` (企业名称) |
| `industry` | 行业分析 | `query` (行业名称) |

### 请求示例

```bash
curl -X POST http://localhost:8000/api/v1/dify/tools/searxng \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-your-token" \
  -d '{
    "query": "华为技术有限公司 年报 2024",
    "max_results": 5
  }'
```

### 响应示例

```json
{
  "success": true,
  "tool_name": "searxng",
  "data": {
    "results": [
      {
        "title": "华为2024年年度报告",
        "url": "https://www.huawei.com/...",
        "summary": "华为2024年实现销售收入..."
      }
    ],
    "total_estimated_matches": 42
  },
  "error": null
}
```

---

## 错误码

| HTTP 状态码 | 错误类型 | 说明 | 处理建议 |
|-------------|----------|------|----------|
| 400 | 请求参数错误 | action 或必要参数缺失 | 检查请求参数 |
| 401 | 认证失败 | Authorization 头缺失或无效 | 检查 DIFY_AUTH_TOKEN |
| 404 | 任务不存在 | task_id 未找到 | 确认 task_id 正确 |
| 500 | 服务器内部错误 | 后端异常 | 查看后端日志 |
| 502 | 工具调用失败 | 外部工具未返回结果 | 检查工具服务状态 |

---

## Dify HTTP 节点配置示例

### 创建任务节点

```
Method: POST
URL: http://localhost:8000/api/v1/dify/invoke
Headers:
  Content-Type: application/json
  Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}
Body (JSON):
  {
    "action": "create_due_diligence",
    "enterprise_name": "{{#start.enterprise_name#}}",
    "template_name": "full"
  }
Timeout: 30
```

### 轮询状态节点

```
Method: GET
URL: http://localhost:8000/api/v1/dify/status/{{store_task_id.task_id}}
Headers:
  Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}
Timeout: 10
```

### 获取报告节点

```
Method: GET
URL: http://localhost:8000/api/v1/dify/report/{{store_task_id.task_id}}
Headers:
  Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}
Timeout: 30
```
