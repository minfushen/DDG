# Dify Chatflow 配置说明

> 由于 Dify Chatflow 的 JSON 导出格式较为复杂且版本相关，本文件以 YAML 结构描述每个节点的配置，供在 Dify UI 中手动搭建。

---

## 深度尽调 Chatflow 节点配置

### 1. 开始节点 (Start)

```yaml
id: start
 type: start
 data:
   title: 开始
   variables:
     - name: enterprise_name
       label: 企业名称
       type: text-input
       required: true
       placeholder: "请输入要尽调的企业名称，如：华为技术有限公司"
```

### 2. 意图识别 LLM (LLM)

```yaml
id: intent_classifier
 type: llm
 data:
   title: 意图识别
   model: gpt-4o-mini  # 或本地模型
   system_prompt: |
     你是一个尽调任务路由助手。请判断用户输入的意图：
     - "deep_diligence": 用户想要对某企业进行完整深度尽调（如"帮我做一份华为技术有限公司的尽调报告"）
     - "simple_qa": 用户只是简单询问某个问题或企业信息（如"华为是做什么的"）
     - "tool_query": 用户想要直接查询某个工具（如"搜索华为的法律诉讼"）

     输出格式（严格的 JSON）：
     {"intent": "deep_diligence|simple_qa|tool_query", "enterprise_name": "提取的企业名称", "tool_hint": "工具提示词（如有）"}
   temperature: 0.1
   output_parser: json
```

### 3. 条件分支 (If-Else)

```yaml
id: route_by_intent
 type: if-else
 data:
   title: 按意图路由
   conditions:
     - id: simple_qa
       expression: "{{intent_classifier.intent}} == 'simple_qa'"
     - id: tool_query
       expression: "{{intent_classifier.intent}} == 'tool_query'"
     - id: deep_diligence
       expression: "{{intent_classifier.intent}} == 'deep_diligence'"
```

### 4. 简单问答分支

#### 4.1 知识库检索 (Knowledge Retrieval)

```yaml
id: kb_retrieval
 type: knowledge-retrieval
 data:
   title: 知识库检索
   knowledge_id: YOUR_KNOWLEDGE_BASE_ID
   query: "{{#start.enterprise_name#}}"
   top_k: 5
```

#### 4.2 LLM 回答 (LLM)

```yaml
id: simple_answer
 type: llm
 data:
   title: 生成回答
   system_prompt: |
     你是尽调智能问答助手。请基于检索到的知识库内容回答用户问题。
     如果知识库中没有相关信息，请诚实地告知用户，并建议进行深度尽调。
   context: "{{kb_retrieval.result}}"
   temperature: 0.7
```

#### 4.3 结束 (End)

```yaml
id: end_simple
 type: end
 data:
   title: 结束
   output: "{{simple_answer.text}}"
```

### 5. 深度尽调分支

#### 5.1 创建任务 (HTTP Request)

```yaml
id: create_task
 type: http-request
 data:
   title: 创建尽调任务
   method: POST
   url: "http://localhost:8000/api/v1/dify/invoke"
   headers:
     Content-Type: application/json
     Authorization: "Bearer {{#env.DIFY_AUTH_TOKEN#}}"
   body:
     action: create_due_diligence
     enterprise_name: "{{#start.enterprise_name#}}"
     template_name: full
```

#### 5.2 变量节点：存储 task_id

```yaml
id: store_task_id
 type: variable-assigner
 data:
   title: 存储任务ID
   variables:
     - name: task_id
       value: "{{create_task.body.data.task_id}}"
```

#### 5.3 轮询状态循环

**5.3.1 状态查询 (HTTP Request)**

```yaml
id: poll_status
 type: http-request
 data:
   title: 查询任务状态
   method: GET
   url: "http://localhost:8000/api/v1/dify/status/{{store_task_id.task_id}}"
   headers:
     Authorization: "Bearer {{#env.DIFY_AUTH_TOKEN#}}"
```

**5.3.2 检查是否完成 (If-Else)**

```yaml
id: check_status
 type: if-else
 data:
   title: 检查状态
   conditions:
     - id: completed
       expression: "{{poll_status.body.status}} == 'completed'"
     - id: waiting_human
       expression: "{{poll_status.body.status}} == 'waiting_human'"
     - id: failed
       expression: "{{poll_status.body.status}} == 'failed'"
     - id: running
       expression: "{{poll_status.body.status}} == 'running'"
```

**5.3.3 等待节点 (Code / Variable)**

```yaml
id: wait_before_poll
 type: code
 data:
   title: 等待3秒
   language: python3
   code: |
     import time
     time.sleep(3)
     return {"waited": True}
```

**5.3.4 循环连接**

从 `check_status` → `running` 分支 → `wait_before_poll` → `poll_status`（形成循环）

#### 5.4 HITL 中断处理

**5.4.1 获取中断 (HTTP Request)**

```yaml
id: get_interrupts
 type: http-request
 data:
   title: 获取中断信息
   method: GET
   url: "http://localhost:8000/api/v1/dify/interrupts/{{store_task_id.task_id}}"
   headers:
     Authorization: "Bearer {{#env.DIFY_AUTH_TOKEN#}}"
```

**5.4.2 展示中断 (LLM)**

```yaml
id: show_interrupt
 type: llm
 data:
   title: 展示中断信息
   system_prompt: |
     请向用户展示任务中断信息，并询问用户如何处理。
     中断信息：{{get_interrupts.body.active}}
     请用友好、简洁的中文描述中断内容和选项。
```

**5.4.3 用户选择 (Question)**

```yaml
id: user_choice
 type: question
 data:
   title: 用户选择
   question: "{{show_interrupt.text}}"
   type: text-input
   placeholder: "请输入您的选择或补充信息"
```

**5.4.4 恢复中断 (HTTP Request)**

```yaml
id: resume_interrupt
 type: http-request
 data:
   title: 恢复中断
   method: POST
   url: "http://localhost:8000/api/v1/dify/interrupts/{{store_task_id.task_id}}/resume"
   headers:
     Content-Type: application/json
     Authorization: "Bearer {{#env.DIFY_AUTH_TOKEN#}}"
   body:
     interrupt_id: "{{get_interrupts.body.active.id}}"
     action: "{{user_choice.text}}"
```

**5.4.5 恢复后回到轮询**

从 `resume_interrupt` → `wait_before_poll` → `poll_status`

#### 5.5 报告获取与展示

**5.5.1 获取报告 (HTTP Request)**

```yaml
id: get_report
 type: http-request
 data:
   title: 获取尽调报告
   method: GET
   url: "http://localhost:8000/api/v1/dify/report/{{store_task_id.task_id}}"
   headers:
     Authorization: "Bearer {{#env.DIFY_AUTH_TOKEN#}}"
```

**5.5.2 生成摘要 (LLM)**

```yaml
id: report_summary
 type: llm
 data:
   title: 生成报告摘要
   model: gpt-4o
   system_prompt: |
     你是尽调报告分析师。请基于以下报告数据生成一份简洁的中文执行摘要：
     1. 企业概况（2-3句）
     2. 核心风险点（3-5个bullet）
     3. 关键财务指标概览
     4. 建议下一步行动

     请用专业但易读的语言，避免过于模板化的表述。
   context: "{{get_report.body}}"
   temperature: 0.3
```

**5.5.3 结束 (End)**

```yaml
id: end_report
 type: end
 data:
   title: 展示报告
   output: |
     # {{get_report.body.enterprise_name}} 尽调报告

     {{report_summary.text}}

     ---
     **完整报告链接**: {{get_report.body.report_url}}
     **风险等级**: {{get_report.body.risk_level}}
     **风险评分**: {{get_report.body.risk_score}}/100
```

### 6. 工具查询分支

```yaml
id: tool_call
 type: http-request
 data:
   title: 直接调用工具
   method: POST
   url: "http://localhost:8000/api/v1/dify/tools/searxng"
   headers:
     Content-Type: application/json
     Authorization: "Bearer {{#env.DIFY_AUTH_TOKEN#}}"
   body:
     query: "{{intent_classifier.tool_hint}}"
     max_results: 8
```

```yaml
id: tool_answer
 type: llm
 data:
   title: 工具结果回答
   system_prompt: 请基于工具搜索结果回答用户问题。
   context: "{{tool_call.body.data}}"
```

---

## 节点连接图（简化）

```
[start] → [intent_classifier]
              │
    ┌─────────┼─────────┐
    │         │         │
[simple_qa] [tool]  [deep_diligence]
    │         │         │
 [kb]     [tool_call] [create_task]
    │         │         │
 [llm]   [tool_answer] [store_task_id]
    │         │         │
   [end]    [end]   [poll_status]
                         │
                    [check_status]
                         │
              ┌─────────┼─────────┐
              │         │         │
           [running] [waiting] [completed]
              │         │         │
         [wait]   [get_interrupts] [get_report]
              │         │         │
              └─────────┘         │
              [resume]      [report_summary]
                                    │
                                   [end]
```

---

## 环境变量配置

在 Dify 应用的「环境变量」中配置：

| 变量名 | 值 | 说明 |
|--------|------|------|
| DDG_API_BASE_URL | http://localhost:8000 | ddg-agent 后端地址 |
| DIFY_AUTH_TOKEN | sk-xxxx | API 认证令牌 |
| DDG_POLL_INTERVAL | 3 | 轮询间隔（秒） |
| DDG_POLL_MAX | 200 | 最大轮询次数 |

---

## 注意事项

1. **轮询循环**：Dify 当前版本不直接支持循环，需通过变量节点和条件节点模拟。
2. **SSE 不支持**：ddg-agent 后端已关闭 SSE，所有状态通过轮询获取。
3. **超时处理**：设置 `DDG_POLL_MAX` 为 200（约 10 分钟），避免无限轮询。
4. **HITL 恢复**：中断恢复后需要重新进入轮询循环。
5. **报告展示**：建议 LLM 生成摘要而非直接输出完整 JSON，避免信息过载。
