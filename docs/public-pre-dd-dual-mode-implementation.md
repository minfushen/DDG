# 公开资料预尽调与财报增强尽调双模式方案

## 背景

当前尽调 MVP 已打通前端输入、后端意图解析、四个专项 Agent、完整报告展示等基础链路，但在非上市中小企业未上传财报时，系统会阻塞在财务上传环节。这种处理方式适合正式财务专项分析，但不适合作为完整贷前尽调产品体验。

参考 Manus 生成的非上市中小企业贷前尽调报告，缺少用户上传财务报表时，系统不应编造财务指标，也不应直接失败，而应进入“公开资料预尽调”模式：基于公开工商、资质、行业、经营、司法、舆情等线索形成初步判断，同时明确披露财务数据边界和正式授信前需补充的材料。

## 目标

将当前“规则化完整尽调”升级为双模式尽调系统：

- `public_pre_dd`：公开资料预尽调。适用于非上市企业且未上传财报的场景。
- `financial_enhanced_dd`：财报增强尽调。适用于上市公司可获取公开财报，或非上市企业已上传近三年财报的场景。

## 模式判断

```python
if company_is_listed:
    report_mode = "financial_enhanced_dd"
elif uploaded_financial_files:
    report_mode = "financial_enhanced_dd"
else:
    report_mode = "public_pre_dd"
```

## 能力边界

| 能力 | 公开资料预尽调 | 财报增强尽调 |
| --- | --- | --- |
| 工商分析 | 支持 | 支持 |
| 行业分析 | 支持 | 支持 |
| 司法分析 | 支持 | 支持 |
| 财务分析 | 公开线索 + 待核验项 | 完整三大表指标分析 |
| 财务指标 | 不硬算缺失指标 | 毛利率、净利率、资产负债率、现金流等 |
| 授信建议 | 初步、有条件、需补充材料 | 可输出更正式的额度和期限建议 |
| 报告语气 | 强调证据边界 | 正式授信审查口径 |

## 后端最小闭环

### 新增模块

```text
backend/app/agents/planning/report_mode_detector.py
backend/app/agents/sub_agents/public_financial_agent.py
```

### 改造模块

```text
backend/app/agents/crew/full_due_diligence_runner.py
backend/app/agents/sub_agents/full_report_builder.py
backend/app/agents/orchestrator_v2.py
src/pages/Report/index.tsx
```

### 公开资料预尽调输出

当非上市企业没有上传财报时，财务 Agent 输出公开财务线索报告：

- `available_clues`：公开资料可支持的经营和财务线索。
- `unavailable_metrics`：因缺少财报不可计算的指标。
- `required_documents`：正式授信前需补充的材料。
- `credit_boundary`：当前报告只能作为初步预尽调，不可替代正式财务审查。

## 报告结构调整

完整报告新增字段：

```json
{
  "report_mode": "public_pre_dd",
  "financial_data_status": "public_clues_only",
  "financial_enhancement_available": true,
  "data_boundary": "当前未获取近三年财务报表，财务结论仅基于公开资料线索。",
  "required_documents": ["近三年审计报告", "最近一期财务报表"]
}
```

前端报告页展示：

- 报告模式标签。
- 财务数据完整度。
- 数据边界提示。
- 不可计算指标。
- 待补充材料清单。

## 后续增强方向

### Evidence Store

统一工商、财务、司法、行业 Agent 的证据结构，所有关键结论绑定证据来源、置信度和可核验状态。

### RAG 全链路接入

将工商审查要点、财务指标阈值、司法风险评级、行业尽调指南、贷后管理清单统一入库。四个 Agent 执行时均调用 RAG，报告中展示命中的知识库条目。

### Tool/MCP Gateway

将 Tavily、上市公司财报、工商 API、司法公开源、RAG 检索封装为统一工具接口，后续可平滑替换为 MCP 服务。

