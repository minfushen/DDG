# 19 Runtime Skill Planner 产品与工程设计

## 1. 背景

对标 Kimi Agent 的思考过程后，确认一个关键差距：专业 Agent 在执行贷前尽调前，会先读取或加载“deep-research / due-diligence skill”，把任务方法论、章节结构、数据需求和输出规范作为计划依据。

DDG-Agent 之前已经具备工具链：Sequential Thinking、Planner、Tool Router、RAG、Evidence、CodeAct、Synthesizer。但缺少运行时方法论层，导致 Planner 有时只是在生成研究问题，而不是按银行尽调 checklist 工作。

## 2. 目标

新增 Runtime Skill Planner，让项目形成稳定的产品/工程模式：

```text
用户任务
  -> 意图识别
  -> Skill Runtime 加载任务手册
  -> Blueprint Planner 生成章节/证据需求/工具计划
  -> Tool Router 执行
  -> Evidence + Claim + Gap
  -> Synthesizer 按业务报告体例装配
```

## 3. 本轮新增技能

技能目录：

```text
backend/data/knowledge_base/skills/
  deep_research/SKILL.md
  loan_due_diligence/SKILL.md
  financial_analysis/SKILL.md
```

### deep_research

定义 Plan-Execute 研究流程：主体边界、证据计划、工具执行、二轮补证、claim-evidence、报告装配。

### loan_due_diligence

定义贷前尽调报告框架、资料完整度、各章节 required data、fallback language 和业务化写作规则。

该技能现在包含机器可读资源：

```text
backend/data/knowledge_base/skills/loan_due_diligence/references/
  evidence_blueprint.schema.json
  default_evidence_blueprint.json
```

- `evidence_blueprint.schema.json`：定义贷前尽调 evidence blueprint 的字段规范。
- `default_evidence_blueprint.json`：Planner 的默认蓝图，包含 report outline、chapter evidence requirements、preferred tools、success criteria、fallback language、credit action when missing、completeness matrix。

这份 JSON 蓝图是 Planner 生成章节任务和 Synthesizer 生成资料完整度矩阵的 source of truth。Markdown 表格只保留给人阅读。

### financial_analysis

定义信用视角财务分析规则：三年趋势、勾稽关系、异常信号、风险定性和核查动作。

## 4. 后端实现

新增：

```text
backend/app/agents/skills/skill_loader.py
```

核心能力：

- 从本地 Markdown `SKILL.md` 读取 frontmatter 和正文。
- 自动读取 skill `references/*.json` 资源。
- 根据任务意图加载 `deep_research`、`loan_due_diligence`、`financial_analysis`。
- 输出 `skill_ids`、`context`、`errors`。
- 输出 `default_evidence_blueprint.json` 给 Planner 和 Synthesizer 使用。
- Planner prompt 注入 `skill_context`。

## 5. Planner 改造

`create_research_plan()` 现在会：

- 加载 runtime skills。
- 从 `loan_due_diligence/references/default_evidence_blueprint.json` 加载 due diligence blueprint。
- 基于 blueprint chapters 自动生成默认章节任务。
- 将 skill context 注入 LLM Planner。
- LLM 失败时，规则 fallback 仍保留 runtime skill metadata。

Planner 不再只是生成研究问题，而是遵循：

```text
章节 -> 证据需求 -> 工具路线 -> 兜底表达
```

## 6. Synthesizer 改造

报告新增第一章：

```text
一、资料完整度总览
```

该章节按主体、财务、行业、司法四类资料展示：

- 完整度：高/中/低
- 当前结论强度
- 需补充或转化为授信动作的事项

完整度矩阵优先读取 blueprint 中的 `completeness_matrix`，因此后续要调整“完整度判断”和“fallback language”时，应优先修改 skill JSON，而不是改 Synthesizer 代码。

最终报告保留：

- `runtime_skills`
- `due_diligence_blueprint`

用于调试、审计和质量评测，但前端主阅读流不展示技术细节。

## 7. 产品原则

- Skill 是方法论，不是外部数据源。
- Skill 不能替代权威工商、司法、财务数据。
- Skill 用来让 Agent 按专业流程做事，而不是临场组织 prompt。
- 报告页仍以业务结论为主，skill 加载过程只在执行页或调试信息中展示。
- 数据不足时允许审慎推断，但必须给出授信动作：前置条件、担保条件、贷后监控或暂缓准入。

## 8. 验收标准

- 后端能读取 3 个 runtime skill。
- Planner metadata 包含 `runtime_skills` 和 `blueprint`。
- LLM Planner prompt 注入 skill context。
- Synthesizer 输出资料完整度总览章节。
- 前端仍保持业务结论阅读流，不把 skill 文本直接展示给客户经理。
