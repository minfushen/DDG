# Dify 集成文档总览

> 将 Dify 作为"轻量入口和问答增强层"，ddg-agent 核心引擎作为"深度研究 + 证据审计 + 质量门"。

---

## 集成目标

| 层面 | Dify 负责 | ddg-agent 核心引擎负责 |
|------|-----------|------------------------|
| **用户入口** | 聊天界面、意图识别、简单问答 | 不直接暴露给用户 |
| **深度尽调** | 编排调用（创建任务→轮询状态→获取报告） | 执行完整研究、证据审计、质量门 |
| **工具调用** | 路由到工具节点 | 实际执行搜索、工商、法律、财务查询 |
| **HITL 交互** | 展示中断信息、收集用户输入 | 维护中断状态、恢复任务执行 |
| **数据存储** | 不存储敏感数据 | 任务快照、证据链、缓存、记忆 |
| **报告展示** | LLM 生成摘要、格式化输出 | 生成完整报告数据 |

---

## 架构图

```
用户输入 → Dify Chatflow → ddg-agent API 适配层 → 核心引擎 → 工具层 → 数据源
                ↓                  ↓
           知识库检索          证据审计链
           LLM 增强回答        任务状态管理
```

---

## 快速开始（3步启动）

### 步骤1：启动 ddg-agent 后端

```bash
cd /path/to/ddg-agent/backend
source venv/bin/activate
python3 run.py
```

后端默认监听 `http://localhost:8000`，包含 Dify 适配层 API。

### 步骤2：配置 Dify 环境变量

在 Dify 应用的「环境变量」中配置：

| 变量名 | 值 | 说明 |
|--------|------|------|
| `DDG_API_BASE_URL` | `http://localhost:8000` | ddg-agent 后端地址 |
| `DIFY_AUTH_TOKEN` | `sk-xxxx` | API 认证令牌（在 `.env` 中设置） |

### 步骤3：搭建 Chatflow

按照 [chatflow-setup.md](chatflow-setup.md) 的指南，在 Dify UI 中搭建尽调工作流。

---

## 目录结构

```
docs/dify-integration/
├── README.md              # 本文件（总览）
├── api-reference.md       # Dify 适配层 API 参考
├── chatflow-setup.md      # Chatflow 配置指南
└── security.md            # 安全与数据合规指南

dify-workflows/
├── due_diligence_chatflow.md  # 深度尽调 Chatflow 节点配置
└── simple_qa_chatflow.md      # 简单问答 Chatflow（可选）

dify-embed/
└── index.html             # Dify 嵌入页面（可部署为静态站点）

backend/app/services/
├── search_service.py        # 搜索工具服务
├── business_service.py      # 工商查询服务
├── legal_service.py         # 法律查询服务
├── financial_service.py     # 财务分析服务
├── industry_service.py      # 行业分析服务
└── due_diligence_service.py # 深度尽调任务服务

backend/app/api/
└── dify_adapter.py        # Dify 适配层主文件
```

---

## 关键设计决策

### 1. 为什么用 `/api/v1/dify/invoke` 统一入口？

Dify 的 HTTP 工具节点需要配置固定的 URL 和参数。统一入口减少了 Dify 端的配置复杂度，所有操作通过 `action` 参数路由，Dify 只需配置一个 HTTP 节点即可。

### 2. 为什么轮询而不是 SSE？

Dify 的 HTTP 节点目前不支持 SSE 流式响应。轮询是可行的替代方案：
- 设置 3 秒轮询间隔，200 次最大重试（约 10 分钟）
- 大部分尽调任务在 2-5 分钟内完成
- 对于超长任务，Dify 用户可以先离开，稍后通过 task_id 查询

### 3. HITL 中断如何在 Dify 中处理？

当任务状态变为 `waiting_human` 时：
1. Dify 获取中断信息（`get_interrupts`）
2. Dify 的 LLM 节点将中断信息转换为人类可读的对话
3. Dify 的 Question 节点收集用户输入
4. Dify 调用 `resume_interrupt` 恢复任务
5. 任务回到 `running` 状态，继续轮询

### 4. 敏感数据如何隔离？

- **财报数据**：通过 `/api/v1/upload/financial` 直接上传到 ddg-agent，不经过 Dify
- **法律数据**：通过 `legal_service` 在 ddg-agent 内部查询，结果摘要返回给 Dify
- **企业工商数据**：同理，在 ddg-agent 内部查询
- **Dify LLM 只处理**：用户对话、报告摘要、简单问答

---

## 向后兼容性

所有原有 API 端点保持不变：
- `/api/v1/tasks/*` — 原任务管理 API
- `/api/v1/tools/*` — 原工具调用 API
- `/api/v1/upload/*` — 原上传 API

Dify 适配层是**新增**的 API，不影响现有前端或客户端的使用。

---

## 后续优化方向

1. **Webhook 推送**：当任务完成时，ddg-agent 通过 Webhook 主动通知 Dify，减少轮询延迟
2. **报告流式生成**：将报告分段生成，Dify 逐段展示，提升用户体验
3. **多任务管理**：Dify 支持同时追踪多个尽调任务
4. **知识库同步**：将 ddg-agent 的行业知识库同步到 Dify 知识库
