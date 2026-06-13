# 11 DeepResearch Engine 数据结构与测试方案

## 数据结构

### ResearchTask

```json
{
  "id": "rt_subject_identity",
  "question": "目标企业主体与上市公司证券代码是否匹配？",
  "purpose": "确认分析对象，避免企业简称、集团主体和上市主体混淆",
  "category": "business",
  "required_evidence": ["上市公司基础信息", "工商主体名称", "证券代码"],
  "priority": 1,
  "status": "pending",
  "tool_hints": ["listed_company", "business_agent", "bocha_search"]
}
```

### ResearchEvidence

复用 Evidence Store 标准结构，并要求最少包含：

- `id`
- `label`
- `claim`
- `source`
- `source_url`
- `source_type`
- `confidence`
- `trust_level`
- `requires_manual_review`
- `agent`
- `domain`

### ResearchClaim

```json
{
  "id": "cl_xxx",
  "task_id": "rt_industry_position",
  "text": "目标企业主营业务与半导体/集成电路制造行业分类基本一致",
  "evidence_ids": ["ev_xxx", "ev_yyy"],
  "confidence": 0.78,
  "risk_level": "medium",
  "missing_evidence": ["需补充主营构成收入占比和同业对标"],
  "requires_manual_review": true
}
```

### ResearchGap

```json
{
  "id": "gap_xxx",
  "task_id": "rt_financial_trend",
  "description": "未获取近三年三大表，核心财务指标无法形成正式结论",
  "why_it_matters": "财务真实性和偿债能力是授信准入的核心依据",
  "suggested_next_actions": ["上传近三年审计报告", "接入上市公司财报结构化数据源"],
  "severity": "high"
}
```

### ResearchReport

```json
{
  "report_type": "deepresearch_due_diligence",
  "enterprise_name": "士兰微",
  "objective": "完整贷前尽调",
  "research_plan": [],
  "claims": [],
  "evidence": [],
  "gaps": [],
  "summary": [],
  "data_boundary": "公开资料仅作为线索，正式授信前需权威源复核"
}
```

## 数据源分级

| source_type | 可信度 | 用途 |
| --- | --- | --- |
| `official_or_authoritative_public_source` | 高 | 交易所、巨潮、政府、法院、信用中国 |
| `financial_statement` | 高 | 财报、审计报告、用户上传三大表 |
| `business_registry` | 高/中 | 国家工商、企查查/天眼查等商业数据 |
| `internal_knowledge_base` | 中/高 | 内部授信制度、行业规则、案例 |
| `public_web_search_clue` | 中低 | 普通网页搜索结果 |
| `low_reliability_public_source` | 低 | 文库、论坛、自媒体 |
| `simulation_or_system_boundary` | 低 | 兜底或系统提示，不作为正式证据 |

## 测试分层

### 单元测试

目标：验证数据结构、规则 planner、claim builder、gap reflector。

测试项：

- 默认研究计划是否包含主体、工商、财务、司法、行业、授信政策任务。
- Evidence 转 Claim 是否绑定 evidence_ids。
- 低可信 evidence 是否触发人工复核。
- 无财务 evidence 是否生成财报上传 gap。
- Bocha 结果是否能规范化为 Evidence。

### 集成测试

目标：验证 Research Engine 能调用现有工具并输出 research_report。

测试样本：

1. `士兰微`：上市公司、半导体、公告/财报/行业资料较多。
2. `闻泰科技`：上市公司、司法/重大诉讼线索明显。
3. `湖南省第二工程有限公司`：非上市企业、需要公开预尽调/上传财报。
4. `蓝思科技`：上市公司，验证企业名简称识别。

### 端到端测试

目标：前端展示 research plan、evidence、claim、gap、report。

第一阶段如不改前端，则通过后端函数和 API 输出 JSON 验证。

## 验收标准

第一阶段验收：

- 能生成 Research Plan。
- 能执行至少 3 类研究任务。
- 能调用 Bocha/RAG/现有单 Agent 中至少两类工具。
- 能生成 Evidence、Claim、Gap。
- 能输出 `deepresearch_due_diligence` 报告 JSON。
- 不影响现有完整尽调和单 Agent 链路。

第二阶段验收：

- 接入 Sequential Thinking MCP 做动态规划和反思。
- 支持 follow-up task。
- 前端展示研究计划和证据链。
- Claim 级别报告可被完整尽调报告引用。

## 安全与合规测试

- 不在日志和文档中写入 API key。
- 公开搜索证据默认 requires_manual_review。
- 私有化部署可关闭公网搜索。
- 用户上传材料 evidence 标记为 `uploaded_private_file`。
- Claim 不得引用不存在的 evidence_id。

