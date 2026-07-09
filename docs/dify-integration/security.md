# Dify 集成安全与数据合规指南

> 确保敏感数据（财报、法诉、企业信息）在 Dify 集成过程中得到妥善保护。

---

## 1. API 认证机制

### 1.1 认证方式

Dify 适配层使用 Bearer Token 认证：

```
Authorization: Bearer {DIFY_AUTH_TOKEN}
```

### 1.2 Token 管理

- **生成**：在 ddg-agent 后端配置中设置 `DIFY_AUTH_TOKEN`，建议使用随机生成的 32 位以上字符串
- **存储**：存储在环境变量中，不提交到代码仓库
- **轮换**：建议定期轮换（如每 3 个月）
- **泄露处理**：如果 Token 泄露，立即更新 `DIFY_AUTH_TOKEN` 并重启后端

### 1.3 多环境配置

| 环境 | Token 建议 | 网络隔离 |
|------|-----------|---------|
| 开发环境 | 简单 Token，允许本地访问 | 本地网络 |
| 测试环境 | 中等复杂度 Token | 内网/VPN |
| 生产环境 | 强随机 Token + IP 白名单 | 防火墙隔离 |

---

## 2. 敏感数据隔离

### 2.1 数据流图

```
用户输入 ──→ Dify Chatflow ──→ ddg-agent API 适配层 ──→ 核心引擎 ──→ 工具层
     │           │                    │                  │           │
     │           │                    │                  │           └──→ 外部数据源
     │           │                    │                  │
     │           │                    │                  └──→ 证据审计链（核心引擎内部）
     │           │                    │
     │           │                    └──→ 不存储敏感数据，只做路由和编排
     │           │
     │           └──→ LLM 只处理：意图识别、摘要生成、简单问答
     │
     └──→ 原始输入（企业名称、简单问题）
```

### 2.2 敏感数据定义

| 数据类型 | 敏感级别 | 处理方式 | Dify 是否接触 |
|----------|---------|---------|-------------|
| 企业名称 | 低 | 明文传输 | ✅ 是 |
| 工商注册信息 | 中 | 后端查询，摘要返回 | ❌ 否（只返回摘要） |
| 法律诉讼记录 | 高 | 后端查询，摘要返回 | ❌ 否（只返回摘要） |
| 财务报表原始数据 | 极高 | 后端分析，不返回原始数据 | ❌ 否（只返回分析结果） |
| 财务分析结论 | 中 | 后端生成，返回摘要 | ❌ 否（只返回摘要） |
| 尽调报告全文 | 高 | 后端生成，返回摘要 + 链接 | ✅ 是（摘要） |
| 用户对话历史 | 中 | Dify 存储，用于上下文 | ✅ 是（建议关闭） |

### 2.3 敏感数据不经过 Dify 的证明

1. **财报数据**：
   - 上传路径：用户 → `/api/v1/upload/financial` → ddg-agent 后端
   - Dify 不接触上传接口，只通过 API 获取分析结果摘要

2. **法律数据**：
   - 查询路径：ddg-agent 后端 → 元典法律数据库 → 内部缓存 → 摘要返回给 Dify
   - Dify 只收到法律风险的摘要描述，不接触具体案例内容

3. **工商数据**：
   - 查询路径：ddg-agent 后端 → 天眼查/企查查 → 内部缓存 → 摘要返回给 Dify
   - Dify 只收到企业基础信息摘要

---

## 3. 数据出境风险评估

### 3.1 Dify 云服务数据流

如果使用 Dify 云服务（dify.ai），需要关注：

| 数据 | 是否出境 | 风险 | 缓解措施 |
|------|---------|------|---------|
| 用户对话内容 | 是（Dify 云存储） | 中 | 对话内容只包含企业名称和简单问题，不含敏感数据 |
| LLM 请求 | 是（OpenAI/Anthropic） | 中 | 只发送摘要和意图识别请求，不含敏感数据 |
| 知识库数据 | 是（Dify 向量存储） | 低 | 只存储公开的行业知识和 FAQ |
| 任务状态 | 否（ddg-agent 本地） | 无 | 任务状态存储在本地 SQLite |
| 证据链 | 否（ddg-agent 本地） | 无 | 证据链不离开本地服务器 |
| 财务数据 | 否（ddg-agent 本地） | 无 | 财务数据不经过 Dify |

### 3.2 私有化部署方案（推荐）

对于高安全要求的场景，建议：

1. **Dify 私有化部署**：在本地服务器或私有云部署 Dify
2. **LLM 私有化**：使用本地部署的大模型（如 Ollama、vLLM）替代 OpenAI
3. **网络隔离**：Dify 和 ddg-agent 在同一内网，不经过公网

### 3.3 合规声明模板

```markdown
## 数据合规声明

本系统采用分层架构：
- **Dify 层**：处理用户对话、意图识别、简单问答，不接触敏感企业数据
- **ddg-agent 核心引擎**：处理深度尽调、证据审计、财务分析，数据不离开本地服务器
- **工具层**：直接查询外部数据源，结果经过脱敏后返回

敏感数据（财务报表、法律诉讼、详细工商信息）仅在 ddg-agent 核心引擎内部处理，
不传输到 Dify 或第三方 LLM 服务。Dify 只接收经过摘要和脱敏后的分析结论。
```

---

## 4. 审计日志

### 4.1 日志记录内容

ddg-agent 后端记录所有 Dify 调用的审计日志：

```python
{
    "timestamp": "2024-01-01T12:00:00Z",
    "source": "dify",
    "action": "create_due_diligence",
    "task_id": "20240101120000abc123",
    "enterprise_name": "华为技术有限公司",
    "ip": "192.168.1.100",
    "user_agent": "Dify-Workflow/1.0",
    "response_status": "success",
    "duration_ms": 150
}
```

### 4.2 日志查看

```bash
# 查看 Dify 相关日志
grep "\[DifyAdapter\]" backend.log

# 查看任务创建日志
grep "create_due_diligence" backend.log

# 查看错误日志
grep "ERROR" backend.log | grep "Dify"
```

### 4.3 日志保留策略

| 日志类型 | 保留期限 | 存储位置 |
|---------|---------|---------|
| 访问日志 | 90 天 | `backend/logs/access.log` |
| 错误日志 | 180 天 | `backend/logs/error.log` |
| 审计日志 | 1 年 | `backend/logs/audit.log` |
| 任务快照 | 永久 | `backend/db/ddg_tasks.sqlite3` |

---

## 5. 最小权限原则

### 5.1 Dify 调用权限

Dify 只能调用以下端点：

```
/api/v1/dify/invoke
/api/v1/dify/status/{task_id}
/api/v1/dify/report/{task_id}
/api/v1/dify/interrupts/{task_id}
/api/v1/dify/interrupts/{task_id}/resume
/api/v1/dify/tools/{tool_name}
```

Dify **不能**调用以下内部端点：

```
/api/v1/tasks/*        ← 原任务管理 API（保留给前端/管理员）
/api/v1/upload/*       ← 文件上传（用户直接上传，不经过 Dify）
/api/v1/report-quality/* ← 质量评估（保留给管理员）
```

### 5.2 任务隔离

- Dify 只能查询自己创建的任务（通过 task_id 关联）
- 任务数据存储在本地 SQLite，不共享给其他应用
- 每个任务有独立的证据链，不可跨任务访问

---

## 6. 应急回退方案

### 6.1 Dify 服务不可用

如果 Dify 服务不可用，可以直接调用原 API：

```bash
# 创建任务（绕过 Dify）
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"enterprise_name": "华为技术有限公司"}'

# 查看任务状态（SSE 流式）
curl http://localhost:8000/api/v1/tasks/20240101120000abc123/stream
```

### 6.2 数据泄露应急响应

1. **立即**：更新 `DIFY_AUTH_TOKEN`，重启后端服务
2. **排查**：查看审计日志，确认泄露范围
3. **通知**：根据公司安全流程通知相关方
4. **修复**：检查代码和配置，修复安全漏洞
5. **复盘**：更新安全策略，防止再次发生

### 6.3 完全回退到原前端

如果 Dify 集成不可行，可以：
1. 在 `settings.py` 中设置 `ENABLE_DIFY_INTEGRATION = False`
2. 继续使用原有的 React 前端
3. Dify 适配层 API 仍然可用，但不再被调用

---

## 7. 安全清单

部署前必须检查：

- [ ] `DIFY_AUTH_TOKEN` 已设置为强随机字符串
- [ ] `DIFY_AUTH_TOKEN` 存储在环境变量中，不在代码中硬编码
- [ ] 生产环境启用了 IP 白名单或防火墙限制
- [ ] 审计日志已启用并配置保留策略
- [ ] 敏感数据（财报、法诉）不经过 Dify 的确认
- [ ] 定期轮换 `DIFY_AUTH_TOKEN`（建议每 3 个月）
- [ ] 错误日志不包含敏感数据（如 API Key、密码）
- [ ] 后端服务运行在 HTTPS（生产环境）
- [ ] CORS 配置只允许可信来源（生产环境）

---

## 8. 参考文档

- Dify 官方文档：https://docs.dify.ai
- Dify 安全最佳实践：https://docs.dify.ai/getting-started/readme#security
- FastAPI 安全文档：https://fastapi.tiangolo.com/tutorial/security/
