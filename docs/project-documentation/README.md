# DDG-Agent 项目文档归集

本文档包用于归集智能尽调项目截至当前 MVP 阶段的产品设计、技术方案、设计决策、测试记录和问题修复记录。

文档目标不是替代代码，而是让后续继续迭代时能回答四个问题：

1. 这个产品到底解决什么业务问题。
2. 当前技术链路是如何工作的。
3. 为什么采用这些实现决策，而不是其他路线。
4. 测试过程中暴露过哪些问题，已经如何修复，仍有哪些风险。

## 文档目录

| 文档 | 内容 |
| --- | --- |
| [01 产品设计总览](./01-product-design-overview.md) | 产品定位、用户角色、核心流程、双模式尽调、页面设计原则 |
| [02 技术架构与链路方案](./02-technical-architecture.md) | 前后端架构、任务流、Agent 编排、RAG、Evidence Store、LLM 与 MCP 工具 |
| [03 单 Agent 与完整尽调实现](./03-agent-implementation.md) | 工商、财务、司法、行业、完整尽调 runner 的实现细节 |
| [04 测试记录与 Bug 修复日志](./04-testing-and-bug-log.md) | 端到端测试、功能测试、典型 Bug、修复方案与验证命令 |
| [05 设计决策日志](./05-design-decision-log.md) | 关键技术和产品决策、取舍、后续影响 |
| [06 后续路线图](./06-roadmap-and-open-risks.md) | 未完成事项、风险、下一阶段建议 |
| [07 已有文档地图](./07-existing-document-map.md) | 原有专题文档、知识库文档和当前归集文档的关系 |
| [08 面试架构答辩手册](./08-interview-architecture-playbook.md) | SaaS/私有化架构、多租户、限流、并发、网关、模型选型、Dify RAG 局限 |
| [09 DeepResearch Engine 产品设计](./09-deepresearch-engine-product-design.md) | Sequential Thinking 金融尽调研究引擎的产品目标、核心对象和体验设计 |
| [10 DeepResearch Engine 技术设计](./10-deepresearch-engine-technical-design.md) | LangGraph 状态机、MCP 接入、工具路由、Claim/GAP 生成技术方案 |
| [11 DeepResearch Engine 数据与测试方案](./11-deepresearch-engine-data-and-test-plan.md) | ResearchTask、Evidence、Claim、Gap 数据结构和测试验收标准 |
| [12 DeepResearch Engine 实施计划](./12-deepresearch-engine-implementation-plan.md) | 分阶段落地计划和本轮代码实现范围 |

## 当前 MVP 能力快照

当前系统已经形成以下最小闭环：

- 前端输入企业名称，创建任务并进入执行工作台。
- 后端快速解析用户输入，区分单 Agent 与完整尽调任务。
- 单 Agent 支持工商、财务、司法、行业四类专项分析。
- 完整尽调顺序调用专项 Agent，生成统一贷前尽调报告。
- 上市公司优先尝试公开财报和公开资料包；非上市公司支持上传三大表。
- 非上市未上传财报时进入公开资料预尽调，不阻塞整个报告。
- 财务和行业报告引入 RAG 知识和 LLM 诊断式写作，并设置质量闸门。
- Evidence Store 统一保存证据来源、置信度、可人工复核标记。
- 前端执行页和报告页展示任务状态、思考过程、报告模式、数据边界和证据。

## 重要边界

当前系统仍是 MVP，不应被理解为正式授信审批系统：

- 工商、司法、行业公开搜索依赖外部搜索工具，稳定性和权威性不足。
- DuckDuckGo MCP 在测试中多次出现 VQD 获取失败，需作为末级兜底。
- CrewAI 综合审查目前是建议性能力，不直接覆盖正式报告正文。
- 对上市公司的行业、财务公开资料抓取仍需要继续接巨潮资讯、交易所公告、研报 API 或更稳定的数据源。
- LLM 输出只能作为初稿，需要通过质量闸门、证据绑定和人工复核控制风险。
- 当前 LangGraph 架构主要面向私有化部署；若未来做 SaaS 服务，应另行评估 Dify 平台化实现。

## 面试答辩重点

如果将本项目用于面试，建议重点准备以下问题：

- SaaS 与私有化两种交付形态下，架构为何不同。
- 多租户权限、数据隔离、知识库隔离如何设计。
- LLM token 限流、预算控制、重试和降级如何做。
- 模型如何选型，什么场景用大模型、什么场景用小模型或规则。
- 完整尽调并发如何设计，哪些 Agent 可并发，哪些必须串行。
- 工商、司法、行政处罚、财报、搜索、RAG 的统一网关如何设计。
- Dify 知识库/RAG 能力有限时，如何外挂自研 RAG 和 Evidence Store。
- DeepResearch / Harness 思路下，如何从固定 Agent 编排升级为研究计划、证据需求和 Claim-Evidence 报告。

这些内容已整理到 [08 面试架构答辩手册](./08-interview-architecture-playbook.md)。

## 相关已有文档

本目录是归集层，项目中还有若干专题文档可参考：

- [上市公司财务数据接入方案](../listed-company-financial-data-integration-design.md)
- [公开资料预尽调与财报增强双模式方案](../public-pre-dd-dual-mode-implementation.md)
- [UI Design System](../UI-Design-System.md)
- [业务设计文档](../BUSINESS-DESIGN.md)
- [统一视觉 Masterplan](../UNIFIED_VISUAL_MASTERPLAN.md)
