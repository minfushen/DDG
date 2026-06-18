# 16 CodeAct 代码即工具产品与技术设计

## 1. 背景与定位

DDG-Agent 当前已经具备 DeepResearch 编排、RAG、Evidence Store、报告质量评测和离线回归能力。项目中也沉淀了很多 Python 脚本和确定性分析函数，例如报告质量评测、财务指标计算、知识库入库、离线回归等。

CodeAct 的目标不是让大模型随意写代码并执行，而是把这些“已经被验证过的代码能力”注册成可被 Agent 调用的内部工具。也就是说，CodeAct 在本项目中的第一阶段定位是：

- 让 Agent 能调用白名单代码工具完成确定性计算、评测、校验和批处理。
- 让工具输出结构化 JSON，并进入 Evidence Store 或任务审计日志。
- 将代码脚本从“开发者手工运行”升级为“研究引擎可编排的能力”。
- 保持安全边界，默认不开放任意 Python 代码执行。

## 2. 产品价值

CodeAct 适合补齐 LLM 和传统工具之间的空白：

| 场景 | 传统做法 | CodeAct 价值 |
| --- | --- | --- |
| 报告质量评测 | 开发者手工跑脚本 | 报告生成后自动评测，输出问题清单和分数 |
| 离线回归 | 命令行批处理 | 可被任务系统或评测页面触发，形成可视化质量闭环 |
| 财务指标计算 | 写在 Agent 内部 | 抽成稳定工具，LLM 只负责诊断表达 |
| 知识库入库校验 | 运维手工检查 | 入库前自动检查格式、来源、敏感字段和 chunk 质量 |
| 私有化 T+1 数据包校验 | 人工抽查 | 自动校验数据包 schema、日期、checksum 和证据覆盖 |

对客户经理和产品演示来说，CodeAct 不需要暴露为“代码执行”。前端可以统一展示为“内部校验工具”“质量评测工具”“数据校验工具”等业务化名称。

## 3. 架构位置

CodeAct 是 Tool Router 下的一类工具，不替代 MCP、RAG、搜索工具或专项 Agent。

```text
Planner / LangGraph Node
  -> Tool Router
  -> CodeAct Runner
  -> Registered Code Tool
  -> Structured JSON Result
  -> Evidence Store / Task Audit / Report Quality Drawer
  -> Synthesizer / Frontend
```

与现有模块的关系：

- Planner 只表达“需要做什么校验或计算”，不关心代码实现细节。
- Tool Router 根据 `codeact:<tool_name>` 或后端任务类型路由到 CodeAct Runner。
- CodeAct Runner 只执行注册表中的工具。
- Registered Tool 封装已有 Python 函数或脚本。
- 返回结果必须是 JSON 可序列化对象。
- 如结果支撑报告正文，可进一步转为 Evidence。

## 4. 两阶段能力边界

### 4.1 第一阶段：注册代码工具

第一阶段只开放白名单工具，由研发在代码中注册。

首个工具：

```text
evaluate_report_quality
```

输入：

```json
{
  "report": {"...": "完整报告 JSON"},
  "sample": {"...": "可选回归样例"}
}
```

输出：

```json
{
  "success": true,
  "tool_name": "evaluate_report_quality",
  "elapsed_ms": 123,
  "result": {
    "overall_score": 78,
    "grade": "B",
    "passed": true,
    "issues": []
  }
}
```

### 4.2 第二阶段：沙箱临时代码执行

第二阶段可以评估受控沙箱，但默认关闭。

只有在满足以下条件时才考虑开放：

- 独立容器或进程隔离。
- 禁止网络访问或仅允许白名单网络。
- 只读挂载输入目录。
- 禁止删除、移动、覆盖生产文件。
- 严格超时、内存、CPU 和输出大小限制。
- 全量审计日志和人工审批。

当前 MVP 不实现任意代码执行。

## 5. 安全与治理规则

CodeAct 必须遵循以下约束：

1. 白名单注册：只能调用 registry 中登记的工具。
2. 参数结构化：输入 payload 必须是 JSON 对象。
3. 输出结构化：结果必须可 JSON 序列化。
4. 超时保护：每个工具配置 timeout，长任务后续迁移到异步队列。
5. 错误隔离：工具失败返回 `success=false`，不影响主链路继续降级。
6. 工具脱敏：前端和报告中显示业务化名称，不暴露内部脚本、供应商和实现细节。
7. 审计留痕：记录 tool_name、elapsed_ms、success、error 和结果摘要。
8. 默认关闭任意执行：`ENABLE_CODEACT_ADHOC=false`。

## 6. MVP 实施范围

已完成的第一轮代码实现范围：

- 新增 `backend/app/codeact/` 包。
- 新增 registry、runner、schemas。
- 注册 `evaluate_report_quality` 工具，复用现有 `report_quality_evaluator.py`。
- 新增配置项：
  - `ENABLE_CODEACT_TOOLS=true`
  - `ENABLE_CODEACT_ADHOC=false`
  - `CODEACT_DEFAULT_TIMEOUT_SECONDS=30`
- 新增单元测试覆盖：
  - 未知工具返回失败。
  - 报告质量工具可返回评分。
  - 结果包含 tool_name、elapsed_ms、success。

本轮不做：

- 不开放用户输入 Python 代码执行。
- 不把 CodeAct 强行接入所有 Agent。
- 不替换现有报告质量 API 和离线回归脚本。
- 不在前端暴露“代码执行”概念。

第二轮代码实现范围：

- 注册 `calculate_financial_ratios`：基于三大表 records 计算近三年核心财务指标。
- 注册 `validate_financial_statements`：校验资产负债表平衡、利润表毛利勾稽、关键科目缺失等问题。
- 注册 `validate_t1_data_package`：校验私有化前置机 T+1 数据包的 schema、日期、来源、记录和追溯字段。

这三个工具的共同约束：

- 只做确定性计算和校验，不生成授信结论。
- 输出 `metrics / issues / warnings / passed` 等结构化字段。
- 后续可由 Tool Router、报告合成层或质量评测抽屉调用。

当前财务分析链路已接入：

```text
financial_report_builder
  -> calculate_financial_ratios
  -> validate_financial_statements
  -> codeact_analysis
  -> financial_narrative_writer prompt
  -> financial_analysis_report.codeact_analysis
```

接入原则：

- 财务报告正文的表格和展示字段暂保留原有生成逻辑，避免一次性大拆。
- LLM 财务诊断 prompt 优先注入 `codeact_analysis.metrics`、`growth_metrics`、`validation_issues` 和 `validation_warnings`。
- 质量闸门允许引用 CodeAct 计算出的数字，避免把确定性计算结果误判为 LLM 编造。
- 若三大表存在 P0/P1 勾稽问题，fallback 和 LLM prompt 都会把问题写入人工复核清单。

### 财务驾驶舱支撑

财务报告生成器会将确定性抽取和 CodeAct 计算结果进一步组装为 `financial_dashboard`：

```text
financial_report_builder
  -> calculate_financial_ratios / validate_financial_statements
  -> financial_dashboard_builder
  -> financial_dashboard.charts[]
  -> Report ECharts rendering
```

该模块只负责结构化呈现，不生成新的授信结论：

- 图表数据来自已解析三大表和内部财务计算结果。
- 图表诊断只描述趋势、异常和核查方向。
- 图表引用 `codeact_financial_metric` 和 `codeact_financial_validation` evidence refs。
- 前端展示为“财务指标计算”“三大表勾稽校验”，不暴露 CodeAct 或脚本实现。

### CodeAct Evidence 化

财务链路已将 CodeAct 输出转换为正式 Evidence：

- `calculate_financial_ratios` 生成 `codeact_financial_metric` 证据。
- `validate_financial_statements` 生成 `codeact_financial_validation` 证据。
- 每条证据包含 `claim`、`source_type`、`trust_level`、`requires_manual_review` 和 `metadata.calculation_basis`。
- 报告中的 `financial_analysis_report.codeact_evidence_refs` 保存这些证据 ID。
- `report_assembler.financial_findings()` 会优先把财务诊断段落绑定到 CodeAct evidence refs，使正文级引用能展示“这句话由内部计算/校验证据支撑”。

前端展示时建议使用业务化名称：

| source_type | 展示名称 | 用户理解 |
| --- | --- | --- |
| `codeact_financial_metric` | 内部财务计算工具 | 指标由三大表确定性计算得出 |
| `codeact_financial_validation` | 内部财务校验工具 | 勾稽关系或异常信号由规则校验得出 |

不要在客户侧页面直接展示 “CodeAct” 或具体脚本名称。

### 报告自动质检闭环

报告生成后会自动调用 CodeAct 质量评测工具：

```text
synthesize_research_report
  -> apply_report_quality_gate
  -> evaluate_report_quality
  -> report.quality_evaluation / quality_score / quality_issues
  -> timeline: 报告质检
  -> export_completed_report
```

当前闭环效果：

- 每次 DeepResearch 完整报告生成后自动写入 `quality_evaluation`。
- 报告顶层提供 `quality_score`、`quality_grade`、`quality_passed`、`quality_issues`、`quality_recommendations`。
- 执行 timeline 增加“报告质检”节点，展示质量评分、P0/P1 数量和主要问题。
- `GET /tasks/{task_id}` 和 SSE state 事件会返回质量摘要字段，前端可直接用于执行页或报告页展示。
- 自动导出的报告 JSON 会携带质量评测结果，便于离线回归和案例复盘。

下一步可继续把 P0/P1 问题自动转成二轮补证任务，例如“正文级引用不足”“财务证据不足”“行业深度不足”等。

## 7. 后续演进

后续可以逐步注册更多代码工具：

| 工具 | 用途 | 优先级 |
| --- | --- | --- |
| `calculate_financial_ratios` | 基于三大表稳定计算财务指标 | 已注册 |
| `validate_financial_statements` | 校验三大表勾稽和平衡关系 | 已注册 |
| `run_report_regression` | 批量跑 10 家公司回归样例 | P1 |
| `validate_t1_data_package` | 校验私有化前置机 T+1 数据包 | 已注册 |
| `ingest_knowledge_documents` | 知识库入库和 chunk 质量检查 | P2 |
| `detect_sensitive_content` | 上传材料脱敏和敏感字段检查 | P2 |

## 8. 面试表达口径

如果面试官问“项目里很多 Python 脚本，如何让 Agent 使用起来”，推荐回答：

> 我不会直接让大模型生成任意代码执行，因为银行场景安全风险太高。我的设计是先做 Registered CodeAct，把稳定脚本注册成白名单工具，由 Planner 或 Tool Router 调用。比如报告质量评测、财务指标计算、T+1 数据包校验都可以变成 CodeAct 工具。LLM 负责规划和解释，代码工具负责确定性计算和校验，结果再进入 Evidence Store 和审计日志。等工具边界稳定后，再评估容器沙箱里的临时代码执行。

这个回答能体现三点：

- 理解 CodeAct 的价值。
- 知道金融场景不能无约束执行代码。
- 能把脚本资产产品化成可编排工具。
