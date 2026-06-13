# 03 单 Agent 与完整尽调实现

## Agent 总览

当前系统包含四个专项 Agent 和一个完整尽调合成流程。

| Agent | 入口 | 当前能力 | 主要输出 |
| --- | --- | --- | --- |
| 工商 Agent | `run_business_agent` | 搜索/工商上下文、基础工商风险线索 | 工商报告、timeline、evidence |
| 财务 Agent | `run_financial_agent` / `run_financial_agent_with_uploaded_data` | 上市公司公开财报、非上市上传三大表、财务诊断写作 | 财务分析报告 |
| 司法 Agent | `run_legal_agent` | 公开搜索司法线索，失败时明确兜底 | 司法风险报告 |
| 行业 Agent | `run_industry_agent` | 行业代码匹配、LLM 裁判、RAG、行业诊断写作 | 行业分析报告 |
| 完整尽调 | `run_full_due_diligence` | 顺序组合四个专项并生成统一报告 | full_due_diligence_report |

## 财务 Agent

### 数据来源

财务 Agent 支持三类数据来源：

1. 上市公司公开财报。
2. 用户上传三大表 Excel/CSV。
3. 非上市未上传时，公开财务线索预审。

早期问题：

- 财务 Agent 使用模拟数据，导致上市公司报告可信度不足。
- 报告中毛利率、净利率、资产负债率、现金流等指标不是来自上传文件。
- 兜底文案只分析最新一年，缺少近三年趋势。

当前实现：

- `financial_report_builder.py` 从三大表中抽取重点科目。
- 支持营业收入、营业成本、毛利润、营业利润、利润总额、净利润、货币资金、应收账款、存货、短期借款、应付票据、应付账款、实收资本、资本公积、未分配利润、经营/投资/筹资现金流等。
- 计算近三年指标和衍生指标：收入 CAGR、应收/营收、资产负债率变化、流动比率变化、经营现金流/净利润等。
- `financial_knowledge_context.py` 动态检索财务异常规则。
- `financial_narrative_writer.py` 调用 LLM 生成诊断式财务文本。

### 财务诊断写作

LLM 输出结构固定为三类：

1. 盈利质量与成长性风险。
2. 资产真实性与营运效率风险。
3. 资本结构与偿债能力风险。

质量闸门包括：

- 禁止使用“销售额为”“资产持有率”“牛奶准入”等错误或污染表达。
- 禁止输出未在输入数据中出现的数字。
- 必须分析近三年趋势。
- 必须包含数据边界和人工复核提示。
- 必须输出 `phenomenon`、`driver`、`risk_level`、`verification_action`。

设计决策：

- 代码负责抽取和计算指标，LLM 负责诊断表达。
- LLM 输出必须通过质量闸门，否则使用 fallback。
- 前端报告页展示 `LLM生成` 或 `兜底模板`，避免用户误判。

## 行业 Agent

### 行业识别

主要文件：

- `industry_classifier_tool.py`
- `industry_llm_classifier.py`
- `industry_code4.json`

早期问题：

- 士兰微被识别为“贸易/进出口”，原因是经营范围中包含“货物进出口、技术进出口”等噪声。

当前策略：

- 先用规则从四级行业代码库召回候选。
- 注入上市公司映射和公开资料上下文。
- 使用轻量 LLM 对候选行业做语义裁判。
- 输出 `classification_source`、`llm_reason`、`ignored_noise`。

验证结果：

- 士兰微稳定识别为 `3973 集成电路制造`。
- 行业路径为 `制造业 > 计算机、通信和其他电子设备制造业 > 电子器件制造 > 集成电路制造`。

### 行业知识和诊断

主要文件：

- `industry_knowledge_context.py`
- `industry_diagnostic_writer.py`
- `industry_report_builder.py`

行业分析不再只输出“政策环境、竞争格局、行业风险”这种模板内容，而是输出：

- 行业定位与周期判断。
- 技术/产品/竞争格局风险。
- 产业链议价能力与经营韧性风险。
- 行业 KPI 与授信审查适配风险。

质量闸门包括：

- 禁止空泛表达：竞争激烈、政策利好、市场空间广阔、技术更新快、人才重要、估值偏高等。
- 每个诊断项必须包含现状锚定、风险实质、核查要点。
- 必须引用 rule_id 或 evidence/source_id。
- 缺失数据必须写 `[需补充：...]`，不能编造良率、市场份额、订单覆盖率。

半导体专项 fallback：

- 技术节点、产品结构、产能利用风险。
- 产业链供需、库存周期与议价能力风险。
- 资本开支、研发投入与偿债压力传导风险。

## 工商 Agent

工商 Agent 的设计目标是获取企业基础信息和治理风险线索。

当前数据通道：

- 企业工商专项 API 配置预留。
- 搜索工具兜底。
- 上市公司公开资料辅助。

关键边界：

- 国家企业信用信息公示系统没有稳定开放 API 时，搜索只能作为线索。
- 报告需要提示人工复核国家企业信用信息公示系统、上市公告、工商变更记录。

后续建议：

- 接入企查查、天眼查或银行内部工商数据源。
- 将工商变更、股权质押、对外投资、异常经营名录作为结构化字段。

## 司法 Agent

司法 Agent 与工商 Agent 类似，存在权威数据源难以结构化访问的问题。

当前策略：

- 使用公开搜索获取裁判、执行、失信、行政处罚线索。
- 搜索失败或数据不稳定时，不展示模拟案件，只列为人工核验事项。
- Evidence 中标记来源和可信度。

关键边界：

- 裁判文书网没有稳定公开 API。
- 搜索结果可能漏报或误报。
- 正式授信前必须人工核验裁判文书、执行信息公开网、信用中国、行政处罚公告等权威渠道。

## 完整尽调报告

主要文件：

- `full_due_diligence_runner.py`
- `full_report_builder.py`

完整报告输入：

- 四个专项报告。
- Evidence Store 证据。
- 报告模式。
- 财务数据状态。
- 可选 CrewAI 综合审查结果。

报告结构：

- `report_mode`：`public_pre_dd` 或 `financial_enhanced_dd`。
- `risk_rating`、`risk_score`。
- `executive_summary`。
- `risk_dimensions`。
- `cross_findings`。
- `credit_decision`。
- `report_chapters`。
- `evidence_docs`。
- `data_boundary`。
- `required_documents`。

设计原则：

- 完整尽调先保证规则和证据可控。
- CrewAI 综合审查暂不覆盖正文，只保留 advisory。
- 公开资料预尽调不直接给正式额度。
- 报告中必须体现数据边界和待补充材料。

## 上传财报恢复流程

当非上市完整尽调缺少财报时：

1. 系统先跑工商、司法、行业。
2. 财务进入公开资料预审或等待上传。
3. 用户上传三大表。
4. 后端调用 `resume_financial_task_with_uploaded_data()`。
5. 沿用已有完整尽调上下文，只补跑财务。
6. 重新生成完整报告。

该设计避免用户上传后从头跑一遍所有 Agent。

