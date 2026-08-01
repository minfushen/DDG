# 07 已有文档地图

本文件用于说明项目中已有文档与本次归集文档之间的关系，避免后续维护时不知道该读哪一份。

## 本次归集文档

| 文档 | 定位 | 维护建议 |
| --- | --- | --- |
| `README.md` | 文档包导航 | 每次新增/删除归集文档时更新 |
| `product/01-product-design-overview.md` | 产品设计总览 | 产品流程、页面结构、报告模式变化时更新 |
| `architecture/02-technical-architecture.md` | 技术架构总览 | 后端编排、RAG、Evidence、LLM/MCP 变化时更新 |
| `architecture/03-agent-implementation.md` | Agent 实现说明 | 单 Agent 能力、输入输出、质量闸门变化时更新 |
| `guides/04-testing-and-bug-log.md` | 测试和 Bug 记录 | 每次关键测试、线上/本地问题修复后追加 |
| `architecture/05-design-decision-log.md` | 设计决策日志 | 做出不可逆或影响后续架构的决策时追加 |
| `product/06-roadmap-and-open-risks.md` | 路线图和风险 | 每轮迭代结束后更新优先级 |
| `product/09-deepresearch-engine-product-design.md` | DeepResearch 产品设计 | 研究引擎产品目标和用户体验变化时更新 |
| `architecture/10-deepresearch-engine-technical-design.md` | DeepResearch 技术设计 | LangGraph 节点、MCP、工具路由和 Claim/GAP 机制变化时更新 |
| `specs/11-deepresearch-engine-data-and-test-plan.md` | DeepResearch 数据和测试 | 数据结构、验收标准和测试样本变化时更新 |
| `architecture/12-deepresearch-engine-implementation-plan.md` | DeepResearch 实施计划 | 每阶段代码推进后更新状态 |

## 原有产品和技术设计文档

| 文档 | 主题 | 与归集文档关系 |
| --- | --- | --- |
| `product/BUSINESS-DESIGN.md` | 早期业务设计 | 可作为产品背景参考；当前实现以 `product/01-product-design-overview.md` 为准 |
| `product/public-pre-dd-dual-mode-implementation.md` | 公开资料预尽调与财报增强双模式 | 已被吸收到产品总览、架构方案和 Agent 实现文档中；仍保留作专题设计来源 |
| `architecture/listed-company-financial-data-integration-design.md` | 上市公司财务数据接入 | 仍是上市公司财务数据源后续实现的专题方案 |
| `plans/backend-execution-plan.md` | 早期执行计划 | 可作为历史计划参考；当前实现以代码和本归集文档为准 |
| `backend/README.md` | 后端说明 | 面向开发启动和后端模块说明，可后续同步更新 |

## UI 和视觉设计文档

| 文档 | 主题 | 与归集文档关系 |
| --- | --- | --- |
| `design-system/UI-Design-System.md` | UI 设计系统 | 视觉 token、组件规范参考 |
| `design-system/UI_DESIGN_SPEC.md` | UI 设计规范 | 页面和组件实现规范参考 |
| `design-system/UNIFIED_VISUAL_MASTERPLAN.md` | 统一视觉方案 | 视觉改造历史方案 |
| `design-system/UI_REFACTOR_TASK_LIST.md` | UI 重构任务清单 | 历史任务拆解参考 |
| `design-system/VISUAL_REFACTOR_V2_SCREEN_REFERENCE_AND_PALETTE.md` | 视觉参考和配色方案 | 历史视觉策略参考 |
| `design-system/REFERENCE_STYLE_ADOPTION.md` | 参考风格采纳说明 | 解释曾采用的外部风格参考 |
| `design-system/ui-specs/**` | UI 原型/示例代码 | 注意其中包含 mock 示例，不一定代表当前真实业务实现 |

## SDD 文档

| 文档 | 主题 | 与当前项目关系 |
| --- | --- | --- |
| `specs/README.md` | SDD 文档索引 | 更偏通用软件设计文档 |
| `specs/prd.md` | PRD | 可作为早期产品需求参考 |
| `specs/spec.md` | 规格说明 | 可作为页面/流程参考 |
| `specs/sdd-plan.md` | 实施计划 | 历史计划参考 |
| `specs/tasks.md` | 任务拆解 | 历史任务参考 |
| `specs/test.md` | 测试方案 | 可结合 `guides/04-testing-and-bug-log.md` 继续完善 |

## 知识库文档

知识库位于 `backend/data/knowledge_base/`，它不是项目说明文档，而是 RAG 的业务知识输入。

| 目录 | 内容 | 用途 |
| --- | --- | --- |
| `financial_guides/` | 财务审查、缺失数据、异常信号 | 财务 Agent prompt 和 RAG 动态注入 |
| `industry_guides/` | 行业指南和行业尽调逻辑 | 行业 Agent RAG 和诊断规则 |
| `business_guides/` | 工商审查指南 | 工商 Agent 后续增强 |
| `legal_guides/` | 司法风险审查 | 司法 Agent 后续增强 |
| `credit_guides/` | 授信决策、贷后管理 | 完整报告和授信建议 |
| `bank_policy_references/` | 同业/内部制度参考包 | RAG 增强，不应直接等同本行正式制度 |
| `risk_frameworks/` | 指标阈值、风险评分、规则 JSON | 质量闸门和风险判断参考 |
| `templates/` | 报告模板 | 报告结构和话术参考 |
| `cases/` / `case_studies/` | 案例 | 后续 few-shot 和风控案例学习 |

## 维护原则

1. 产品方向和实现现状写入 `docs/product/` 和 `docs/architecture/`。
2. 专题方案仍可保留在 `docs/` 对应主题目录下，但要在本地图中登记。
3. 可被 RAG 检索的业务知识放入 `backend/data/knowledge_base/`，并添加 front matter。
4. 测试发现的问题优先追加到 `guides/04-testing-and-bug-log.md`，不要只留在聊天记录里。
5. 关键架构取舍追加到 `architecture/05-design-decision-log.md`，避免后续重复争论同一问题。
