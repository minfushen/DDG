# 产品需求文档 v2.0 — 专业深度对齐信贷/风控标尺

> **文档定位**（与 v1 PRD / spec 的关系）
> - 本文件是 [`prd.md`](./prd.md)（v1.0/1.1）的**重构升级版**，聚焦"专业深度"这一专项。
> - 沿用文档体系：`spec.md` 是**稳定的工程契约**（用例编号权威），本 PRD 是**鲜活的需求池**；本文件落地前，对应能力须同步更新 `spec.md`（见 §9 级联清单），遵循宪法"先改文档，再改代码"。
> - 用户定位**不变**（仍是一线客户经理），变的是**验收标尺**：按信贷岗 / 风控岗的专业标准定。

---

## 1. 重构背景与核心判断

### 1.1 调研结论（驱动本次重构）

信贷岗副总在需求调研中明确反馈：**一线客户经理产出的初版尽调报告"太粗浅、不专业"**，希望本智能体帮助客户经理写出的报告，**尤其是财务分析和行业分析部分，深度向信贷 / 风控部门的专业水准看齐**。

由此得到本次重构的两个锚点：

- **用户不变**：核心用户仍是一线客户经理（张经理），高频日常使用者。
- **验收标尺升级**：报告的"好"不再以"能生成框架"衡量，而以**能否过信贷 / 风控评审这一关**衡量。价值重心从"广度（生成）"移到"深度（专业分析 + 可信验证）"。

> 这与现有 `README` 中"财务分析 Agent、行业分析 Agent 是核心交付模块"的方向一致，只是把价值主张从"能生成"升级为"**生成得够专业、够深、能过信贷风控专业评审**"。

### 1.2 "粗浅"的具体表现（副总反馈 + rubric 印证）

| 维度 | 粗浅表现（现状痛点） | 专业标尺（信贷 / 风控要什么） |
|------|----------------------|-------------------------------|
| 财务 | 只堆数字，不做同业对比、不做趋势归因 | 每指标后跟**行业中位数**对比 + "为什么"归因 |
| 财务 | 缺现金流质量、盈利质量分析 | 显式**经营现金流质量、扣非 vs 归母、政府补助依赖度** |
| 财务 | 现金流分析只基于财报现金流量表，缺银行流水尽调 | 财报现金流 + 银行流水双重验证：收入真实性、纳税/水电/人力勾稽、对手方重合、隐性负债 |
| 行业 | 只讲宏观，不落到企业授信影响 | 落到**本企业授信风险与关注点**、竞品市占率对标 |
| 交叉验证 | 基本缺失 | 独立**交叉验证与重大风险**章节 |
| 整体 | 行业分析甚至直接缺失 | 行业分析是授信报告一等公民章节 |

### 1.3 专业标尺（来源：三安光电贷前尽调报告 + 现有 rubric）

从专业模板与现有 `docs/specs/15-report-quality-evaluation-rubric.md` 提炼出两层标尺：

**① 报告结构标尺（8 章，已与 rubric 对齐）**

1. 报告摘要与授信建议
2. 企业主体与治理结构
3. 财务状况与偿债能力
4. 行业与经营环境
5. 司法与合规风险
6. **交叉验证与重大风险**（现有系统缺独立一等公民章节）
7. **信贷方案建议**（分阶段额度 / 条件 / 风险权重）
8. 证据链与待补充材料

**② 4 个深度维度（本次重构的核心）**

| 维度 | 专业模板做法 | 现状差距 |
|------|--------------|----------|
| 同业对比 | 每个指标后跟"行业中位数 / 行业合理区间"（如资产负债率 37.53% vs 行业 44.93%） | Rebecca 行业基准是**硬编码假值**（`analyzers.py`：毛利率 35%、ROE 15%、流动比率 1.5、资产负债率 60%） |
| 趋势归因 | 解释"为什么"（毛利率下滑归因为产能过剩 / 产能爬坡 / 折旧摊销） | 只有"优秀 / 一般"评价，缺归因叙述 |
| 现金流质量 | 经营现金流净额、扣非 vs 归母、政府补助依赖度 | Rebecca 有基础框架，未**显式输出盈利质量 / 现金流质量** |
| 行业→授信传导 | 4.1~4.3 全部落到"对本企业授信的影响与关注点" + 竞品对标表 | 行业 Agent 已有"授信审查重点"方向，但**未落到企业级、缺竞品对标** |

---

## 2. 现有能力盘点（已具备 vs 缺口）

> 结论先行：**能力底座已能支撑专业骨架的约 80%**，重构重点不是重写引擎，而是补"对标基准真实化 + 归因深度 + 渲染完成 + 解析可信下传"。

### 2.1 解析层（对标 Quaesto 财报 OCR 结构化）

现有 `backend/app/engines/rebecca/parsers/` 已有一个**与 Quaesto 方法论同构**的四阶段管线：

| Quaesto 五幕 | 上市公司路径（已有） | 非上市公司上传路径（缺口） |
|---|---|---|
| ① MinerU 版面分析 | ✅ `financial_pdf_pipeline.py` Stage1 `MinerUParser` | ❌ 仅 `pdfplumber`（`parsers.py` `FinancialParser._parse_pdf`） |
| ② 小模型只抄不算 | ✅ `vision_transcriber.py` MiniCPM-V（系统提示"只做抄写，不做计算"） | ❌ 无 |
| ③ 代码算账勾稽 | ✅ Stage3 `AccountingValidator`（23 条确定性规则 + 红黄绿） | ❌ 无（pdfplumber 提取后直接进 Rebecca） |
| ④ 看图兜底 | ✅ Stage4 `VisionFallback` | ❌ 无 |
| ⑤ 人工核验工作台 | ⚠️ 仅报告页证据链，无解析层对账台 | ❌ 无 |

- `FinancialPdfPipeline` 已在上市公司年报路径（`cninfo_announcement_tool.py`）落地，但**非上市公司上传 PDF 未路由到该管线**。
- `ParsedTable` 仅记 `page`，`Normalizer` 不保留坐标 → 缺字段级 **bbox 坐标溯源**。
- pipeline 已产出 `auto_judgment_rate` / `issues` / `needs_human_review`，但 **Rebecca 与报告不接收这些质量信号**。

### 2.2 财务引擎 Rebecca（`backend/app/engines/rebecca/`）

- 10 维度框架方向正确（盈利 / 偿债 / 营运 / 成长 / 现金流 / 风险）。
- **致命缺口**：行业基准全部硬编码假值（`analyzers.py` 多处 `"行业平均"` 写死 35% / 10% / 15% / 1.5 / 60%）；成本结构 / 资产质量 / 负债结构 / 盈利趋势为占位假值（`return` 写死百分比与"稳定 / 上升"）。
- 报告渲染半成品：`report_generator.py` 把 DataFrame 直接 `json.dumps` 塞文本，未渲染成表格；结论为写死套话"企业整体财务状况良好"。

> **现金流分析的两种口径**：
> - **财报现金流量表口径**：适合上市公司，回答"账面现金流结构、盈利质量、偿债保障"（经营现金流/净利润、自由现金流、利息保障）。
> - **银行流水尽调口径**：适合非上市公司/中小企业，回答"账面现金流是否真实、收入有没有水分、有无隐形负债和关联交易"（数据质量、有效流入/流出、对手方重合、疑似关联方、隐形负债）。
> v2.0 要求两者互补：上市公司以财报现金流为主、银行流水为辅；非上市公司在财报不可得或可信度低时，以银行流水尽调作为现金流质量的核心输入。

### 2.3 行业分析 Agent（`backend/app/agents/sub_agents/industry_agent.py`）

- 方向正确：已输出景气度 / 竞争格局 / 政策环境 / **授信审查重点**。
- 缺口：细分行业定位易错分（rubric 典型 P1：半导体被识别成贸易）；未**落到企业级授信传导**；缺竞品市占率对标；未结合主营构成 / 年报经营讨论。

### 2.4 质量门 rubric（`docs/specs/15-report-quality-evaluation-rubric.md`）

- 已定义 8 章结构 + 财务深度（15 分）+ 行业深度（15 分）作为质量门，是本次重构的**现成抓手**。
- 需把"财务 / 行业深度"条款**具体化**：加入"真实行业中位数对比 / 趋势归因 / 盈利质量 / 现金流质量 / 异常信号"以及"落到企业授信传导 / 竞品对标"作为通过 / 高分必要条件（见 §5）。

---

## 3. 重构三大支柱

### 支柱一：解析可信化（数据底座可信）

> 解析不准，后面分析再深也站不住。对标 Quaesto，但**只借鉴方法论，不直连其云端服务**（企业财报属敏感数据，数据出域有合规红线）。

| 编号 | 需求 | 落点 | 现状 |
|------|------|------|------|
| P1.1 | 非上市公司扫描件 PDF 优先路由到 `FinancialPdfPipeline`（同构四阶段），而非 pdfplumber 裸解析 | `parsers.py` `FinancialParser._parse_pdf` 增加路由判断 | 仅 pdfplumber，扫描件乱码 / 漏抽 |
| P1.2 | 字段级 bbox 坐标溯源：每个财务数字可点击溯源到原 PDF 坐标 | `ParsedTable` 补 `bbox` 字段；`Normalizer` 保留坐标 | 仅记 `page` |
| P1.3 | 解析质量信号下传：把"标红 / 黄 / 绿、是否需人工复核"传进 Rebecca 分析与授信报告 | `AccountingValidator` 输出 → `analyzers.py` 输入；报告体现"数据可信度" | 信号未下传 |
| P1.4 | 根因聚类：`findings` 按规则族 / 根因聚合，便于人工复核 | `financial_pdf_pipeline.py` `AccountingValidator` | 平铺文本 |
| P1.5 | 人工核验工作台（第五幕）：解析异常时"标红 → 看原图 → 修正"闭环（只记事务不改原文） | 复用现有 HITL"财报上传恢复"机制 | 仅报告页证据链 |

### 支柱二：财务分析深度（核心补强区）

| 编号 | 需求 | 落点 | 现状 |
|------|------|------|------|
| P2.1 | **真实行业中位数对标**：替换 `analyzers.py` 硬编码行业基准，按申万行业取同行业 A 股近三年财报批量算各指标中位数 | 复用 akshare / 东方财富（系统已用）；新增行业中位数取数模块 | 硬编码 35% / 15% / 1.5 / 60% 假值 |
| P2.2 | **趋势归因叙述**：每个异常 / 关键指标解释"为什么"（如毛利率下滑归因为 N 因素） | `analyzers.py` 补归因生成；结论绑定证据 | 只有"优秀 / 一般"评价 |
| P2.3 | **盈利质量分析**：扣非 vs 归母、非经常性损益 / 政府补助依赖度 | `analyzers.py` 新增盈利质量维度 | 缺 |
| P2.4 | **现金流质量显式输出**：经营现金流 / 净利润、经营现金流 / 营收、自由现金流 | Rebecca 已有基础框架，显式成章节 | 框架在，未成章 |
| P2.5 | **财务异常信号识别**：勾稽冲突、科目异常、偿债压力预警 | 结合 P1.3 解析校验信号 + `risk_assessment` 升级 | `risk_assessment` 仅简单阈值 |
| P2.6 | **报告渲染对齐**：8 章结构 + 财务指标渲染成表格（非 json.dumps）+ 各指标行业中位数对照列 | `report_generator.py` | DataFrame 直接 `json.dumps` 塞文本 |

### 支柱三：行业分析深度（核心补强区）

| 编号 | 需求 | 落点 | 现状 |
|------|------|------|------|
| P3.1 | **细分行业定位防错分**：结合主营构成 / 年报经营讨论锁定细分行业，杜绝"半导体被识别成贸易" | `industry_agent.py` 行业识别逻辑 | rubric 典型 P1 |
| P3.2 | **落到企业授信传导**：行业周期 / 政策 / 景气度 → 本企业授信风险与关注点 | `industry_agent.py` 输出结构升级 | 已有"授信审查重点"方向，未落到企业级 |
| P3.3 | **竞品市占率对标**：主要竞争对手市占率 / 排名对比表 | 行业知识库 + 公告 / 年报线索 | 缺 |
| P3.4 | **周期 / 政策 / 上下游议价**：行业周期位置、关键政策传导、上下游议价能力 | 复用现有 RAG 行业库 + 结构化输出 | 部分覆盖，需强化授信视角 |

---

## 4. 用户故事（US-050 系列，避免与 v1 编号冲突）

> 格式沿用 v1：`As a <角色>, I want <能力>, so that <价值>`，每故事带验收标准（AC）。

### US-050 解析可信化（非上市公司扫描件）

> 作为**张经理**，我希望上传的扫描件财报也能被正确解析并标注可信度，这样我不用手动重录或担心数据错误被信贷风控挑刺。

**关联**：`spec-DD-1`、`P1.1~P1.5`
**AC**：
- [ ] 无文字层 PDF 上传后自动路由到 `FinancialPdfPipeline`，解析成功率 ≥ 95%（抽样 20 份扫描件）
- [ ] 解析异常数字在报告中带"标红 / 黄 / 绿"可信度标记
- [ ] 报告中每个财务数字可点击溯源到原 PDF 坐标（bbox）
- [ ] "需人工复核"的财报触发 HITL 恢复流程，修正只记事务不改原文

**优先级**：P0（数据底座）
**版本**：v2.0

---

### US-051 财务分析专业深度

> 作为**张经理**，我希望生成的财务分析带**真实行业中位数对比、趋势归因、盈利质量与现金流质量**，这样信贷 / 风控评审时不再嫌"粗浅"。

**关联**：`spec-DD-2`、`spec-DD-5`、`P2.1~P2.6`
**AC**：
- [ ] 每项核心指标（毛利率 / 净利率 / ROE / 流动比率 / 资产负债率等）后跟**真实行业中位数**（来源可查，非硬编码）
- [ ] 至少 1 个异常信号形成"现象 — 归因 — 风险定性 — 核查要点"
- [ ] 显式输出**盈利质量**（扣非 vs 归母、非经常性损益/政府补助依赖）与**现金流质量**章节；现金流质量须覆盖：经营现金流/净利润、经营现金流/营业收入、自由现金流、经营现金流利息保障倍数、现金流短债覆盖；对非上市公司须补充**银行流水尽调结论**（数据质量、有效流入/流出、对手方重合、疑似关联方、隐形负债）
- [ ] 财务指标渲染为表格（含行业中位数对照列），非 json 文本
- [ ] 财务结论绑定结构化财报 / 公告 / 财务诊断 evidence
- [ ] 无"暂不可计算""行业平均 35%"等占位 / 假值表达（rubric 语言红线）

**优先级**：P0（核心补强）
**版本**：v2.0

---

### US-052 行业分析专业深度

> 作为**张经理**，我希望行业分析落到"对本企业授信的影响与关注点"并带竞品对标，这样信贷 / 风控能直接引用。

**关联**：`spec-DD-2`、`P3.1~P3.4`
**AC**：
- [ ] 细分行业定位准确（回归样例 10 家上市公司无错分，尤其半导体 / 军工 / CXO）
- [ ] 行业章节覆盖周期 / 竞争格局 / 政策环境 / 上下游议价 / **授信关注点**
- [ ] 授信关注点**落到本企业**（结合主营构成、年报经营讨论）
- [ ] 主要竞品市占率 / 排名对比表
- [ ] 行业结论绑定 evidence

**优先级**：P0（核心补强）
**版本**：v2.0

---

### US-053 交叉验证与信贷方案建议章节升级

> 作为**张经理**，我希望报告含独立的"交叉验证与重大风险""信贷方案建议"章节，这样结构与信贷 / 风控专业模板一致。

**关联**：`spec-DD-3`、rubric 8 章结构
**AC**：
- [ ] 稳定输出 8 章结构，第 6 章"交叉验证与重大风险"、第 7 章"信贷方案建议"为独立一等公民章节
- [ ] 交叉验证体现多源数据勾稽（如营收 vs 纳税 vs 流水一致性）
- [ ] 信贷方案建议含分阶段额度 / 条件 / 风险权重，且与风险分一致

**优先级**：P1
**版本**：v2.0

---

## 5. 验收标尺更新（具体到 rubric）

> 本 PRD 要求把 `docs/specs/15-report-quality-evaluation-rubric.md` 的"财务分析深度""行业分析深度"条款**具体化**，作为 v2.0 质量门的硬条件。

**财务分析深度（15 分）新增通过条件：**
- 每项核心指标绑定真实行业中位数（来源可查），缺失则扣 3 分；
- 至少 1 个异常信号含"现象 — 归因"叙述，否则扣 2 分；
- 显式盈利质量 + 现金流质量章节，现金流质量须覆盖经营现金流/净利润、经营现金流/营业收入、自由现金流、利息保障、现金流短债覆盖；对非上市公司须补充银行流水尽调结论（数据质量、有效流入/流出、对手方重合、疑似关联方、隐形负债），否则扣 2 分；
- 报告内无硬编码假行业基准 / 占位表达（rubric 语言红线），否则记 P1。

**行业分析深度（15 分）新增通过条件：**
- 细分行业定位无错分（回归样例 10 家 0 错分），否则 P1；
- 含"落到本企业授信影响与关注点"，否则扣 3 分；
- 含竞品市占率 / 排名对标，否则扣 2 分；
- 含周期 / 政策 / 上下游议价，否则各扣 1 分。

**演示标准（建议）上调：** 财务分析深度 `>= 80`、行业分析深度 `>= 80`（原为 75）。

---

## 6. 优先级与路线图

### 6.1 RICE（新增需求，相对 v1 增量）

| 需求 | Reach | Impact | Confidence | Effort | RICE | 排序 |
|------|-------|--------|------------|--------|------|------|
| US-050 解析可信化 | 100% | 3 | 0.9 | 5 | 54 | 1 |
| US-051 财务深度 | 100% | 3 | 0.8 | 6 | 40 | 2 |
| US-052 行业深度 | 100% | 3 | 0.8 | 5 | 48 | 3 |
| US-053 章节升级 | 100% | 2 | 0.9 | 3 | 60 | 4 |

> 解析可信化（US-050）排序虽靠后，但它是 P2.1 真实行业对标的数据前提，工程上应**优先启动 P1.1（PDF 路由）**。

### 6.2 版本路线

- **v2.0 — 专业深度对齐（本次重构）**
  - P1.1 非上市公司 PDF 路由到 `FinancialPdfPipeline`
  - P2.1 真实行业中位数对标（替换硬编码）
  - P2.2~P2.5 趋势归因 + 盈利质量 + 现金流质量 + 异常信号
  - P3.1~P3.4 行业落到企业授信传导 + 竞品对标
  - P1.2~P1.3 bbox 溯源 + 质量信号下传
  - US-053 8 章结构固化（交叉验证 / 信贷方案建议）
  - rubric 财务 / 行业深度条款具体化

---

## 7. 数据源决策（回答"行业中位数从哪来"）

| 用途 | 正确数据源 | 决策 |
|------|------------|------|
| **企业财务指标同业对标**（中位数 ROE / 毛利率 / 流动比率等） | 同行业可比上市公司财务指标中位数（akshare / 东方财富按申万行业取同行业 A 股算中位数） | ✅ 系统已用 akshare，**直接复用**；非上市公司用同行业中位数代理 |
| **行业宏观背景**（行业整体增速 / 利润率 / 景气度） | 国家统计局分行业数据 | ⚠️ 仅作"行业环境"素材，**不用于企业直接对标**（口径错配：是行业宏观总量，非企业级中位数） |
| 银行内部更权威 | iFinD / Wind | 可选增强（客户侧，非系统必备） |
| 第三方 OCR（如 Quaesto） | 云端 SaaS | ❌ **不直连**（数据出域合规红线）；仅借鉴方法论或私有化部署 |

---

## 8. 反向需求 / 约束（明确不做）

| 需求 | 不做的理由 | 来源 |
|------|-----------|------|
| 直连 Quaesto 等第三方 OCR 云端 | 财报敏感，数据出域违反银行合规 | 合规建议 |
| 用国家统计局数据做企业级行业对标 | 口径错配，是行业宏观总量非企业中位数 | 本次评估 |
| 替代信贷 / 风控最终决策 | 监管要求 + 信任问题（宪法 §1.3） | 宪法 |
| 重写 Rebecca 引擎框架 | 10 维框架方向正确，只需补基准真实化 + 深度 | 能力盘点 |

## 9. RPA 工具分工边界设计（新增）

> 随着行内数据接口、网银流水、征信/工商/税务等外部系统对接需求增加，本项目与 RPA 工具的分工需要明确边界：**RPA 负责"数据搬运"，Agent 负责"数据理解"**。两者通过标准化数据池与任务 ID 协同，避免职责重叠或能力错配。

### 9.1 核心原则

| 原则 | 含义 | 原因 |
|------|------|------|
| **RPA 搬运，Agent 理解** | RPA 做规则化、低认知的界面操作；Agent 做语义解析、归因、推理、报告生成 | RPA 稳定、可控；Agent 擅长非结构化数据与复杂逻辑 |
| **RPA 进系统，Agent 不直接写生产库** | RPA 负责从网银/行内系统抓数、向信贷系统回填字段；Agent 只输出结构化字段和结论 | 防止 Agent 直接操作生产系统带来的安全与合规风险 |
| **数据池解耦** | RPA 输出标准化原始数据到共享数据池（如 S3/MinIO/消息队列）；Agent 按任务 ID 读取 | 双方不直接依赖对方实现，便于独立升级与回滚 |
| **Agent 是调度大脑，RPA 是执行手脚** | Agent 判断"需要哪些数据、何时需要"；RPA 负责"去指定系统把数据拿回来" | 避免 RPA 盲目抓数，也避免 Agent 被界面变更拖累 |

### 9.2 职责边界矩阵

| 能力 | 归属 | 本项目定位 | 说明 |
|------|------|-----------|------|
| 从网银/银企直连下载银行流水 | RPA | 数据搬运 | 网银界面无 API，RPA 最稳定 |
| 银行流水解析、分类、交叉核验 | Agent | 数据理解 | 用 `bank_flow_tool.py` + `flow_reconciliation.py` |
| 从征信/工商/税务/司法网站抓数据 | RPA | 数据搬运 | 如人行征信、企查查、裁判文书网等 |
| 财报/公告/合同 PDF 解析 | Agent | 数据理解 | 用 `FinancialPdfPipeline` / Rebecca |
| 行内信贷系统数据回填 | RPA | 数据搬运 | Agent 输出结构化字段，RPA 按字段映射写入 |
| 授信逻辑推导、风险识别、报告生成 | Agent | 数据理解 | 核心差异化能力 |
| 审批流程节点推进 | RPA | 流程执行 | 按人工/Agent 确认结果触发流程 |

### 9.3 协作接口

1. **输入接口**：RPA 将抓取的原始数据以标准化 JSON/CSV 形式放入共享数据池，文件命名包含 `task_id` + `source` + `timestamp`。
2. **输出接口**：Agent 将需要回填的字段写入共享数据池的回填区，RPA 读取后按字段映射写入行内系统。
3. **状态同步**：RPA 和 Agent 都通过任务 ID 向任务总线（或数据库）更新状态，便于前端追踪"数据采集 → 分析 → 回填"全链路。
4. **异常处理**：RPA 抓数失败时，把失败原因（验证码、页面变更、超时）写入任务日志；Agent 据此调整计划或标记数据缺口。

### 9.4 典型协作场景

| 场景 | RPA 动作 | Agent 动作 | 产出 |
|------|----------|-----------|------|
| **贷前数据采集** | 从征信/工商/税务/行内系统抓取原始数据 | 读取数据池，触发分析计划 | 证据链 + 缺口清单 |
| **银行流水获取** | 从网银/银企直连下载 Excel | 解析 `BankFlowData`，与年报交叉核验 | 流水×年报一致性结论 |
| **报告回填** | 按字段映射写入信贷系统 | 输出 8 章报告 + 结构化授信建议 | 尽调报告 + 系统字段 |
| **审批流程推进** | 在信贷系统点击提交/退回 | 根据风险信号判断是否需要人工复核 | 流程状态更新 |

### 9.5 明确不做

- **不让 RPA 做语义理解或行业分析**：RPA 不适合处理非结构化文本的归因与推理。
- **不让 Agent 直接登录网银/行内系统**：安全与合规风险高，且 Agent 对界面变更敏感。
- **不让 Agent 替代 RPA 执行大量规则化操作**：如反复下载、分页翻页、表单填写，RPA 更稳定、成本更低。

---

## 10. 对现有文档的级联更新清单

> 落地前需同步更新以下文档（遵循宪法"先改文档，再改代码"）。本 PRD 不直接改写它们，仅列出待更新条目。

| 文档 | 需更新条目 | 更新内容 |
|------|-----------|----------|
| `docs/product/prd.md` | §1 背景、§2 P1 核心诉求、§3 US-005 / US-006、§4 RICE、§5 路线图 | 核心定位补"验收标尺按信贷 / 风控专业深度"；US-005/006 升级为 US-051/052 深度要求；纳入解析可信化需求 |
| `docs/specs/spec.md` | §3.2 `SPEC-DD-2` / `SPEC-DD-5`、业务规则 | 业务规则增加"财务必须含真实行业中位数对比 / 归因 / 盈利质量 / 现金流质量""行业必须落到企业授信传导 / 竞品对标""解析可信度信号下传" |
| `docs/specs/15-report-quality-evaluation-rubric.md` | 财务 / 行业深度条款、演示标准 | 按 §5 具体化通过条件，演示标准上调至 80 |
| `docs/specs/constitution.md` | §1.1 一句话定义 | 补充"专业深度对齐信贷 / 风控标尺"（需团队评审 + 修订记录） |
| `README.md` | 核心价值 §2、架构图 | 财务 / 行业 Agent 描述升级为"专业深度对标信贷 / 风控"；解析层补 `FinancialPdfPipeline` |

---

## 11. 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0-draft | 2026-07-13 | 初版，聚焦"专业深度对齐信贷 / 风控标尺"，含三大支柱（解析可信化 / 财务深度 / 行业深度）、US-050~053、rubric 验收标尺更新、级联文档清单 |
| v2.0-draft-b | 2026-07-14 | 补充现金流分析的两种口径（财报现金流量表 + 银行流水尽调），并在 US-051 / US-053 / §5 验收标尺中增加银行流水验证维度（收入真实性、纳税/水电/人力勾稽、对手方重合、隐性负债） |
| v2.0-draft-c | 2026-07-14 | 新增 §9 RPA 工具分工边界设计，明确 RPA 负责数据搬运、Agent 负责数据理解，并定义协作接口与典型场景 |
| v2.0-draft-d | 2026-07-15 | 代码落地 P2.2 / P2.3 / P2.5：`analyzers.py` 趋势归因（多期真实趋势 + 杜邦式数据驱动归因）、盈利质量（扣非 vs 归母 / 非经常性损益占比 / 政府补助依赖度）、异常信号（勾稽冲突 / 科目异常 / 偿债压力，结构化"现象—归因—风险定性—核查要点"）；`report_generator.py` 接入盈利趋势与盈利质量两个新维度并动态编号，风险提示改为信号表格渲染 |
| v2.0-draft-e | 2026-07-16 | 代码落地 P2.1 接线：① 复用 `industry_market_data_tool._map_to_index_symbol` 把语义行业名（如"半导体/集成电路产业链")映射到东方财富板块名（"半导体")，`industry_benchmark._get_constituents` 查不到成分股时自动回退映射，确保真实行业中位数可命中；② `financial_agent._run_rebecca_analysis` 接收 `industry_name` 并透传 `FinancialDDAnalyzer`（替换硬编码假基准）；③ `run_financial_agent`（上市路径）从行业报告正确提取行业名（修复原 `_build_industry_context_for_narrative` 误读顶层 `industry` 取到位占位 `"industry_name"` 的 bug）；④ 上传路径 `run_financial_agent_with_uploaded_data` 新增 `industry_name` 入参并在上市公司时自动归类兜底；⑤ 经 `financial_service.analyze_full` 与 `tasks.py` 恢复流程透传；⑥ 沙箱网络受限（代理拦截东财），真实取数已用 mock 验证端到端正确，部署环境可取得真实中位数 |
| v2.0-draft-f | 2026-07-16 | 新增**关联网络模块**（对标真实项目案例的"关联信息挖掘"诉求）：① 新增 `relationship_network_tool` 整合股权/担保/质押/上下游——上市公司走 cninfo 股东表+风险档案+东方财富公开资料包，非上市走元典企业工商，失败安全降级（绝不伪造/占位）；输出标准化关联网络 + 风险标签（担保圈/关联担保、股权冻结、高比例质押、股权分散）；② 新增 `relationship_report_builder`（结构化章节：股权穿透/担保质押/上下游/关联风险评级）与 `relationship_agent.run_relationship_agent`（镜像 `legal_agent` 模式）；③ 接入编排链：`manifest` 新增 `relationship_network` 工具（类别 relationship）、`prompts.ALLOWED_RESEARCH_CATEGORIES`/`ALLOWED_TOOL_HINTS` 增加 relationship、`planner` 增加 `rt_relationship_network` 研究任务、`tool_router` 增加 relationship 执行步骤与公开搜索分支；④ 报告装配：主流程 `synthesizer` 新增"七、关联网络与关联交易"章节（`report_assembler.relationship_findings`），上传恢复路径 `full_report_builder` 以正式维度+章节接入（条件纳入，不影响既有 4 维评分）；`tasks.py` 恢复流程复用关联网络报告；⑤ 单测 `test_relationship_agent.py`（上市/非上市/降级/agent 四场景）全过。下一步：舆情 agent（P3.x 同范式） |
| v2.0-draft-g | 2026-07-16 | 新增**舆情/声誉风险模块**（对标真实项目案例"舆情整合+声誉风险"诉求，落位于 P3.x）：① 新增 `sentiment_tool.search_enterprise_sentiment`——Bocha 为主、SearXNG 兜底，按正/中/负词表分类并标注来源可信度（gov/court/creditchina/cninfo/sse/szse 视为权威源），搜索失败安全降级；② 新增 `sentiment_report_builder`（四章节：舆情概览/负面线索/正面线索/声誉风险评级，含权威源负面升级 high、负面≥3 升级 high、其余 medium/low，标签"权威源负面舆情/负面舆情线索/舆情平稳"）；③ 新增 `sentiment_agent.run_sentiment_agent`（镜像 `legal_agent`/`relationship_agent` 模式，返回 `sentiment_analysis_report`）；④ 接入编排链：`manifest` 新增 `sentiment_monitor`（类别 sentiment）、`prompts`/`planner` 增加 sentiment 任务（priority=6）与公开搜索分支、`tool_router` 增加 sentiment 执行步骤；⑤ 报告装配：主流程 `synthesizer` 新增"八、舆情与声誉风险"章节（`report_assembler.sentiment_findings`），原交叉验证/信贷/证据链顺延为九/十/十一；⑥ 单测 `test_sentiment_agent.py`（返回报告/权威源负面升级/纯正面 low/双源失败降级 四场景）全过。注：舆情与关联网络均作为信息型章节接入主流程、条件维度接入上传恢复路径，刻意不改动既有 4 维加权评分以避免回归。 |
| v2.0-draft-h | 2026-07-16 | 入口层**多意图识别 + 槽位抽取**（对标面试高频考察的产品要点"多意图分类与槽位识别"）：① 重写 `intent_extractor`——`fast_extract`/`fallback`/`extract_user_intent`(LLM) 均由单意图升级为多意图，输出 `intents: [{category,goal,slots}]`（1..N，覆盖 business/financial/legal/industry/relationship/sentiment/credit），并定义 `SLOT_SCHEMA`（depth/time_window/comparison/industry_segment/credit_assumptions/has_on_site_materials/output_format）与 `validate_slots` 校验+默认值回填；② 歧义澄清：`_is_generic_name` 识别"这家/该公司/某某"等占位指代，返回 `needs_clarification`+`clarification_prompt`（修复旧版无歧义分支的缺口；顺带修复 `extract_user_intent` 旧有的 `resolve_listed_company` 未导入会 NameError 的隐患）；③ 向后兼容：仍输出 `task_type`/`target_agent`/`enterprise_name`/`stock_code`/`confidence`，旧调用方无感；④ 编排贯通：planner 接收 `parsed_intent` 按 `intents` 裁剪研究类别（单意图只跑相关维度，主体确认 `rt_subject_identity` 始终保留）并把 `slots` 挂载到每个研究任务；经 `engine`→`graph_engine`→`_prepare_plan_node` 全程透传，主入口 `tasks.py` 与 `due_diligence_service` 均传入 `task["input_parse"]`；⑤ 单测 `test_intent_extractor.py`（多意图/完整不裁剪/槽位抽取校验/歧义澄清/向后兼容/planner 裁剪+挂载 九场景）全过，回归 57 通过。注：槽位目前已挂载到研究任务并存入 state，各 agent 对 slots 的深层消费（如按 time_window 取数、按 comparison 生成对比）为后续增量。 |
| v2.0-draft-i | 2026-07-17 | **槽位深层消费**（draft-h 标注的后续增量落地）：① 执行路径 `tool_router.execute_research_task` 读取 `task["slots"]` 并真正生效——`time_window`（latest/近一年/近三年/近五年）映射为巨潮公告回溯年数 `years_back` 与财报检索年份从句（替换原硬编码"2024 2023 2022"），`depth`（quick/standard/full）映射为公开搜索返回条数 `max_results`；新增 helpers `_years_back_for_time_window/_freshness_for_time_window/_year_clause_for_time_window/_max_results_for_depth`；② `comparison`/`industry_segment` 经 `execute_research_task`→`run_industry_agent`→`build_industry_analysis_report` 贯通：行业细分方向作为强提示注入分类上下文引导行业识别，`comparison∈{peer,self}` 时插入"同业对比分析/自身纵向对比"章节（基于行业指数/市场规模/竞争格局数据锚点），`none` 不插入；③ 报告层 `graph_engine` 把 `parsed_intent.slots` 存入 `state["slots"]`，`synthesizer.synthesize_research_report` 注入 `research_config`（depth/time_window/comparison/industry_segment/credit_assumptions/has_on_site_materials/output_format 七项），供前端渲染与 brief/slides 等下游消费；④ 单测 `test_slot_consumption.py`（检索参数映射/_bocha_query 年份从句/对比章节 peer-self-none/报告 research_config 落盘 九场景）全过，回归 118 通过。注：`credit_assumptions`/`has_on_site_materials`/`output_format` 当前以 `research_config` 形式落报告并供前端/下游消费（slides/brief 渲染属前端职责），尚未在 backend 改变报告章节结构，后续可据前端需求扩展。 |
| v2.0-draft-j | 2026-07-17 | **非功能需求落地（模板解析 + 灵活修改配置）**，对照建设要求"支持模板解析""前端灵活修改知识库/提示词"：① **模板解析与配置** `app/template/*`（models/parser/store/renderer）：解析 Markdown/DOCX 尽调模板，识别 `{{指标:营业收入|单位:万元}}`、`{{解读:财务健康度@financial}}`、`{{子报告:financial}}` 与指标表，抽成章节+指标位/解读位/子报告嵌入的结构化 `ReportTemplate`；文件存储（`DATA_DIR/templates`，内置标准模板开箱即用，支持激活/编辑/删除）；`full_report_builder.build_full_due_diligence_report` 新增 `template` 参数，按模板章节顺序组织报告并绑定指标值（来自财务 `key_metrics`）、子报告与解读（来自专项 `recommendation/risk_summary`），缺数据显式标"待补充/AI 解读位置"；`create_task` 新增 `template_id`（缺省取激活模板）并贯穿至财务增强报告生成。② **灵活修改** `app/config/prompt_overrides.py`+`app/rag/editable_knowledge.py`+`app/api/config.py`：提示词基线在 `prompts.yaml`，前端编辑只写覆盖层 `prompt_overrides.json`（可随时重置回基线、即时生效，且 `load_prompt_template` 优先返回覆盖）；知识库提供可编辑 JSON 条目 CRUD 并作为 RAG `retrieve_knowledge` 的额外召回源即时参与分析。③ 前端 `pages/ConfigCenter`（路由 `/config` + 导航）：模板上传/解析预览/保存/激活列表，提示词逐项编辑保存/重置，知识条目增删改。④ 单测 `test_template.py`（7 场景：解析结构/指标表/维度单位/docx 跳过/存储激活/渲染绑定/集成）与 `test_config_flex.py`（3 场景：提示词覆盖生效与重置/知识 CRUD/检索召回合并）全过；回归 294 通过（仅 1 例预存失败 `test_retrieve_knowledge_with_company_name` 与公司集合名哈希有关，与本次改动无关）。 |
| v2.0-draft-k | 2026-07-17 | **模板能力接入 DeepResearch 综合报告（draft-j 后续①）**：将 draft-j 的模板驱动从"财务增强 DD 报告"扩展到"DeepResearch 综合报告"，使两类报告都按客户经理上传模板组织章节。① `app/agents/research_engine/synthesizer.py`：`synthesize_research_report` 新增 `template` 参数；新增 helpers `_deepresearch_sub_reports`（把 `report_chapters` 按维度 id business/financial/... 转成渲染器可消费的 `sub_reports`，含 `report_chapters`/`recommendation`/`risk_summary`）与 `_deepresearch_financial_indicators`（从财务章文本按指标标签抽取可绑定值）；复用 `render_report_from_template` 生成 `report["template_sections"]` 与 `report["template"]` 元数据。② `app/agents/research_engine/graph_engine.py`：`_synthesize_node` 透传 `state["template"]`。③ `app/api/tasks.py`：执行 DeepResearch 前把 `_resolve_template(task)` 注入 `approved_state["template"]`，贯穿至合成。④ 前端 `pages/Report`：新增 `TemplateSectionsView` 组件渲染 `report.template_sections`（指标位/解读位置/子报告嵌入/静态指引，缺数据标"待补充"），在封面卡后展示并带模板名徽标；`ReportData`/`TemplateSectionRendered` 类型补齐；导出器 `report_exporter.py` 序列化整份报告，模板章节随报告 JSON 自动落盘。⑤ 单测 `test_template.py::test_deepresearch_report_attaches_template_sections` 全过；`test_template.py` 8 场景、`test_config_flex.py` 3 场景、`test_slot_consumption.py` 9 场景全过，无回归。 |
