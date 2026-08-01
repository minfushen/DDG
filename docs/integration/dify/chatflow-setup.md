# Dify Chatflow 配置指南

> 手把手在 Dify UI 中搭建尽调工作流。

---

## 准备工作

### 1. 启动 ddg-agent 后端

```bash
cd /path/to/ddg-agent/backend
source venv/bin/activate
python3 run.py
```

确认后端启动成功：
```bash
curl http://localhost:8000/health
# 应返回 {"status": "healthy", ...}
```

### 2. 获取 Dify 账号和 API Key

- 注册 Dify 账号（https://dify.ai 或私有化部署）
- 创建 Chatflow 应用
- 在「设置」→「API Key」中获取应用 API Key（用于嵌入）
- 在「环境变量」中配置 `DIFY_AUTH_TOKEN`（ddg-agent 后端认证用）

### 3. 配置 ddg-agent 环境变量

在 `backend/.env` 中添加：

```env
DIFY_AUTH_TOKEN=sk-your-secret-token-here
ENABLE_DIFY_INTEGRATION=true
```

---

## 步骤1：创建 Chatflow 应用

1. 登录 Dify 控制台
2. 点击「创建应用」→「Chatflow（聊天工作流）」
3. 输入应用名称：「DDG 智能尽调」
4. 选择模型：建议使用 `gpt-4o-mini`（意图识别）和 `gpt-4o`（报告生成）

---

## 步骤2：配置开始节点

1. 点击「开始」节点
2. 添加变量：
   - 名称：`enterprise_name`
   - 类型：`text-input`
   - 必填：`是`
   - 提示词：`请输入要尽调的企业名称，如：华为技术有限公司`

---

## 步骤3：配置意图识别 LLM

1. 添加「LLM」节点，连接「开始」节点
2. 配置：
   - 模型：`gpt-4o-mini`（成本低，速度快）
   - 系统提示词：
     ```
     你是一个尽调任务路由助手。请判断用户输入的意图：
     - "deep_diligence": 用户想要对某企业进行完整深度尽调
     - "simple_qa": 用户只是简单询问某个问题或企业信息
     - "tool_query": 用户想要直接查询某个工具

     输出格式（严格的 JSON）：
     {"intent": "deep_diligence|simple_qa|tool_query", "enterprise_name": "提取的企业名称", "tool_hint": "工具提示词（如有）"}
     ```
   - 上下文：留空（不需要）
   - 温度：0.1（意图识别需要确定性）
   - 输出解析器：选择「JSON 解析器」

3. 连接下一个节点：「条件分支」

---

## 步骤4：配置条件分支

1. 添加「If-Else」节点，连接「意图识别 LLM」
2. 配置三个条件：

   **条件1：简单问答**
   - 表达式：`{{#intent_classifier.intent#}} == 'simple_qa'`
   - 连接：「知识库检索」节点

   **条件2：工具查询**
   - 表达式：`{{#intent_classifier.intent#}} == 'tool_query'`
   - 连接：「工具调用」节点

   **条件3：深度尽调**
   - 表达式：`{{#intent_classifier.intent#}} == 'deep_diligence'`
   - 连接：「创建任务」节点

---

## 步骤5：配置简单问答分支

### 5.1 知识库检索

1. 添加「知识库检索」节点
2. 配置：
   - 知识库：选择已创建的知识库（如「行业知识库」或「FAQ 库」）
   - 查询：`{{#start.enterprise_name#}}`
   - 返回数量：5

### 5.2 LLM 回答

1. 添加「LLM」节点，连接「知识库检索」
2. 配置：
   - 模型：`gpt-4o`
   - 系统提示词：`你是尽调智能问答助手。请基于检索到的知识库内容回答用户问题。如果知识库中没有相关信息，请诚实地告知用户，并建议进行深度尽调。`
   - 上下文：选择「知识库检索」的结果
   - 温度：0.7

### 5.3 结束节点

1. 添加「结束」节点，连接「LLM 回答」
2. 配置输出：`{{#llm.text#}}`

---

## 步骤6：配置深度尽调分支

### 6.1 创建任务（HTTP Request）

1. 添加「HTTP 请求」节点，连接「条件分支」的 deep_diligence 分支
2. 配置：
   - 方法：`POST`
   - URL：`http://localhost:8000/api/v1/dify/invoke`
   - 请求头：
     ```
     Content-Type: application/json
     Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}
     ```
   - 请求体（JSON）：
     ```json
     {
       "action": "create_due_diligence",
       "enterprise_name": "{{#start.enterprise_name#}}",
       "template_name": "full"
     }
     ```
   - 超时：30 秒

### 6.2 存储任务ID（变量节点）

1. 添加「变量赋值」节点，连接「创建任务」
2. 配置：
   - 变量名：`task_id`
   - 值：`{{#http.body.data.task_id#}}`

### 6.3 轮询状态循环

**6.3.1 状态查询**

1. 添加「HTTP 请求」节点
2. 配置：
   - 方法：`GET`
   - URL：`http://localhost:8000/api/v1/dify/status/{{#task_id#}}`
   - 请求头：`Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}`
   - 超时：10 秒

**6.3.2 检查状态（If-Else）**

1. 添加「If-Else」节点，连接「状态查询」
2. 配置四个条件：
   - `completed`：`{{#http.status#}} == 'completed'` → 连接「获取报告」
   - `waiting_human`：`{{#http.status#}} == 'waiting_human'` → 连接「获取中断」
   - `failed`：`{{#http.status#}} == 'failed'` → 连接「错误处理」
   - `running`：`{{#http.status#}} == 'running'` → 连接「等待节点」

**6.3.3 等待节点**

1. 添加「代码执行」节点（或「变量赋值」节点配合延迟）
2. 如果使用代码节点：
   - 语言：`Python3`
   - 代码：`import time; time.sleep(3); return {"waited": True}`
3. 连接回「状态查询」节点（形成循环）

> **注意**：Dify 的循环通过节点连接实现。从「等待节点」的输出连接回「状态查询」的输入，即可形成轮询循环。

### 6.4 HITL 中断处理

**6.4.1 获取中断**

1. 添加「HTTP 请求」节点，连接「检查状态」的 waiting_human 分支
2. 配置：
   - 方法：`GET`
   - URL：`http://localhost:8000/api/v1/dify/interrupts/{{#task_id#}}`
   - 请求头：`Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}`

**6.4.2 展示中断（LLM）**

1. 添加「LLM」节点，连接「获取中断」
2. 配置：
   - 模型：`gpt-4o`
   - 系统提示词：`请向用户展示任务中断信息，并询问用户如何处理。请用友好、简洁的中文描述。`
   - 上下文：`{{#http.body.active#}}`

**6.4.3 用户选择（Question）**

1. 添加「问题」节点，连接「展示中断」
2. 配置：
   - 问题：`{{#llm.text#}}`
   - 类型：文本输入
   - 占位符：`请输入您的选择或补充信息`

**6.4.4 恢复中断**

1. 添加「HTTP 请求」节点，连接「用户选择」
2. 配置：
   - 方法：`POST`
   - URL：`http://localhost:8000/api/v1/dify/interrupts/{{#task_id#}}/resume?interrupt_id={{#http.body.active.id#}}&action={{#question.answer#}}`
   - 请求头：`Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}`
3. 连接回「等待节点」→「状态查询」（继续轮询）

### 6.5 报告获取与展示

**6.5.1 获取报告**

1. 添加「HTTP 请求」节点，连接「检查状态」的 completed 分支
2. 配置：
   - 方法：`GET`
   - URL：`http://localhost:8000/api/v1/dify/report/{{#task_id#}}`
   - 请求头：`Authorization: Bearer {{#env.DIFY_AUTH_TOKEN#}}`
   - 超时：30 秒

**6.5.2 生成摘要（LLM）**

1. 添加「LLM」节点，连接「获取报告」
2. 配置：
   - 模型：`gpt-4o`
   - 系统提示词：`你是尽调报告分析师。请基于以下报告数据生成一份简洁的中文执行摘要...`
   - 上下文：`{{#http.body#}}`
   - 温度：0.3

**6.5.3 结束节点**

1. 添加「结束」节点，连接「生成摘要」
2. 配置输出：
   ```
   # {{#http.body.enterprise_name#}} 尽调报告

   {{#llm.text#}}

   ---
   **风险等级**: {{#http.body.risk_level#}}
   **风险评分**: {{#http.body.risk_score#}}/100
   **完整报告**: {{#http.body.report_url#}}
   ```

---

## 步骤7：测试和调试

### 7.1 预览测试

1. 点击 Dify 右上角的「预览」
2. 输入：`帮我做一份华为技术有限公司的尽调报告`
3. 观察：
   - 意图识别是否正确（deep_diligence）
   - 任务是否创建成功
   - 轮询是否正常
   - 报告是否正确返回

### 7.2 调试技巧

- **任务创建失败**：检查后端是否启动，API 地址和 Token 是否正确
- **轮询不停止**：检查状态查询的 URL 和变量是否正确引用
- **报告为空**：检查报告端点是否返回数据，task_id 是否正确
- **中断处理失败**：检查中断 ID 和 resume 端点的参数

### 7.3 日志查看

后端日志查看：
```bash
tail -f /path/to/ddg-agent/backend/backend.log
```

查看 Dify HTTP 请求日志：在 Dify 的「日志与标注」中查看每次对话的详细请求和响应。

---

## 常见问题

### Q1: 轮询次数太多怎么办？

在「环境变量」中设置 `DDG_POLL_MAX` 为合适的值（如 100）。如果任务超时，可以提示用户稍后通过 task_id 查询。

### Q2: 如何支持同时追踪多个任务？

在 Dify 的「对话开场白」中提示用户提供 task_id，或者在「变量」中存储多个 task_id（用数组）。

### Q3: 报告太长，Dify 输出被截断？

使用 LLM 节点生成摘要，只展示关键信息。提供「完整报告链接」让用户自行查看。

### Q4: 如何在不暴露敏感数据的情况下展示财务分析？

Dify 的 LLM 只处理摘要和格式化，不接触原始财务数据。原始数据在 ddg-agent 后端处理，只返回摘要和指标。

### Q5: 可以接入 Dify 的知识库吗？

可以。将行业知识、FAQ、术语库导入 Dify 知识库，供简单问答分支使用。深度尽调分支仍由 ddg-agent 核心引擎执行。
