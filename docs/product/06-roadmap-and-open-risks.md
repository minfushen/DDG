# 06 后续路线图与开放风险

## 当前优先级判断

项目已经从“演示型 Agent 应用”推进到“具备报告结构、数据边界、RAG、Evidence、LLM 诊断写作”的 MVP。下一阶段重点不是继续堆页面，而是增强数据源、知识库和报告质量。

截至当前阶段，项目已经具备 DeepResearch、Sequential Thinking、CodeAct、Evidence、质量评测和公开财报交叉校验等关键能力。下一阶段不建议立刻做“全服务容器化”或“完整 LangGraph 原生迁移”，而应先补齐 Agent 能力底座：Document Intelligence Pipeline、Runtime Skill Registry、Memory Service 和 Enhanced RAG Service。原因是 LangGraph 和 Docker 主要解决编排与交付问题，而资料解析、Skill、Memory、RAG 决定 Agent 是否真正具备专业方法论、长期经验和检索增强能力。

推荐总体顺序：

```text
Structured Financial Data Layer v1
-> 财务诊断 Writer 重构 + 财务九宫格和表格展示优化
-> 巨潮年报 PDF / 交易所公告 PDF / 网页公告新闻研报摘要处理闭环
-> Document Intelligence Pipeline + Agent Capability Layer v1
-> LangGraph interrupt/checkpoint/resume 原生迁移
-> Docker Compose 私有化交付
-> 服务化拆分和多场景 Agent 平台
```

详细方案见 [23 Structured Financial Data Layer v1 实施计划](./23-structured-financial-data-layer-v1-plan.md)、[20 Agent Capability Layer v1 产品迭代方案](./20-agent-capability-layer-v1-roadmap.md) 和 [21 文档智能解析与生产级 RAG 设计](./21-document-intelligence-and-rag-design.md)。

## P0：Structured Financial Data Layer v1

目标：优先利用 AKShare、东方财富等结构化财务数据源，建立统一财务数据包、跨源校验、关键指标计算和财务诊断输入层，快速提升财务分析和交叉验证质量。

下一步：

- 定义 `FinancialStatementPackage`，统一三大表、期间、单位、口径、来源、置信度和 evidence refs。
- 金额类计算层统一用元，展示层自动转亿元/万元。
- 补齐关键字段：营业收入、营业成本、毛利率、归母净利润、扣非净利润、经营现金流、短期借款、应收账款、存货、现金短债比、EBITDA 利息保障倍数、周转天数等。
- 对 AKShare 和东方财富做字段级交叉校验，差异超过阈值生成 evidence gap 或人工复核标记。
- 财务 writer 固定输出收入与利润、资产负债、盈利质量与营运效率、偿债能力与异常信号、数据边界与核查动作五个小节。
- 财务 dashboard 和二维表只消费结构化包，避免前端临时猜字段和误译指标。

第二阶段接入巨潮年报 PDF、交易所公告 PDF、网页公告/新闻/研报摘要处理闭环，用于解释财务指标变化、补充交叉验证和提升行业分析质量。

详细方案见 [23 Structured Financial Data Layer v1 实施计划](./23-structured-financial-data-layer-v1-plan.md)。

## P0：Document Intelligence Pipeline

目标：把上传资料、公告 PDF、网页、扫描件、Excel 财务表和私有化 T+1 数据包统一转换为可入库、可检索、可引用、可复核的结构化资料。

下一步：

- 定义 `ParsedDocument`、`DocumentBlock`、`ParsedTable` 和解析质量 `quality` schema。
- 新增 Document Parser Router，通过文件类型、MIME 和 magic bytes 路由 PDF、Word、Excel、HTML、图片、JSON/CSV 数据包。
- 财务 Excel/PDF 专项解析支持多表切分、单位继承、合并/母公司口径识别、年份列识别和三大表标准字段映射。
- Chunk Builder 支持语义切片、父子切片、表格整切、图片与 caption 绑定。
- 低置信 OCR、表头缺失、字段冲突、跨源财报差异等进入 Evidence Gap 或人工复核队列。
- 记录 parser、版本、耗时、失败原因、降级链路和人工复核状态。

简历表达：

> 参与规划面向 RAG/Agent 的文档智能解析管线，围绕 PDF、Excel、扫描件、网页和客户前置机数据包，设计 Parser 路由、统一中间 Schema、表格整切、置信度校验、人工复核和降级机制，提升知识入库质量与报告生成稳定性。

## P0：Agent Capability Layer v1

目标：把 DDG-Agent 从“工具链编排型 Agent”升级为“可加载方法论、可沉淀经验、可增强检索的专业尽调工作台”。

### 1. Runtime Skill Registry

现状：

- 项目已初步引入 `deep_research`、`loan_due_diligence`、`financial_analysis` 等 Runtime Skill。
- Planner 已能读取 evidence blueprint，但专项节点对 Skill 的动态注入仍需进一步产品化。

下一步：

- 建立统一 Skill Registry，管理 `SKILL.md`、`references/*.json`、质量规则和节点输出契约。
- Planner 根据任务类型、报告模式、行业分类动态选择 Skill。
- 财务、行业、司法、工商专项节点执行前注入对应 Skill。
- Skill 加载失败时回退默认规则，不阻塞任务。

简历表达：

> 设计 Runtime Skill Registry，将贷前尽调、DeepResearch、财务分析等领域方法论抽象为可运行 Skill，使 Planner 从“问题拆解”升级为“章节-证据需求-工具路线-质量规则”的结构化计划。

### 2. Memory Service

现状：

- 用户偏好、报告 bad case、人工复核结论和同一公司历史任务尚未系统沉淀。

下一步：

- 预留 `MemoryService` 抽象接口，不直接绑定具体供应商。
- 支持写入用户偏好、项目经验、报告 bad case、公司历史和人工复核结论。
- 支持 Planner、专项 writer、质量评测器按任务上下文检索记忆。
- SaaS/PoC 可评估 mem0；私有化保留 PostgreSQL/向量库/客户内网记忆服务替换能力。

简历表达：

> 规划 Agent Memory 机制，将用户偏好、报告质检 bad case、人工复核结论和企业历史分析沉淀为可检索记忆，为持续优化报告质量和个性化尽调体验提供基础。

### 3. Enhanced RAG Service

现状：

- 当前 RAG 已支持向量检索和关键词 fallback，但仍偏基础检索。

下一步：

- 引入 Query Rewrite、Hybrid Retrieval、Cross-Encoder Rerank、Rule Rerank 和 Evidence-aware RAG。
- 按 `financial`、`industry`、`credit_policy`、`case_study`、`legal`、`user_memory`、`company_history` 做知识域隔离。
- 建设向量索引、BM25/关键词索引、元数据索引，关系密集场景再评估 Graph RAG。
- 建设 RAG 评估集，覆盖 Context Recall、Context Precision、Faithfulness 和 Answer Relevance。
- 低置信知识只作核查方向，不直接支撑强结论。
- SaaS 版本可采用 Dify workflow + 外挂 Enhanced RAG；私有化版本部署本地 Enhanced RAG。

简历表达：

> 设计 Enhanced RAG Service，针对金融尽调场景补齐查询改写、混合召回、重排序、知识域隔离、证据级引用和 RAG 评估集，解决通用知识库 RAG 难以支撑专业报告的问题。

### 4. Capability Context Builder

下一步：

- 将 Skill、Memory、RAG、CodeAct 和 Evidence 统一组装为节点上下文。
- Planner、财务节点、行业节点、司法节点和 Synthesizer 分别消费不同上下文。
- 按 token 预算做摘要、去重和裁剪，避免 prompt 过长。

简历表达：

> 规划 Capability Context Builder，将领域 Skill、历史记忆、RAG 知识和确定性工具结果统一注入 Agent 节点，提升计划生成、专项诊断和报告装配的一致性。

## P0：稳定任务执行和外部搜索

### 1. 移除不稳定 DuckDuckGo MCP（已完成）

现状：

- DuckDuckGo MCP 多次出现 `Failed to get the VQD`。

建议：

- 从默认配置和 MCP provider 列表中移除 DuckDuckGo。
- 搜索顺序保留 Bocha、Exa/Tavily、RAG 和结构化数据源。
- 后续不再把 DuckDuckGo 作为兜底通道，避免 VQD 错误拖慢任务。

### 2. 任务状态持久化

现状：

- 任务存在后端内存中。

建议：

- 引入 SQLite/PostgreSQL 或 Redis 存储任务状态、timeline、evidence、report。
- 支持服务重启后恢复任务。

### 3. 私有化数据源适配层

现状：

- 当前工具层仍较多依赖公网搜索和公开 API。
- 私有化客户环境中通常无法直接访问外网。

建议：

- 新增统一 Data Source Gateway，屏蔽公网搜索、客户自购 API、内网数据中台之间的差异。
- 工商、司法、行政处罚、征信等高成本接口支持按需调用、缓存和费用统计。
- 报告中区分“权威内网数据源”“商业 API”“公开搜索线索”“人工上传材料”。
- 私有化部署默认关闭公网搜索工具，改用客户授权数据源和本地 RAG。

### 4. 私有化 T+1 数据前置机方案

私有化项目中，最现实的限制是 Agent 运行环境通常无法直接访问公网搜索工具和外部 SaaS API。即使客户允许访问，也会涉及网络安全、审计、数据出域、接口成本和供应商白名单审批。因此不能假设生产环境可以直接调用 Bocha、Exa、Tavily、搜索 MCP 或公开网站。

更稳妥的妥协方案是：客户侧每日 T+1 将外部搜索和自购数据源结果推送到一个“数据前置机”，Agent 不直接出网，而是通过内网 MCP/Tools 从前置机拉取标准化数据包。

推荐架构：

```text
外部数据采集区/客户数据供应商
  -> T+1 数据推送任务
  -> 数据前置机 Landing Zone
  -> 标准化/去重/脱敏/签名
  -> 内网 Data Gateway / MCP Server
  -> Agent Tool Router
  -> Evidence Store
  -> 报告正文级引用
```

前置机承载的数据类型：

| 数据包 | 内容 | 更新频率 | 典型来源 |
| --- | --- | --- | --- |
| 企业工商包 | 登记信息、股东、变更、异常经营、股权质押、对外投资 | T+1 或按客户授权 | 客户自购工商数据、内部主数据 |
| 司法合规包 | 裁判、执行、失信、行政处罚、监管处罚、重大违法 | T+1 | 客户自购司法数据、监管公告供应商 |
| 舆情与公告包 | 上市公告、重大诉讼、担保质押、监管问询、新闻舆情 | T+1 | 交易所公告、巨潮、商业资讯源 |
| 财务公开包 | 上市公司三大表、主营构成、年报经营讨论、财务摘要 | T+1/公告后 | 金融数据供应商、公告解析服务 |
| 行业资料包 | 行业景气、政策、研报摘要、价格指数、同业指标 | T+1/周更/月更 | 研报服务、行业协会、内部研究 |

前置机数据建议采用“原始区 + 标准区 + 索引区”三层结构：

- `raw/`：保留原始供应商文件或接口响应，便于审计追溯。
- `standardized/`：按统一 schema 输出 JSON/Parquet/CSV，供 Agent 工具读取。
- `index/`：企业名、统一社会信用代码、股票代码、日期、数据类型、版本号等索引。

标准数据包字段建议：

```json
{
  "package_id": "pkg_20260614_0001",
  "subject_name": "某某股份有限公司",
  "subject_keys": {
    "credit_code": "...",
    "stock_code": "...",
    "aliases": ["..."]
  },
  "data_domain": "business|legal|financial|industry|news",
  "as_of_date": "2026-06-13",
  "source_name": "客户授权数据源",
  "source_type": "customer_authorized_data_feed",
  "trust_level": "high",
  "license_scope": "仅限本客户内网尽调用途",
  "records": [],
  "raw_refs": [],
  "checksum": "...",
  "ingested_at": "2026-06-14T02:00:00"
}
```

Agent 侧接入方式：

1. 前置机部署轻量 MCP Server 或 FastAPI Tool Server。
2. Tool Router 将“公开搜索工具”替换为“前置机数据检索工具”。
3. Planner 生成证据需求时仍使用业务语言，例如“核查工商变更”“核查行政处罚”“获取近三年财务数据”。
4. Tool Router 根据私有化配置路由到前置机，不暴露公网工具实现。
5. 返回结果统一转成 Evidence Store，`source_type` 标记为 `customer_authorized_data_feed` 或 `internal_front_machine_feed`。
6. 报告中展示“客户授权数据源 / T+1 数据包 / 截止日期 / 需人工复核边界”。

关键产品边界：

- T+1 数据适合作为“预尽调”和“批量筛查”的主要数据源。
- 对审批当天发生的重大事项，仍需配置人工补充、权威系统实时查询或例外审批流程。
- 报告必须标明 `as_of_date`，避免用户误以为数据实时。
- 对高成本接口，前置机可统一做缓存、批处理和费用统计，Agent 不直接按任务实时调用。
- 前置机数据必须保留原始来源引用和 checksum，满足审计追溯。

与 SaaS/PoC 搜索工具的关系：

- PoC/SaaS：可以直接调用公开搜索和商业 API，强调覆盖面和实时性。
- 私有化生产：优先读取 T+1 前置机数据包，公网搜索默认关闭或仅在隔离区运行。
- 同一套 Agent 逻辑通过 Data Gateway 适配不同数据源，不应把搜索供应商写死在业务 Agent 中。

该方案的价值：

- 满足银行/大型客户内网安全要求。
- 避免 Agent 节点直接出网。
- 降低工商、司法、公告、研报等高成本接口的实时调用压力。
- 保持 Evidence、报告引用和质量评测逻辑一致。
- 让同一套产品同时适配 PoC/SaaS 和私有化交付。

## P1：增强真实数据源

### 1. 上市公司财务数据

建议接入：

- 原始披露源：巨潮资讯公告、沪深北交易所公告、上市公司公告原文。
- 机构级数据库：Wind、CSMAR 等，用于正式项目中的标准化财报、行业对标和估值数据。
- 开源量化数据包：AKShare、Tushare，用于 POC、个人量化开发和低成本兜底校验。
- 财经网站与投研工具：东方财富、同花顺、萝卜投研、理杏仁等，用于基本面摘要、估值分析、图表和交叉验证。

目标：

- 年报经营讨论。
- 主营构成。
- 近三年三大表。
- 诉讼公告。
- 担保质押。
- 行业地位和研报摘要。

优先级原则：正式授信报告以巨潮/交易所原始披露和客户授权机构数据库为高可信主源；东方财富等公开接口可作为 MVP 主链路和补充验证；AKShare/Tushare 适合作为开发及兜底；萝卜投研、理杏仁等可视化工具用于辅助理解和交叉验证，不应单独承担正式结论。

### 2. 工商权威数据

建议接入：

- 国家企业信用信息公示系统可用通道。
- 企查查/天眼查等商业 API。
- 银行内部工商数据源。

目标字段：

- 企业名称、统一社会信用代码、法人、注册资本、成立日期、经营状态。
- 股东结构、实际控制人、工商变更。
- 对外投资、分支机构、异常经营、股权质押。

### 3. 司法权威数据

建议接入：

- 裁判文书网可用通道。
- 中国执行信息公开网。
- 信用中国。
- 行政处罚公告源。

目标：

- 裁判案件数量和类型。
- 被执行和失信信息。
- 行政处罚和重大违法线索。
- 涉诉金额、案由、时间和状态。

## P1：完善 RAG 知识库

用户计划补充内部资料：

- 长沙银行内部授信制度。
- 内部行业准入、限入、禁入政策。
- 内部客户评级模型。
- 内部额度测算规则。
- 内部贷后检查模板。
- 内部审查审批话术。
- 脱敏真实客户经理尽调报告。
- 内部不良案例复盘。

建议处理方式：

- 所有内部资料先脱敏。
- 按 `knowledge_base` 目录分类入库。
- 每份资料加 front matter：category、source_label、disclaimer、tags。
- RAG 检索结果在报告中显示“内部制度/同业参考/案例复盘”等来源类型。
- 入库前先经过 Document Intelligence Pipeline，确保 PDF、Word、Excel、扫描件和网页材料都转换为统一 block。
- 知识切片按资料价值分层：普通制度用语义切片，年报/尽调报告用父子切片，高价值授信规则可抽命题切片。
- 检索层采用向量 + BM25 混合召回，重排后再进入生成节点。
- 建设 RAG 评估集和消融实验流程，避免靠主观感觉调整 chunk、embedding、rerank 和 prompt。

## P1：报告质量提升

## P1：CodeAct 代码工具化

现状：

- 项目中已经沉淀了报告质量评测、离线回归、知识库入库、财务解析等 Python 能力。
- 这些能力目前主要由开发者手工运行，尚未完全纳入 Agent 编排链路。

建议：

- 采用 Registered CodeAct，把稳定脚本注册成白名单代码工具。
- 第一阶段注册报告质量评测工具，后续扩展财务指标计算、三大表勾稽校验、T+1 前置机数据包校验和知识库入库校验。
- CodeAct 输出统一 JSON，可进入 Evidence Store、任务审计日志或质量评测抽屉。
- 任意代码执行保持关闭，只有在容器沙箱、资源限制、只读挂载和审计机制成熟后再评估。

价值：

- 让 LLM 负责规划和诊断表达，让代码工具负责确定性计算和校验。
- 把开发脚本沉淀为产品能力，而不是散落在命令行里。
- 为私有化交付中的离线批处理、数据包校验和运维检查提供标准工具接口。

详细设计见 [16 CodeAct 代码即工具产品与技术设计](./16-codeact-product-technical-design.md)。

### 财务报告

下一步：

- 引入更多财务勾稽规则。
- 支持行业基准注入。
- 对应收、存货、CAPEX、研发资本化、政府补助、或有负债做专项诊断。
- 建立“劣质生成 vs 专业改写”的 few-shot 样本库。

### 行业报告

下一步：

- 按子赛道建立 KPI 字典。
- 半导体、锂电池、建筑工程、食品加工、贸易等行业先做专题规则。
- 行业报告引入关键假设清单。
- 每个风险点至少绑定 1 个证据、1 个规则和 1 个核查动作。

### 完整报告

下一步：

- 接近银行贷前尽调报告体例。
- 增加“调查对象基本情况”“经营分析”“财务分析”“风险事项”“授信建议”“贷后监控”正式章节。
- 支持导出 Word/PDF。

## P2：CrewAI 能力恢复

当前 CrewAI 的问题：

- 限流风险。
- 输出不可控。
- 自由文本容易污染正式报告。

建议恢复路径：

1. CrewAI 只处理结构化输入摘要。
2. 输出严格 JSON schema。
3. 增加质量闸门。
4. 不通过时保留 advisory，不覆盖正文。
5. 逐步引入多 Agent 互审，例如财务 Agent 审行业假设、行业 Agent 审财务增长合理性。

## P2：SaaS 版本 Dify 化评估

如果项目未来从私有化方案转为 SaaS 服务，应单独做 Dify 化评估。

评估内容：

- 将当前 LangGraph 编排迁移为 Dify workflow 的成本。
- 将工商、财务、司法、行业 Agent 封装为 Dify 工具或子流程的方式。
- 将 RAG 知识库迁移到 Dify 知识库或外部向量服务的方式。
- Evidence Store、报告模板、成本计费和租户隔离是否仍需自研后端承载。
- SaaS 中公网搜索、商业 API 和用户上传材料的证据可信度分级。

初步判断：

- 私有化 AI 能力层：LangGraph/FastAPI 更合适，强调可控、可审计、可接内网数据源。
- SaaS 轻量编排：Dify 更可能合适，强调快速编排、运营配置、多租户知识库和低运维成本。
- 企业级重后台：Spring Boot / Spring Cloud Alibaba 更合适，强调多租户权限、任务中心、报告管理、审批流、配置中心、审计日志、WebSocket 推送和第三方系统集成。
- 最终平台形态不应二选一，而应采用 Spring Boot 企业后台 + FastAPI AI 能力服务的双后端分工；Spring AI Alibaba 用于 Java 侧模型接入和轻量 AI 能力，复杂 DeepResearch Engine 继续保留在 FastAPI。

## P2：Docker 化与平台底座工程化

本项目后续不应只被理解为“贷前尽调应用”，更适合演进为一套 DeepResearch / Agent Workbench 底座。贷前尽调只是第一个业务场景，后续可以衔接法律尽调、投研分析、竞品分析、招投标分析、客户准入审查等多类研究型任务。

从能力拆分看，当前单体内已经隐含了若干可独立服务化的模块：

| 能力模块 | 后续服务形态 | 职责 |
| --- | --- | --- |
| Plan Agent | `planner-service` | 将用户目标拆解为研究计划、证据需求、工具路线和 HITL 节点 |
| Tool Router / Data Gateway | `tool-gateway-service` | 统一封装搜索、工商、司法、财报、公告、客户内网数据源和 MCP 工具 |
| Evidence Store | `evidence-service` | 管理证据、来源、置信度、正文级引用和 Claim-Evidence 关系 |
| AI Writing / Synthesizer | `writing-service` | 将结构化证据和专项结果装配为贷前、法律、投研、竞品等报告 |
| RAG / Knowledge | `knowledge-service` | 管理行业知识、授信制度、法律法规、投研框架和分析模板 |
| Task Orchestrator | `orchestrator-service` | 管理任务状态、checkpoint、resume、HITL、并发、重试和降级 |
| Frontend Workbench | `frontend` | 统一任务创建、执行过程、人机确认、报告查看和质量评测 |

因此，Docker 镜像化不是上线前的简单运维动作，而是后续架构拆分和私有化交付的前置能力。建议演进路线如下：

```text
MVP 单体
-> 模块化单体
-> Docker Compose 单机私有化交付
-> Spring Boot 企业后台 + FastAPI AI Service 双后端分工
-> 服务化拆分
-> 多场景 Agent 平台
```

### 阶段 1：模块化单体

当前优先目标仍是稳定业务质量，而不是为了架构而拆服务。

重点工作：

- 稳定 10 家上市公司报告质量回归。
- 完善报告质量评测台。
- 自动保存报告 JSON，支持离线批量回归。
- 完善工具调用 trace、耗时、失败率和 evidence coverage。
- 保持 Plan、Evidence、Tool、Writing 等模块边界清晰。

### 阶段 2：Docker Compose 单机部署

当报告质量和任务链路稳定后，优先做 Compose 级封装，而不是直接上 Kubernetes。

建议服务：

- `frontend`：React/Vite 静态资源或 Nginx 承载。
- `backend`：FastAPI + LangGraph DeepResearch Engine。
- `postgres`：替代 SQLite 存储任务、报告、证据、用户和租户数据。
- `redis`：任务队列、限流、缓存、SSE/事件状态。
- `vector-db`：Chroma 或可替换向量库。
- `browser-runtime`：可选，用于网页正文解析和抓取能力。

Compose 化目标：

- 固化 Python/Node/浏览器运行环境，降低本地和私有化部署差异。
- 支持一键启动演示环境。
- 为客户私有化部署提供最小可交付包。
- 为后续服务拆分提供网络、配置、日志和数据卷基础。

### 阶段 3：服务化拆分

只有当各模块输入输出稳定后，再逐步拆成微服务。优先拆高复用、高成本、强边界模块：

1. `tool-gateway-service`：统一管理外部数据源、客户内网 API、调用成本和缓存。
2. `knowledge-service`：统一管理知识库入库、检索、重排和知识域隔离。
3. `writing-service`：统一提供报告写作、模板装配、质量闸门和多业务报告输出。
4. `planner-service`：抽象研究计划生成和人机确认节点，支持不同业务场景复用。
5. `evidence-service`：沉淀跨场景证据模型、证据引用和审计能力。

拆分原则：

- 先按业务边界拆，不按技术炫技拆。
- 先拆最可能被多个业务场景复用的能力。
- 每拆一个服务都必须具备独立测试、独立镜像、独立配置和清晰 API contract。
- 任务编排层保留对 partial result、fallback 和人工确认的控制权。

### 阶段 4：企业级平台化：Spring Boot + FastAPI 双后端分工

当产品从 MVP/PoC 演进为企业级 AI 写作平台时，后台能力会明显变重：用户租户、组织权限、任务中心、审批流、报告管理、配置中心、审计日志、移动端/第三方系统接入。这些能力更适合由 Spring Boot / Spring Cloud Alibaba 承接，而不是继续让 FastAPI 承担所有业务后台，也不建议为了传统 Python Web 框架要求把 FastAPI 迁移到 Django。

推荐架构：

```text
Web / Mobile / Third-party Systems
-> Spring Boot Enterprise Backend
   -> 用户 / 租户 / 权限 / 任务 / 报告 / 审批 / 审计 / 配置 / WebSocket
   -> Spring AI Alibaba 模型接入和轻量 AI 能力
-> FastAPI AI Service
   -> LangGraph / DeepResearch / Document Intelligence / Enhanced RAG / Evidence / Report / Quality Eval
```

通信方式：

- REST / OpenFeign / WebClient：任务创建、结果查询、文档解析、RAG 检索、报告生成、质量评测。
- MQ：批量文档解析、长耗时报告生成、离线质量评测、批量 RAG 入库。
- Redis Stream / MQ + WebSocket：FastAPI 产生 AI 执行事件，Spring Boot 统一向 Web/移动端推送。

Spring Boot 侧建议主表：

- `sys_user`、`sys_role`、`sys_tenant`、`sys_org`。
- `ai_task`、`ai_task_event`、`ai_document`、`ai_report`、`ai_report_version`。
- `ai_evidence`、`ai_quality_eval`、`ai_model_config`、`ai_tool_config`、`ai_datasource_config`、`audit_log`。

该阶段目标不是替换现有 FastAPI AI 能力，而是把 FastAPI 收敛为 AI Service，由 Spring Boot 承接企业后台和系统集成。

详细设计见 [22 Spring Boot 企业后台 + FastAPI AI 能力服务架构](./22-springboot-fastapi-hybrid-architecture.md)。

### 阶段 5：多场景 Agent 平台

当平台底座稳定后，可以通过不同领域知识库、工具配置、报告模板和评测 Rubric 扩展新场景：

| 场景 | 复用能力 | 差异化资产 |
| --- | --- | --- |
| 贷前尽调 | Plan、Evidence、RAG、Writing、HITL | 授信制度、财务规则、工商司法数据源、贷前报告模板 |
| 法律尽调 | Plan、Evidence、Writing、Tool Gateway | 法律法规、合同审查规则、裁判/处罚数据源、法律尽调报告模板 |
| 投研分析 | Plan、RAG、财报/公告工具、Writing | 行业研究框架、财务模型、研报摘要、投研报告模板 |
| 竞品分析 | Web Search、RAG、Evidence、Writing | 竞品资料库、产品功能框架、市场分析模板 |

平台化后的核心产品定位是：

> 以 Plan-Execute DeepResearch 为核心，以 Evidence Store 和 AI Writing 为底座，面向金融、法律、投研和商业分析的多场景 Agent Workbench。

### Roadmap 判断

当前不建议立刻拆成多个微服务。更稳妥的顺序是：

1. 先把当前 LangGraph DeepResearch 单体打磨成“可评测、可观测、可导出、可部署”的模块化单体。
2. 再用 Docker Compose 固化运行环境，解决私有化交付和演示部署问题。
3. 如果产品进入重后台和企业集成阶段，引入 Spring Boot 企业后台，FastAPI 收敛为 AI Service。
4. 等 Plan、Evidence、Tool、Writing 的接口稳定后，再拆微服务。
5. 最后通过知识库、工具链和报告模板扩展到贷前尽调以外的业务场景。

这一演进逻辑也适合用于面试答辩：不是一上来为了架构而架构，而是按业务成熟度从 MVP 单体逐步演进到多场景 Agent 平台。

## Sequential Thinking Remote MCP 路线

DeepResearch Engine 下一阶段需要让计划节点更像研究智能体，而不是只在计划生成后做一次复核。Sequential Thinking 的定位调整为“公开化研究思考状态机”：记录研究启动、计划扩展和自我修订，再把摘要化结果注入 LLM Planner。

近期落地顺序：

1. 新增 `services/sequential-thinking-wrapper`，以 Streamable HTTP 暴露 `sequentialthinking` 工具，默认监听 `http://127.0.0.1:38001/mcp`。
2. 后端新增 `SEQUENTIAL_THINKING_TRANSPORT=stdio|streamable_http` 和 `SEQUENTIAL_THINKING_REMOTE_URL`。
3. DeepResearch `prepare_plan` 节点从“LLM 生成计划后 MCP review”升级为“Sequential thought loop + LLM plan generation”。
4. 前端执行页后续展示“研究思考链”分段，重点展示计划、扩展、修订和人工确认点。
5. 私有化部署时把 wrapper 纳入 Docker Compose，并按 task/tenant 增加 `session_id` 隔离。

该方向的设计文档见 [17 Sequential Thinking Remote MCP 设计文档](./17-sequential-thinking-remote-mcp-design.md)。

## P2：前端增强

建议：

- 报告页支持证据侧栏。
- 风险点旁展示 rule_id、evidence_id、confidence。
- 支持下载报告。
- 支持上传补充材料后局部刷新章节。
- 支持任务日志查看，方便没有后台运维监控时排查。

## 开放风险

| 风险 | 影响 | 缓解方式 |
| --- | --- | --- |
| 外部公开搜索不稳定 | 工商、司法、行业线索缺失 | 接正式 API，搜索只作兜底 |
| LLM 生成幻觉 | 报告出现错误结论 | 结构化输入、质量闸门、证据绑定、fallback |
| 内部知识缺失 | 报告专业度不足 | 持续补充 RAG 知识库和案例 |
| 任务状态内存存储 | 服务重启丢任务 | 引入数据库或 Redis |
| 凭证泄露 | 安全风险 | `.env` 管理、文档不记录真实 key、定期轮换 |
| 前端 mock 遗留 | 用户误以为是真实数据 | 清理 mock 展示，报告只展示后端真实字段 |

## 建议下一步

最建议的下一步顺序：

1. Document Intelligence Pipeline：统一资料解析、ParsedDocument schema、财务表专项解析、低置信复核和 parser 可观测性。
2. Agent Capability Layer v1：Runtime Skill Registry、MemoryService 抽象、Enhanced RAG Service 和 Capability Context Builder。
3. Skill-aware Planner：让计划生成从“研究问题列表”升级为“章节-证据需求-工具路线-质量规则”。
4. Specialist Skill Injection：财务、行业、司法、工商节点按领域 Skill 动态注入方法论和输出契约。
5. Memory 最小闭环：沉淀用户偏好、报告 bad case、人工复核结论和公司历史任务。
6. Enhanced RAG 最小闭环：查询改写、混合召回、重排序、知识域隔离、evidence-aware 引用和 RAG 评估集。
7. LangGraph 原生迁移：待节点输入输出稳定后，再接 interrupt/checkpoint/resume。
8. Docker Compose 私有化交付：能力接口稳定后再固化 backend、frontend、数据库、向量库、Sequential Thinking wrapper 和前置机数据网关。
9. Spring Boot 企业后台路线评估：当出现多租户权限、任务中心、审批流、报告管理、审计日志和第三方系统集成需求时，引入 Spring Boot / Spring Cloud Alibaba，FastAPI 收敛为 AI Service。

面试表达建议：

> 我没有急着先做容器化、完整 LangGraph 迁移或 Java 重后台重构，而是先规划 Document Intelligence 和 Agent Capability Layer，因为 LangGraph 解决流程控制，Docker 解决交付环境，Spring Boot 解决企业后台，而资料解析、Skill、Memory、Enhanced RAG 决定 Agent 是否真正具备专业能力。我的路线是先把资料入口和能力层接口稳定，再把这些能力映射成 LangGraph 节点；当项目进入多租户、审批、审计和系统集成阶段，再引入 Spring Boot 企业后台，FastAPI 收敛为 AI Service。
