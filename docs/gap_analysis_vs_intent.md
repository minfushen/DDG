# ddg-agent：需求意图 vs 代码落地 差距分析

> 来源：用户提供的《百融对公尽调项目-面试深度准备材料.md》（产品解决方案视角的能力清单）。
> 目的：把文档里声称的 11 项核心能力，逐条与 `/Users/minfushen/Projects/ddg-agent` 实际代码对照，标注「已落地 / 部分落地 / 缺失 / 预期之外」，附 `file:line` 证据。
> 日期：2026-07-06。状态：只读分析，未改动任何业务代码。

---

## 头条发现（面试前必看）

文档反复把 **「向量 + BM25 混合检索 + RRF 倒数排名融合 + RERANKER 精排」** 定义为行业分析 Agent 的核心竞争力（故事 4 / 5 / 7、Q5、第六章架构映射）。

但代码现状：

- `backend/app/rag/retriever.py:51-55` 只有 `kb.search(query, category, top_k)`——**纯向量检索 + category 过滤**，没有 BM25、没有 RRF 融合、没有重排模型。
- 全仓 grep `rerank | RERANKER | RRF | BM25` **零匹配**。

结论：你面试叙事里最硬的一条「宽进严出 + RRF 融合 + 重排精排 + 意图路由控成本」链路，**代码目前撑不住**。追问「RRF 怎么融合、重排模型用哪个、BM25 权重怎么定」会露馅。这是当前版本与文档差距最大、也最该补的一块。

---

## 差距矩阵

| # | 能力（文档主张） | 代码现实 | 证据（file:line） | 状态 |
|---|---|---|---|---|
| 1 | 行业 RAG：向量 + BM25 混合 + RRF + 重排 | 纯向量检索 + category 过滤 | `rag/retriever.py:51`；grep 无 RRF/BM25/reranker | ❌ 缺失 |
| 2 | 财报解析：MinerU/pdfplumber/pymupdf 分级 + 表格修复 | 有分级提取引擎 + pdfplumber 表格提取 | `agents/tools/pdf_extraction_engine.py`；`engines/rebecca/parsers.py:328` | ✅ 已落地 |
| 3 | 财报解析：**标准科目映射表**（schema 对齐） | 仅关键字列匹配，无维护式映射表 | `sub_agents/financial_report_builder.py:910-917` 字段元组 | 🟡 部分落地 |
| 4 | 财报解析：跨页表格合并 + 数值勾稽校验（年初+增−减=期末） | 未见显式实现 | grep 无 `跨页`/`勾稽`/`cross.?page` | 🟡 部分落地 |
| 5 | **父子文档分片**（故事 4/5 核心技术） | 未实现 | grep 无 `parent_child`/`父子` | ❌ 缺失 |
| 6 | **CRAG 纠错**回路 | 仅有 legal/business 的「兜底搜索」 | `sub_agents/legal_agent.py:174`；`sub_agents/business_agent.py:57` | 🟡 部分落地 |
| 7 | Tool Router + 工具**负向边界** | 有 category 路由，无独立 Router 类 + 负向描述 | grep 无 `tool_router`；`codeact/financial_tools.py:273` 的 negative 是「负号」非「负向边界」 | 🟡 部分落地 |
| 8 | 长期记忆（企业画像）+ **解析/计算缓存跨任务复用** | 有长期记忆 + LLM 缓存，但跨任务复用企业解析/计算结果未明确坐实 | `memory/long_term.py:133`；`config/llm_config.py:109 cached_invoke(ttl)`；`main.py:13 init_cache_store` | 🟡 部分落地 |
| 9 | 视觉 RAG（ColPali）处理年报图片 | 无（文档自标「探索方向」） | grep 无 `colpali`/`vision` | ➖ 预期之外 |
| 10 | Rebecca 规则引擎（数值不走 LLM） | 扎实 | `engines/rebecca/` | ✅ 已落地 |
| 11 | 四 Agent 分治 + full_report_builder（Map-Reduce） | 扎实 | `agents/sub_agents/` | ✅ 已落地 |
| 12 | 报告质量门（完整/证据/一致/数值） | 扎实 | `agents/research_engine/report_quality_evaluator.py` | ✅ 已落地 |
| 13 | HITL 人工在环（原生 API 路径） | 实装 | `api/tasks.py:879-976` | ✅ 已落地 |
| 14 | PDF / Word 报告导出 | 本轮已补齐 | `engines/rebecca/report_generator.py` + `api/tasks.py` 下载端点 | ✅ 已落地 |

图例：✅ 已落地　🟡 部分落地（比文档承诺窄/弱）　❌ 缺失（文档暗示已交付，实际无/桩）　➖ 文档自标探索方向，非缺口

---

## 已扎实落地的部分（面试叙事站得住）

- **Rebecca 规则引擎**：数值计算 100% 可复现，LLM 只做定性研判 → 支撑「零幻觉财务」。
- **四 Agent 分治 + full_report_builder**：工商/财务/行业/司法分治，最后合拢授信意见 → 支撑「多 Agent 协同决策」。
- **报告质量门**：完整性 / 证据充分性 / 一致性 / 数值准确性四维度检查 → 支撑「报告质量门控」故事。
- **HITL 原生路径 + SSE 流式**：关键节点可中断恢复，过程可观测 → 支撑「人工在环 / 可审计」。
- **财报分级解析引擎**：MinerU → pdfplumber → pymupdf 多级回退 → 支撑「高精度解析打底」。

---

## 按优先级排列的待补项

| 优先级 | 待补能力 | 与文档的落差 | 建议修法 |
|---|---|---|---|
| P0 | 行业 RAG 混合检索 | 纯向量 ≠ 文档承诺的混合+RRF+重排 | 加 BM25 关键词索引 + 向量召回 + RRF 融合 + 轻量 reranker（bge-reranker / 本地交叉编码器）+ 意图路由控成本 |
| P0 | 财报解析增强 | 关键字匹配 ≠ 标准科目映射表；无跨页合并/勾稽 | 维护标准科目映射表 + 跨页表格合并 + 数值勾稽校验（不平则告警） |
| P1 | 父子文档分片 + CRAG | 文档核心 RAG 技术全缺 | 短片段召回 + 父段落回填；低置信触发 Web/重检索纠错 |
| P1 | Tool Router 负向边界 | 有 category 路由无独立 Router + 负向描述 | 抽 ToolRouter 类，工具描述写负向边界 + 返回相关性分数/引导指令 |
| P2 | 跨任务缓存复用 | 有 LLM 缓存，无企业级解析/计算缓存 | 同企业年报解析结果、财务指标计算结果按企业主键缓存复用 |

---

## 给面试的提醒

1. 讲「RAG 准确率从 60%→80%」时，要清楚代码当前是纯向量检索——若被追问 RRF/重排细节，可如实说「这是设计目标，落地时按场景做了简化」，避免被现场戳穿。
2. 「标准科目映射表」「跨页表格合并」「数值勾稽」目前是关键字匹配 + 人工校验级别，讲的时候收一收「90% 准确率」的口径。
3. 视觉 RAG（ColPali）文档已自标探索方向，可大方讲「如果重做会怎么做」，这是加分项而非缺口。
4. 扎实落地的四块（Rebecca / 四 Agent 分治 / 质量门 / HITL）可以讲深、讲细节，代码撑得住。
