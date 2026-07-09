# DDG Agent 工具 Manifest

> 单一事实来源：每个工具的**功能 / 负向边界 / 相关性分数契约 / 引导指令 / 降级工具**。供 LLM 兜底路由(`select_for_llm`)与人工审阅使用。

**相关性阈值**：`relevance_score < 0.4` 时，应采纳工具的 `guidance_on_low_relevance`。

## Financial

### `cninfo_webapi` — 巨潮 WebAPI 结构化财报
- **功能**：通过深证信(webapi.cninfo.com.cn)获取 A 股上市公司权威结构化数据：三大表、财务指标(ROE/EPS/毛利率等)、十大股东、实控人、股本变动。
- **负向边界**：
  - 仅覆盖 A 股上市公司，非上市/未上市企业无数据
  - 不返回行业研究、竞争格局或政策结论
  - 不含司法诉讼/工商行政处罚（属 legal/business 工具）
  - 只取结构化字段，PDF 表格深度解析不在本工具（见 cninfo_announcement / pdf_extraction_engine）
- **入参**：stock_code, report_date(可选, 默认最新)
- **相关性契约**：结构化字段覆盖率；关键报表缺失则 relevance 降低并 error 标注
- **低相关引导**：若企业非 A 股 → 改用 eastmoney_structured / akshare_financial；若字段缺失 → 检查 report_date 或换财报来源
- **降级/互补**：eastmoney_structured, akshare_financial
- **入口**：`app.agents.tools.cninfo_webapi_tool:fetch_balance_sheet`

### `eastmoney_structured` — 东方财富 F10 结构化数据
- **功能**：无鉴权获取 A 股 F10 结构化数据：财务摘要、股东画像、公司基础信息、股本表。输出 schema 与 cninfo_webapi 1:1 兼容，供 tool_router 切换数据源。
- **负向边界**：
  - 免费档有频率/字段限制，权威度低于巨潮直连
  - 不提供审计意见语义解读
  - 不含行业/司法/工商信息
- **入参**：stock_code, report_date(可选)
- **相关性契约**：与 cninfo 同口径；接口失败则 success=False
- **低相关引导**：作为 cninfo 的互补源；若两源都缺字段 → 用 akshare_financial 兜底或标记需人工上传财报
- **降级/互补**：cninfo_webapi, akshare_financial
- **入口**：`app.agents.tools.eastmoney_structured_tool:eastmoney_build_financial_summary`

### `akshare_financial` — AKShare 财报(兜底)
- **功能**：通过 AKShare 获取结构化财报，用于 POC 与多源兜底。依赖可选，未安装时动态加载失败。
- **负向边界**：
  - 非权威源，仅作兜底，不替代巨潮/东财
  - 部署未装 akshare 时本工具不可用
  - 不含指标解读与行业分析
- **入参**：enterprise_name, stock_code, stock_exchange
- **相关性契约**：成功拉到三表则高；否则 success=False
- **低相关引导**：仅作最后兜底；失败时应提示用户上传财报 Excel/PDF
- **降级/互补**：cninfo_webapi, eastmoney_structured
- **入口**：`app.agents.tools.akshare_financial_tool:fetch_akshare_financial_data`

### `cninfo_announcement` — 巨潮公告与年报 PDF 抽取
- **功能**：检索巨潮公告元数据与 PDF 链接，下载并抽取年报 PDF 的叙事章节（经营情况讨论、主营业务构成表）转为可审计证据。
- **负向边界**：
  - 只取公告元数据 + PDF 抽取，不替代结构化三表工具
  - 非 A 股无公告数据
  - 扫描件依赖前置 OCR，抽取质量受源文件影响
- **入参**：enterprise_name, announcement_item
- **相关性契约**：抽取到章节/表格则高；缺失章节降级并标注
- **低相关引导**：结构化数值请走 cninfo_webapi；PDF 抽取失败 → 提示用户上传财报
- **降级/互补**：pdf_extraction_engine, cninfo_webapi
- **入口**：`app.agents.tools.cninfo_announcement_tool:fetch_and_extract_annual_report_pdf`

### `listed_company_public_info` — 上市公司公开信息包
- **功能**：汇总 A 股上市公司轻量可审计公开上下文：经营评述、主营业务构成、公告线索、质押/担保线索、行业地位、研报线索。
- **负向边界**：
  - 不替代权威三表（cninfo/eastmoney）
  - 研报/新闻观点仅供参考，非尽调结论
  - 不含司法诉讼与工商行政处罚全文
- **入参**：enterprise_name, stock_code, stock_exchange
- **相关性契约**：能解析到证券信息则高；否则 success=False
- **低相关引导**：需权威财务请走 cninfo_webapi；需工商/司法请走 yuandian_*
- **降级/互补**：cninfo_webapi, yuandian_company
- **入口**：`app.agents.tools.listed_company_public_info_tool:fetch_listed_company_public_info_data`

### `financial_provider_reconciliation` — 多源财报交叉校验
- **功能**：对 cninfo/eastmoney/akshare 的结构化三表做勾稽比对，输出差异项与数据缺口，供证据可信度评估。
- **负向边界**：
  - 不做指标解读或风险研判（那是 Rebecca 引擎/LLM 的事）
  - 不抓取数据，只比对调用方传入的已取数据
- **入参**：primary_provider, primary_statements, secondary_provider, secondary_statements
- **相关性契约**：差异在阈值内则高；超出阈值产出 gap 列表
- **低相关引导**：出现重大差异时应提示人工复核或要求上传原始财报
- **入口**：`app.agents.tools.financial_provider_reconciliation:reconcile_financial_providers`

### `pdf_extraction_engine` — 年报 PDF 分级抽取引擎
- **功能**：年报 PDF 分级抽取：MinerU(复杂版面/扫描件优先) → pdfplumber(主) → pymupdf(回退)，输出文本+表格。
- **负向边界**：
  - 抽取为文本/表格，不解析为三大表 schema（schema 对齐由 rebecca.parsers 完成）
  - 扫描件依赖 OCR 前置，质量受源文件影响
- **入参**：pdf_bytes, url(可选)
- **相关性契约**：成功抽出文本/表格则高；全失败 success=False
- **低相关引导**：抽取失败 → 提示用户上传更清晰的财报或 Excel
- **降级/互补**：cninfo_announcement
- **入口**：`app.agents.tools.pdf_extraction_engine:extract_pdf`

### `annual_report_section_extractor` — 年报章节抽取器
- **功能**：从年报抽取高价值叙事章节（经营情况讨论与分析、主营业务构成等）并转为证据，供深度归因。
- **负向边界**：
  - 仅适用数字 PDF；章节缺失则降级
  - 不抽取结构化数值表（见 pdf_extraction_engine）
- **入参**：extraction_result, context_chars
- **相关性契约**：抽到优先章节则高；无匹配章节则低
- **低相关引导**：章节缺失 → 依赖公开信息包或提示上传财报
- **降级/互补**：listed_company_public_info
- **入口**：`app.agents.tools.annual_report_section_extractor:extract_all_sections`

## Industry

### `industry_classifier` — 行业四级代码识别
- **功能**：识别企业所属国民经济行业四级代码，并映射到行业分析知识库。规则候选打分 → 语义加权 → 可选 LLM 裁判。
- **负向边界**：
  - 只做行业分类，不返回行业分析结论
  - 不处理具体企业财务/司法数据
- **入参**：enterprise_name, business_scope, extra_context, enable_llm
- **相关性契约**：命中行业代码则高；候选分散则降并建议 LLM 裁判
- **低相关引导**：候选分歧大 → 调用 industry_llm_classifier；scope 含泛化尾词时谨慎
- **降级/互补**：industry_llm_classifier
- **入口**：`app.agents.tools.industry_classifier_tool:classify_industry`

### `industry_llm_classifier` — 行业分类 LLM 裁判
- **功能**：对规则产出的行业候选代码做 LLM 语义裁判，解决经营范围含进出口等泛化尾词导致的误判。
- **负向边界**：
  - 不独立使用，依赖上游候选
  - 不返回行业分析，只定类
- **入参**：enterprise_name, business_scope, extra_context, candidates
- **相关性契约**：LLM 选定候选则高；否则返回失败载荷
- **低相关引导**：LLM 也无法判定时 → 回退行业知识库按关键词检索
- **降级/互补**：industry_market_data
- **入口**：`app.agents.tools.industry_llm_classifier:adjudicate_industry_with_llm`

### `industry_market_data` — 行业市场数据
- **功能**：获取行业指数走势(akshare)，并通过公开搜索补充行业规模、增速、集中度、竞争格局、政策、产业链线索。
- **负向边界**：
  - 不含具体企业财务数据（属 financial）
  - 政策以公开检索为准，非官方法规全文（法规见 yuandian_legal）
  - 搜索结果权威性低于权威库，需标注来源
- **入参**：industry_name, max_results
- **相关性契约**：指数/搜索命中则高；行业名过泛时召回噪声大
- **低相关引导**：行业名模糊 → 先用 industry_classifier 锁定标准行业；补权威政策走 yuandian_legal
- **降级/互补**：research_report_search, yuandian_legal
- **入口**：`app.agents.tools.industry_market_data_tool:get_industry_index_data`

### `research_report_search` — 研报搜索
- **功能**：组合 Bocha 与 SearXNG 检索中文行业/券商研报，优先 Bocha(配置 Key)，失败回退 SearXNG，结果归一化+去重+相关度排序。
- **负向边界**：
  - 研报观点仅供参考，不替代权威数据/法规
  - 不含企业工商/司法信息
- **入参**：query, max_results, industry_name(可选)
- **相关性契约**：命中研报则中高；无结果则低
- **低相关引导**：无研报 → 用 industry_market_data 补行业宏观；需要法规走 yuandian_legal
- **降级/互补**：industry_market_data, bocha_search
- **入口**：`app.agents.tools.research_report_search_tool:search_research_reports`

### `research_report_extractor` — 研报 PDF 抽取
- **功能**：下载并抽取研报 PDF 原始文本，交给共享知识库分片管线，供 RAG 检索。
- **负向边界**：
  - 不解析年报结构，只抽原始文本
  - 不自带分析，仅作为知识库入库
- **入参**：url, title
- **相关性契约**：抽取成功则高；下载失败 success=False
- **低相关引导**：抽取失败 → 用 research_report_search 换来源
- **降级/互补**：research_report_search
- **入口**：`app.agents.tools.research_report_tool:extract_research_report_from_url`

## Business

### `yuandian_company` — 元典企业工商/风险画像
- **功能**：通过元典 Open Platform(MCP) 获取企业基础信息(股东/法人/注册资本)、涉诉统计、经营异常、行政处罚、股权冻结等风险摘要，构建工商+司法风险画像。覆盖非上市民企。
- **负向边界**：
  - 不含财务三大表（属 financial）
  - 不含法规全文（属 yuandian_legal）
  - 返回风险摘要，不返回完整裁判文书
- **入参**：enterprise_name, top_k
- **相关性契约**：匹配到企业且返回风险项则高；无匹配则低
- **低相关引导**：名称匹配失败 → 核对全称/统一社会信用代码；需法规全文走 yuandian_legal
- **降级/互补**：yuandian_legal, listed_company_public_info
- **入口**：`app.agents.tools.yuandian_company_tool:build_business_profile`

## Legal

### `yuandian_legal` — 元典法规/案例检索
- **功能**：通过元典 Open Platform(MCP) 做法律法规语义检索、裁判文书/案例语义检索，构建企业司法风险画像(涉案金额、原被告、审理法院等级等结构化摘要)。
- **负向边界**：
  - 不返回完整文书内容，只返回结构化摘要
  - 不含财务/工商信息
  - 不输出授信结论或风险评级（那是报告引擎的事）
- **入参**：enterprise_name, query, top_k
- **相关性契约**：命中法规/案例则高；无匹配则低
- **低相关引导**：需工商风险走 yuandian_company；需政策导向走 industry_market_data
- **降级/互补**：yuandian_company, searxng_search
- **入口**：`app.agents.tools.yuandian_legal_tool:build_legal_risk_profile`

## Search

### `bocha_search` — Bocha 公开网页搜索
- **功能**：中文公开网络感知搜索，发现候选公开证据（新闻/官网/舆情）。配置 API Key 后使用。
- **负向边界**：
  - 只发现候选证据，不替代权威工商/司法/财务源
  - 不保证权威性与时效性，需交叉验证
  - 不含结构化财报/工商/法规
- **入参**：query, max_results, freshness, include, exclude
- **相关性契约**：返回结果数 + 域名匹配度；无结果=0.0
- **低相关引导**：低相关 → 切 searxng_search 或 industry_market_data；权威信息请走对应领域工具
- **降级/互补**：searxng_search, industry_market_data
- **入口**：`app.agents.tools.bocha_search_tool:search_with_bocha`

### `searxng_search` — SearXNG 聚合搜索
- **功能**：通过 SearXNG 实例聚合公开搜索，归一化结果，作为公开证据发现网关。
- **负向边界**：
  - 同 bocha：候选证据，不替代权威源
  - 依赖自建/第三方 SearXNG 实例可用性
- **入参**：query, max_results, categories, language, base_url
- **相关性契约**：返回结果数归一化；实例不可达则 success=False
- **低相关引导**：实例不可用 → 用 bocha_search；需权威数据走领域工具
- **降级/互补**：bocha_search
- **入口**：`app.agents.tools.searxng_search_tool:search_with_searxng`

### `mcp_search` — 可选 MCP 搜索(Exa 等)
- **功能**：配置后通过 Exa 等 MCP 提供方补充公开尽调信号，结果归一化为统一形状。
- **负向边界**：
  - 可选能力，未配置则返回空
  - 不替代权威工商/司法/财务源
- **入参**：query, max_results, providers
- **相关性契约**：有配置且命中则中高；未配置=0.0
- **低相关引导**：未配置 → 用 bocha_search / searxng_search
- **降级/互补**：bocha_search, searxng_search
- **入口**：`app.agents.tools.mcp_search_tool:search_with_mcp_providers`

## Infra

### `cninfo_token_manager` — 巨潮 Token 管理器  _(不暴露给 LLM)_
- **功能**：管理深证信 access_token 自动刷新与失效失效，供 cninfo_webapi 内部调用。
- **负向边界**：
  - 不直接取业务数据，仅凭证管理
  - 不是 LLM 可选工具
- **入参**：(无)
- **相关性契约**：返回有效 token 则高
- **低相关引导**：401 时 invalidate 后重试
- **入口**：`app.agents.tools.cninfo_token_manager:get_cninfo_access_token`

### `yuandian_mcp_client` — 元典 MCP 客户端  _(不暴露给 LLM)_
- **功能**：元典 Open Platform 的 streamable-HTTP MCP 客户端，执行 initialize 握手并调用 law/case/company 端点。
- **负向边界**：
  - 不直接对外，属基础设施
  - 不是 LLM 可选工具
- **入参**：endpoint, payload
- **相关性契约**：握手+调用成功则高
- **低相关引导**：连接失败 → 对应 yuandian_* 工具降级返回结构化失败
- **入口**：`app.agents.tools.yuandian_mcp_client:call_yuandian`

## Resolve

### `listed_company_resolver` — 上市公司解析器
- **功能**：根据企业名或股票代码解析 A 股上市公司证券信息（代码/交易所），供后续财务工具定位。
- **负向边界**：
  - 不取财报；非上市返回空
  - 不做行业分类
- **入参**：enterprise_name, stock_code, stock_exchange
- **相关性契约**：解析到证券信息则高；否则低
- **低相关引导**：解析失败 → 视为非上市，走 yuandian_company 工商路径
- **降级/互补**：yuandian_company
- **入口**：`app.agents.tools.listed_company_tool:resolve_listed_company`

## Deprecated (重构中已移除的 stub)

- `authoritative_business` — 权威工商(已移除 stub)：架构重构中已移除。当前仅返回结构化失败载荷，供 business/industry agent 降级。 降级走 yuandian_company。
- `authoritative_legal` — 权威司法(已移除 stub)：架构重构中已移除。当前仅返回结构化失败载荷，供 legal agent 降级。 降级走 yuandian_legal。
- `business_search_tavily` — 工商搜索 Tavily(已移除 stub)：架构重构中已移除(Tavily 版)。仅返回结构化失败，不伪造数据。 降级走 yuandian_company。
- `legal_search_tavily` — 司法搜索 Tavily(已移除 stub)：架构重构中已移除(Tavily 版)。仅返回结构化失败，不伪造数据。 降级走 yuandian_legal。
- `legacy_search_wrapper` — 旧版搜索兼容包装(已弃用)：旧版 sub-agent 的兼容包装，保留导入兼容但不伪造业务/法律/财务事实，内部转调 DeepResearch 工具。 降级走 bocha_search, searxng_search。
