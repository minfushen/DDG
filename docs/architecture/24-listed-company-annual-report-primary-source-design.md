# 24 上市公司年报 PDF 主数据源设计

> 目标：将 A 股上市公司财务数据获取路径从「结构化接口为主」切换为「CNINFO 年报 PDF 解析为主」，使 DDG Agent 的核心亮点——非结构化文档布局分析 + 内容解析 + RAG 检索——在上市公司尽调场景中真正落地。

---

## 1. 背景与问题

当前 `backend/app/agents/sub_agents/financial_agent.py` 的主链路：

1. `resolve_listed_company()` 识别上市公司
2. `_fetch_listed_financial_data()` 拉取 **东方财富 + AKShare 结构化三大表**
3. 结构化数据作为 `rebecca_data` 输入 Rebecca 引擎
4. `_fetch_cninfo_annual_report_evidence()` 仅作为**补充证据**和年报原文引用
5. `_build_annual_report_notes()` 从 PDF 抽取经营讨论、主营构成等叙事材料

问题：
- **结构化接口不是原始披露**，证据等级低于巨潮/交易所 PDF。
- **产品亮点被弱化**：布局分析、PDF 解析、RAG 检索只在补充证据环节出现，未进入核心财务数据生产链路。
- **报告来源不一致**：财务数字来自东方财富/AKShare，正文引用却指向巨潮 PDF，审计追溯困难。

因此必须切换为：**上市公司财务数据优先从年报 PDF 解析，结构化接口降为交叉校验/兜底**。

---

## 2. 目标架构

```text
用户输入企业名
    ↓
resolve_listed_company() ──→ 非上市公司 → 上传财报 / 公开资料线索
    ↓ 上市公司
cninfo_announcement_tool.search_annual_reports()
    ↓
下载近 3 年年报 PDF（合并报表）
    ↓
financial_pdf_pipeline.parse_annual_report_pdf()
    ├── MinerU：PDF → content_list（文本/表格/图片块 + bbox + 页码）
    ├── MiniCPM-V：表格块 → 行列网格 JSON（只抄不算）
    ├── 会计恒等式引擎：23 条规则勾稽校验，红黄绿分级
    └── qwen3.7 视觉：跨页/宽表/图表兜底
    ↓
标准化三大表 FinancialStatementData
    ├── income_statement
    ├── balance_sheet
    └── cash_flow
    ↓
Rebecca 规则引擎
    ↓
财务分析结果 + Evidence（source_url = 巨潮 PDF URL，source_page = 页码）
    ↓
报告正文级引用可跳转原始 PDF
```

东方财富 / AKShare 新定位：
- **交叉校验源**：当年报解析成功时，用结构化接口做差异校验；差异超阈值标记人工复核。
- **字段补缺源**：当年报 PDF 缺少某年/某科目时，用结构化接口补字段，并标注来源边界。
- **完全兜底**：当年报 PDF 四阶段管道全部失败时，回退到结构化接口，确保任务不阻塞。

---

## 3. 与现有模块的关系

### 3.1 复用已有能力

| 已有模块 | 复用方式 |
|---|---|
| `backend/app/agents/tools/cninfo_announcement_tool.py` | 搜索并下载年报 PDF；已有 PDF 抽取能力（`extract_pdf_content=True`） |
| `backend/app/agents/tools/annual_report_section_extractor.py` | 抽取年报章节、三大表、主营构成、经营讨论 |
| `backend/app/agents/tools/pdf_extraction_engine.py` | PDF 通用解析引擎 |
| `backend/app/engines/rebecca/analyzers.py` + `adapter.py` | 输入标准化三大表，输出财务分析 |
| `backend/app/rag/pdf_knowledge_ingestion.py` | 年报全文切片入库 |
| `backend/app/agents/evidence/evidence_store.py` | 生成带 `source_url`/`page` 的 evidence |

### 3.2 新增能力

| 新增模块 | 职责 |
|---|---|
| `backend/app/engines/rebecca/parsers/financial_pdf_pipeline.py` | 四阶段 PDF 解析管道，输出标准化三大表 |
| `backend/app/engines/rebecca/parsers/statement_normalizer.py` | 把 MiniCPM-V 转录的科目名映射到标准字段 |
| `backend/app/engines/rebecca/parsers/accounting_validator.py` | 23 条会计恒等式勾稽引擎 |
| `backend/app/agents/tools/financial_reconciliation.py`（扩展） | 年报 PDF 数据 vs 东方财富/AKShare 差异校验 |

---

## 4. 核心数据流

### 4.1 上市公司识别

复用现有 `backend/app/agents/tools/listed_company_tool.py` 的 `resolve_listed_company()`：

```python
listed_info = {
    "stock_code": "600703",
    "stock_exchange": "SSE",
    "security_name": "三安光电",
    "company_full_name": "三安光电股份有限公司",
}
```

### 4.2 年报检索与下载

复用 `cninfo_announcement_tool.search_annual_reports()`，参数：

```python
{
    "enterprise_name": "三安光电",
    "stock_code": "600703",
    "stock_exchange": "SSE",
    "keyword": "年度报告",
    "max_results": 6,           # 近 3 年 + 可能的重述公告
    "extract_pdf_content": True,
    "max_pdf_extract": 3,       # 下载前 3 份年报
}
```

返回需包含：
- 公告标题、披露日期、公告 ID、PDF URL、报告年度
- 下载后的本地 PDF 路径
- PDF 抽取出的原始文本/表格块

### 4.3 四阶段 PDF 解析管道

```python
# backend/app/engines/rebecca/parsers/financial_pdf_pipeline.py
class FinancialPdfPipeline:
    def parse_annual_report(self, pdf_path: str, report_year: int) -> ParsedAnnualReport:
        # Stage 1: MinerU / pdfplumber 版面分析
        doc = self._layout_parse(pdf_path)
        # Stage 2: MiniCPM-V 表格转录
        tables = self._transcribe_tables(doc.tables)
        # Stage 3: 会计恒等式勾稽
        validated = self._accounting_validate(tables)
        # Stage 4: qwen3.7 视觉兜底（跨页/宽表/图表）
        fallback = self._vision_fallback(doc, validated)
        return self._normalize_to_statements(fallback)
```

#### Stage 1：版面分析（MinerU）

- 输入：年报 PDF
- 输出：`content_list` JSON，含 `text`/`table`/`image` 块及 bbox、page
- 关键：识别三大表所在页码范围，过滤页眉/页脚/目录噪声

#### Stage 2：表格转录（MiniCPM-V）

- 输入：Stage 1 识别的表格块截图
- 输出：行×列网格 JSON
- Prompt 原则：「只抄不算」，不执行计算、不推断、不补全
- 截图策略：单表截图；跨页/超宽表先拼接再分片

#### Stage 3：勾稽校验（确定性引擎）

23 条规则示例：

| 规则 | 表达式 | 用途 |
|---|---|---|
| 资产负债表平衡 | 资产总计 = 负债合计 + 所有者权益合计 | 检测列错位 |
| 利润表勾稽 | 营业收入 - 营业成本 = 营业利润（近似） | 检测数值异常 |
| 现金流量净额 | 经营活动现金流净额 + 投资活动现金流净额 + 筹资活动现金流净额 = 现金及等价物净增加额 | 检测跨表一致性 |
| 应收账款 | 流动资产 ≥ 应收账款 | 检测单位错误 |

输出：
- 每条规则：通过/疑似 OCR 错/暂不定
- 整体可信度：数字触达率、自动判定率
- 需人工复核项列表

#### Stage 4：视觉兜底（qwen3.7）

触发条件：
- 跨页表格 Stage 2 无法完整拼接
- 超宽表（列数 > 阈值）
- 图表（趋势图、饼图）需要数值读回
- Stage 3 勾稽不通过且无法自动修复

处理方式：
- 把相关页面/区域截图发给 qwen3.7
- Prompt：「逐字读回表格中的科目和数值，只转录不计算」
- 输出重新进入 Stage 3 校验

### 4.4 标准化输出

```python
class ParsedAnnualReport(BaseModel):
    report_year: int
    stock_code: str
    security_name: str
    pdf_url: str
    pdf_local_path: str
    source_type: Literal["annual_report_pdf"]
    statements: FinancialStatementData
    quality: PdfParsingQuality
    evidence_pages: Dict[str, int]  # 科目 -> 页码

class FinancialStatementData(BaseModel):
    income_statement: pd.DataFrame      # 标准字段：revenue, operating_cost, net_profit, ...
    balance_sheet: pd.DataFrame         # 标准字段：total_assets, total_liabilities, ...
    cash_flow: pd.DataFrame             # 标准字段：net_operating_cash_flow, ...
    unit: str                           # yuan / wan_yuan / yi_yuan
    scope: Literal["consolidated", "parent"] = "consolidated"
    periods: List[int]

class PdfParsingQuality(BaseModel):
    digital_reach_rate: float           # 数字触达率
    auto_judgment_rate: float           # 自动判定率
    main_table_coverage: str            # 6/6
    rule_family_coverage: str           # 已实施/总规则族
    issues: List[str]
    needs_human_review: bool
```

### 4.5 财务 Agent 改造

改造 `backend/app/agents/sub_agents/financial_agent.py` 的 `run_financial_agent()`：

```python
async def run_financial_agent(enterprise_name, ...):
    listed_info = resolve_listed_company(enterprise_name)
    if listed_info:
        # 1. 优先从 CNINFO 年报 PDF 解析
        annual_reports = await fetch_annual_report_pdfs(listed_info, years=3)
        pdf_result = await parse_annual_reports_with_pipeline(annual_reports)

        if pdf_result.success and pdf_result.quality.auto_judgment_rate >= 0.85:
            rebecca_data = pdf_result.statements
            data_source = "巨潮资讯年报 PDF"
            source_type = "annual_report_pdf"
        else:
            # 2. 降级：结构化接口 + 差异校验
            structured_result = await _fetch_listed_financial_data(enterprise_name, listed_info)
            rebecca_data = structured_result.statements
            data_source = structured_result.data_source
            source_type = "investment_research_tool"
            reconciliation = await reconcile_pdf_vs_structured(pdf_result, structured_result)

        # 3. 年报全文 RAG 入库 + evidence 生成
        cninfo_evidence = build_annual_report_evidence(annual_reports, pdf_result)
        annual_report_notes = _build_annual_report_notes(rebecca_data, cninfo_result, ...)

        # 4. Rebecca 分析
        result = _run_rebecca_analysis(
            enterprise_name,
            rebecca_data,
            data_source=data_source,
            source_type=source_type,
            annual_report_notes=annual_report_notes,
            ...
        )
```

---

## 5. Evidence 与 RAG

### 5.1 Evidence 生成

每个财务指标 evidence 必须绑定：

```json
{
  "label": "营业收入",
  "value": "161.06亿",
  "source": "三安光电2024年年度报告",
  "source_name": "巨潮资讯网",
  "source_url": "https://static.cninfo.com.cn/.../6007032024.pdf",
  "source_page": 78,
  "source_type": "annual_report_pdf",
  "trust_level": "high",
  "confidence": 0.92,
  "metadata": {
    "report_year": 2024,
    "stock_code": "600703",
    "statement_type": "income_statement",
    "unit": "yuan",
    "auto_judgment_rate": 0.875
  }
}
```

### 5.2 年报全文 RAG 入库

- 使用 `backend/app/rag/pdf_knowledge_ingestion.py` 将年报 PDF 全文切片
- 元数据注入：`report_year`、`stock_code`、`source_url`、`page_number`、`statement_type`
- 支持按年度过滤、按行业别名匹配、按页码追溯

### 5.3 正文级引用

报告章节中财务结论的 `evidence_refs` 指向 evidence id，前端「查看证据」可跳转：
- 原始 PDF URL（新标签页打开）
- 页码锚点（PDF.js `#page=78`）
- 本地缓存的表格截图（HITL 复核用）

---

## 6. 降级策略

| 场景 | 处理 |
|---|---|
| 年报 PDF 下载失败 | 降级东方财富/AKShare，任务继续，evidence 标注来源边界 |
| 年报 PDF 解析后自动判定率 < 85% | 结构化接口补字段；整体标记「财务章节置信度不足」 |
| 某一年年报缺失 | 用现有年份 + 结构化接口补缺失年份 |
| 某科目 OCR 连续错误 | 该科目走视觉兜底；仍失败则标记 Research Gap |
| 四阶段管道完全失败 | 完全回退结构化接口，并在报告中明确提示数据来源 |

---

## 7. 与 PRD 指标的关系

| PRD 指标 | 本设计对应 |
|---|---|
| 数字触达率 ≥80% | PDF 中可被提取并参与勾稽的数字占比 |
| 自动判定率 ≥85% | 勾稽发现中确定性引擎自动解决的比例 |
| 主表覆盖率 6/6 | BS/CF/IS × 合并/母公司 |
| 证据深度 ≥16 项 | 年报 PDF 提供高可信 evidence |
| 正文级引用 | evidence 绑定 source_url + page |

---

## 8. 实施顺序建议

1. **评估现有 CNINFO 抽取能力**：用三安光电/欣旺达 2022-2024 年报跑 `cninfo_announcement_tool.py` + `annual_report_section_extractor.py`，确认当前能抽出什么。
2. **封装四阶段管道骨架**：先实现 MinerU → MiniCPM-V → 勾稽 → 视觉兜底的串接流程，输出标准化 JSON（不要求一次完美）。
3. **字段标准化映射**：把转录科目映射到 Rebecca 所需标准字段。
4. **改造 financial_agent**：上市公司优先走 PDF 管道，结构化接口降为校验/兜底。
5. **Evidence 与 RAG 入库**：确保 PDF URL、页码、年度进入 evidence 和知识库。
6. **回归测试**：用 10 家上市公司样例验证数字触达率和自动判定率。

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| MinerU/MiniCPM-V 在银行内网不可用 | 高 | 每阶段可独立降级；最终 fallback 结构化接口 |
| 年报 PDF 版式差异大 | 中 | 按规则 + 视觉兜底；建立 10 家公司回归样例 |
| 勾稽规则覆盖不足 | 中 | 从 23 条起步，按行业扩展规则族 |
| 解析耗时过长 | 中 | 年报解析结果缓存；同公司重复分析直接复用 |
| 证据来源从接口切到 PDF 后报告质量波动 | 高 | 保留结构化接口做 A/B 校验，差异大时人工复核 |

---

## 10. 关键文件清单

- `backend/app/agents/sub_agents/financial_agent.py`
- `backend/app/agents/tools/cninfo_announcement_tool.py`
- `backend/app/agents/tools/annual_report_section_extractor.py`
- `backend/app/engines/rebecca/parsers/financial_pdf_pipeline.py`（新增）
- `backend/app/engines/rebecca/parsers/statement_normalizer.py`（新增）
- `backend/app/engines/rebecca/parsers/accounting_validator.py`（新增）
- `backend/app/agents/tools/financial_provider_reconciliation.py`（扩展）
- `backend/app/rag/pdf_knowledge_ingestion.py`
- `backend/app/agents/evidence/evidence_store.py`

---

## 11. 验收标准

- 输入「分析三安光电财务风险」，系统下载其 2022-2024 年报 PDF。
- Rebecca 输入的三大表主要字段来自 PDF 解析，而非东方财富/AKShare。
- Evidence 中至少 50% 的财务指标绑定 `source_url = 巨潮 PDF` 且带 `source_page`。
- 数字触达率 ≥80%，自动判定率 ≥85%。
- 当年报解析失败时，任务不崩溃，明确提示数据来源降级。
- 10 家上市公司回归样例平均分 ≥75。
