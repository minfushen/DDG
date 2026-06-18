---
name: loan-due-diligence
description: Runtime methodology for bank pre-loan due diligence. Use when a task asks for enterprise credit due diligence, loan investigation, customer manager review draft, or full due-diligence report.
---

# Loan Due Diligence Runtime Skill

## Goal

Generate a business-readable pre-loan due-diligence report. The report must lead with conclusions and credit actions, not research process.

## Report Outline

1. 资料完整度总览
2. 报告摘要与授信建议
3. 企业主体与治理结构
4. 财务状况与偿债能力
5. 行业与经营环境
6. 司法与合规风险
7. 交叉验证与重大风险
8. 信贷方案建议
9. 证据链与待补充材料

## Evidence Checklist

Machine-readable resources:

- `references/evidence_blueprint.schema.json`: JSON Schema for the evidence blueprint.
- `references/default_evidence_blueprint.json`: default report outline, chapter evidence requirements, completeness matrix, preferred tools, success criteria, fallback language, and credit action rules.

Planner must load `default_evidence_blueprint.json` first. The table below is for human readability only.

| Chapter | Required data | Preferred source | Fallback language |
| --- | --- | --- | --- |
| 主体治理 | 工商登记、经营状态、股权/实控人、对外投资、异常经营、行政处罚 | 权威工商源、上市公告、客户授权数据源 | 基于现有资料推断，授信前需权威工商源复核 |
| 财务偿债 | 近三年三大表、审计意见、收入利润、现金流、资产负债、应收存货、短债 | 上传财报、上市公告、财务数据包、内部计算工具 | 财务资料不足时，不测算正式额度，将三大表/流水/纳税列为前置材料 |
| 行业经营 | 主营构成、行业定位、周期、竞争格局、政策、上下游、授信关注点 | 年报经营讨论、RAG、研报/行业资料、公告 | 基于现有资料作审慎预判，需补充行业研报或内部行业政策 |
| 司法合规 | 裁判、执行、失信、行政处罚、监管问询、重大舆情 | 权威司法源、交易所公告、监管公告、公开搜索线索 | 暂未见重大阻断性风险，不等于无风险，提款前需权威源复核 |
| 信贷建议 | 准入、额度、期限、担保、提款条件、贷后监控 | 专项结论、内部授信制度、客户材料 | 证据缺口转化为提款前置条件、担保条件或贷后监控指标 |

## Writing Rules

- Start every chapter with 1-3 business judgments.
- Use cautious but useful conclusions: “基于现有资料推断”, “疑似”, “暂未见明确重大异常”, “需核实”.
- Do not ask the reader to infer conclusions from process logs.
- Evidence is supporting material; keep it inline and collapsible, or move it to appendix.
- When data is missing, still provide a credit action: precondition, material list, monitoring item, or temporary limit boundary.
- Never fabricate exact credit amount, legal result, shareholder, or financial number without evidence.

## Planner Instructions

Plan by report chapter first, then evidence need, then tool route. Cover主体、财务、行业、司法、授信边界 at minimum. Use `references/default_evidence_blueprint.json` as the source of truth for chapter tasks and completeness matrix.

Each task should include:

- chapter
- required_data
- preferred_tools
- success_criteria
- fallback_language
