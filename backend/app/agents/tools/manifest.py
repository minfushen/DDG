"""Tool manifest for the DDG Agent due-diligence toolkit.

Purpose
-------
This module is the **single source of truth** describing every tool the
research engine can call. It documents, for each tool:

* ``description``            – what the tool does (功能)
* ``negative_boundaries``    – what the tool explicitly does NOT do (负向边界)
* ``relevance_contract``     – how the tool computes ``relevance_score``
* ``guidance_on_low_relevance`` – the instruction returned to an LLM when the
  result is weak (引导指令)
* ``fallback_to``            – which tools to try next

Why this exists
---------------
``research_engine/tool_router.py`` routes by hard-coded ``category`` (financial /
industry / legal / business). That avoids LLM tool-mis-selection entirely. But the
product spec also calls for an **LLM fallback** when the category is ambiguous.
This manifest makes that fallback possible: ``select_for_llm()`` returns a ranked
candidate list with descriptions + negative boundaries so an LLM can pick the
right tool instead of guessing.

Design notes / safety
---------------------
* Entry points are stored as lazy ``"module:func"`` strings, so importing this
  manifest never pulls heavy optional deps (akshare, yuandian MCP, ...).
* Tools removed during refactoring are kept with ``status="deprecated"`` and
  ``exposed_to_llm=False`` so the manifest stays honest and the LLM never calls a
  stub that would silently return a structured failure.
* No existing routing logic is modified. This file is additive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Relevance score is a float in [0, 1].
# Below this threshold the tool's ``guidance_on_low_relevance`` should be honored
# (switch tool / rephrase query / fall back to web).
LOW_RELEVANCE_THRESHOLD = 0.4


@dataclass
class ToolManifest:
    key: str
    display_name: str
    category: str  # financial | industry | business | legal | search | infra | resolve
    entry: str  # "module:func" lazy reference, never imported here
    description: str
    negative_boundaries: List[str] = field(default_factory=list)
    accepts: List[str] = field(default_factory=list)
    relevance_contract: str = "按命中记录数/权威度归一化；无命中=0.0"
    guidance_on_low_relevance: str = "换关键词或切换互补工具，不要据此下结论"
    fallback_to: List[str] = field(default_factory=list)
    status: str = "active"  # active | deprecated
    exposed_to_llm: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Manifest
# ─────────────────────────────────────────────────────────────────────────────
TOOL_MANIFEST: List[ToolManifest] = [
    # ----------------------------- Financial --------------------------------
    ToolManifest(
        key="cninfo_webapi",
        display_name="巨潮 WebAPI 结构化财报",
        category="financial",
        entry="app.agents.tools.cninfo_webapi_tool:fetch_balance_sheet",
        description="通过深证信(webapi.cninfo.com.cn)获取 A 股上市公司权威结构化数据：三大表、财务指标(ROE/EPS/毛利率等)、十大股东、实控人、股本变动。",
        negative_boundaries=[
            "仅覆盖 A 股上市公司，非上市/未上市企业无数据",
            "不返回行业研究、竞争格局或政策结论",
            "不含司法诉讼/工商行政处罚（属 legal/business 工具）",
            "只取结构化字段，PDF 表格深度解析不在本工具（见 cninfo_announcement / pdf_extraction_engine）",
        ],
        accepts=["stock_code", "report_date(可选, 默认最新)"],
        relevance_contract="结构化字段覆盖率；关键报表缺失则 relevance 降低并 error 标注",
        guidance_on_low_relevance="若企业非 A 股 → 改用 eastmoney_structured / akshare_financial；若字段缺失 → 检查 report_date 或换财报来源",
        fallback_to=["eastmoney_structured", "akshare_financial"],
    ),
    ToolManifest(
        key="eastmoney_structured",
        display_name="东方财富 F10 结构化数据",
        category="financial",
        entry="app.agents.tools.eastmoney_structured_tool:eastmoney_build_financial_summary",
        description="无鉴权获取 A 股 F10 结构化数据：财务摘要、股东画像、公司基础信息、股本表。输出 schema 与 cninfo_webapi 1:1 兼容，供 tool_router 切换数据源。",
        negative_boundaries=[
            "免费档有频率/字段限制，权威度低于巨潮直连",
            "不提供审计意见语义解读",
            "不含行业/司法/工商信息",
        ],
        accepts=["stock_code", "report_date(可选)"],
        relevance_contract="与 cninfo 同口径；接口失败则 success=False",
        guidance_on_low_relevance="作为 cninfo 的互补源；若两源都缺字段 → 用 akshare_financial 兜底或标记需人工上传财报",
        fallback_to=["cninfo_webapi", "akshare_financial"],
    ),
    ToolManifest(
        key="akshare_financial",
        display_name="AKShare 财报(兜底)",
        category="financial",
        entry="app.agents.tools.akshare_financial_tool:fetch_akshare_financial_data",
        description="通过 AKShare 获取结构化财报，用于 POC 与多源兜底。依赖可选，未安装时动态加载失败。",
        negative_boundaries=[
            "非权威源，仅作兜底，不替代巨潮/东财",
            "部署未装 akshare 时本工具不可用",
            "不含指标解读与行业分析",
        ],
        accepts=["enterprise_name", "stock_code", "stock_exchange"],
        relevance_contract="成功拉到三表则高；否则 success=False",
        guidance_on_low_relevance="仅作最后兜底；失败时应提示用户上传财报 Excel/PDF",
        fallback_to=["cninfo_webapi", "eastmoney_structured"],
    ),
    ToolManifest(
        key="cninfo_announcement",
        display_name="巨潮公告与年报 PDF 抽取",
        category="financial",
        entry="app.agents.tools.cninfo_announcement_tool:fetch_and_extract_annual_report_pdf",
        description="检索巨潮公告元数据与 PDF 链接，下载并抽取年报 PDF 的叙事章节（经营情况讨论、主营业务构成表）转为可审计证据。",
        negative_boundaries=[
            "只取公告元数据 + PDF 抽取，不替代结构化三表工具",
            "非 A 股无公告数据",
            "扫描件依赖前置 OCR，抽取质量受源文件影响",
        ],
        accepts=["enterprise_name", "announcement_item"],
        relevance_contract="抽取到章节/表格则高；缺失章节降级并标注",
        guidance_on_low_relevance="结构化数值请走 cninfo_webapi；PDF 抽取失败 → 提示用户上传财报",
        fallback_to=["pdf_extraction_engine", "cninfo_webapi"],
    ),
    ToolManifest(
        key="listed_company_public_info",
        display_name="上市公司公开信息包",
        category="financial",
        entry="app.agents.tools.listed_company_public_info_tool:fetch_listed_company_public_info_data",
        description="汇总 A 股上市公司轻量可审计公开上下文：经营评述、主营业务构成、公告线索、质押/担保线索、行业地位、研报线索。",
        negative_boundaries=[
            "不替代权威三表（cninfo/eastmoney）",
            "研报/新闻观点仅供参考，非尽调结论",
            "不含司法诉讼与工商行政处罚全文",
        ],
        accepts=["enterprise_name", "stock_code", "stock_exchange"],
        relevance_contract="能解析到证券信息则高；否则 success=False",
        guidance_on_low_relevance="需权威财务请走 cninfo_webapi；需工商/司法请走 yuandian_*",
        fallback_to=["cninfo_webapi", "yuandian_company"],
    ),
    ToolManifest(
        key="financial_provider_reconciliation",
        display_name="多源财报交叉校验",
        category="financial",
        entry="app.agents.tools.financial_provider_reconciliation:reconcile_financial_providers",
        description="对 cninfo/eastmoney/akshare 的结构化三表做勾稽比对，输出差异项与数据缺口，供证据可信度评估。",
        negative_boundaries=[
            "不做指标解读或风险研判（那是 Rebecca 引擎/LLM 的事）",
            "不抓取数据，只比对调用方传入的已取数据",
        ],
        accepts=["primary_provider", "primary_statements", "secondary_provider", "secondary_statements"],
        relevance_contract="差异在阈值内则高；超出阈值产出 gap 列表",
        guidance_on_low_relevance="出现重大差异时应提示人工复核或要求上传原始财报",
        fallback_to=[],
    ),
    ToolManifest(
        key="pdf_extraction_engine",
        display_name="年报 PDF 分级抽取引擎",
        category="financial",
        entry="app.agents.tools.pdf_extraction_engine:extract_pdf",
        description="年报 PDF 分级抽取：MinerU(复杂版面/扫描件优先) → pdfplumber(主) → pymupdf(回退)，输出文本+表格。",
        negative_boundaries=[
            "抽取为文本/表格，不解析为三大表 schema（schema 对齐由 rebecca.parsers 完成）",
            "扫描件依赖 OCR 前置，质量受源文件影响",
        ],
        accepts=["pdf_bytes", "url(可选)"],
        relevance_contract="成功抽出文本/表格则高；全失败 success=False",
        guidance_on_low_relevance="抽取失败 → 提示用户上传更清晰的财报或 Excel",
        fallback_to=["cninfo_announcement"],
    ),
    ToolManifest(
        key="annual_report_section_extractor",
        display_name="年报章节抽取器",
        category="financial",
        entry="app.agents.tools.annual_report_section_extractor:extract_all_sections",
        description="从年报抽取高价值叙事章节（经营情况讨论与分析、主营业务构成等）并转为证据，供深度归因。",
        negative_boundaries=[
            "仅适用数字 PDF；章节缺失则降级",
            "不抽取结构化数值表（见 pdf_extraction_engine）",
        ],
        accepts=["extraction_result", "context_chars"],
        relevance_contract="抽到优先章节则高；无匹配章节则低",
        guidance_on_low_relevance="章节缺失 → 依赖公开信息包或提示上传财报",
        fallback_to=["listed_company_public_info"],
    ),

    # ----------------------------- Industry ---------------------------------
    ToolManifest(
        key="industry_classifier",
        display_name="行业四级代码识别",
        category="industry",
        entry="app.agents.tools.industry_classifier_tool:classify_industry",
        description="识别企业所属国民经济行业四级代码，并映射到行业分析知识库。规则候选打分 → 语义加权 → 可选 LLM 裁判。",
        negative_boundaries=[
            "只做行业分类，不返回行业分析结论",
            "不处理具体企业财务/司法数据",
        ],
        accepts=["enterprise_name", "business_scope", "extra_context", "enable_llm"],
        relevance_contract="命中行业代码则高；候选分散则降并建议 LLM 裁判",
        guidance_on_low_relevance="候选分歧大 → 调用 industry_llm_classifier；scope 含泛化尾词时谨慎",
        fallback_to=["industry_llm_classifier"],
    ),
    ToolManifest(
        key="industry_llm_classifier",
        display_name="行业分类 LLM 裁判",
        category="industry",
        entry="app.agents.tools.industry_llm_classifier:adjudicate_industry_with_llm",
        description="对规则产出的行业候选代码做 LLM 语义裁判，解决经营范围含进出口等泛化尾词导致的误判。",
        negative_boundaries=[
            "不独立使用，依赖上游候选",
            "不返回行业分析，只定类",
        ],
        accepts=["enterprise_name", "business_scope", "extra_context", "candidates"],
        relevance_contract="LLM 选定候选则高；否则返回失败载荷",
        guidance_on_low_relevance="LLM 也无法判定时 → 回退行业知识库按关键词检索",
        fallback_to=["industry_market_data"],
    ),
    ToolManifest(
        key="industry_market_data",
        display_name="行业市场数据",
        category="industry",
        entry="app.agents.tools.industry_market_data_tool:get_industry_index_data",
        description="获取行业指数走势(akshare)，并通过公开搜索补充行业规模、增速、集中度、竞争格局、政策、产业链线索。",
        negative_boundaries=[
            "不含具体企业财务数据（属 financial）",
            "政策以公开检索为准，非官方法规全文（法规见 yuandian_legal）",
            "搜索结果权威性低于权威库，需标注来源",
        ],
        accepts=["industry_name", "max_results"],
        relevance_contract="指数/搜索命中则高；行业名过泛时召回噪声大",
        guidance_on_low_relevance="行业名模糊 → 先用 industry_classifier 锁定标准行业；补权威政策走 yuandian_legal",
        fallback_to=["research_report_search", "yuandian_legal"],
    ),
    ToolManifest(
        key="research_report_search",
        display_name="研报搜索",
        category="industry",
        entry="app.agents.tools.research_report_search_tool:search_research_reports",
        description="组合 Bocha 与 SearXNG 检索中文行业/券商研报，优先 Bocha(配置 Key)，失败回退 SearXNG，结果归一化+去重+相关度排序。",
        negative_boundaries=[
            "研报观点仅供参考，不替代权威数据/法规",
            "不含企业工商/司法信息",
        ],
        accepts=["query", "max_results", "industry_name(可选)"],
        relevance_contract="命中研报则中高；无结果则低",
        guidance_on_low_relevance="无研报 → 用 industry_market_data 补行业宏观；需要法规走 yuandian_legal",
        fallback_to=["industry_market_data", "bocha_search"],
    ),
    ToolManifest(
        key="research_report_extractor",
        display_name="研报 PDF 抽取",
        category="industry",
        entry="app.agents.tools.research_report_tool:extract_research_report_from_url",
        description="下载并抽取研报 PDF 原始文本，交给共享知识库分片管线，供 RAG 检索。",
        negative_boundaries=[
            "不解析年报结构，只抽原始文本",
            "不自带分析，仅作为知识库入库",
        ],
        accepts=["url", "title"],
        relevance_contract="抽取成功则高；下载失败 success=False",
        guidance_on_low_relevance="抽取失败 → 用 research_report_search 换来源",
        fallback_to=["research_report_search"],
    ),

    # ----------------------------- Business ---------------------------------
    ToolManifest(
        key="yuandian_company",
        display_name="元典企业工商/风险画像",
        category="business",
        entry="app.agents.tools.yuandian_company_tool:build_business_profile",
        description="通过元典 Open Platform(MCP) 获取企业基础信息(股东/法人/注册资本)、涉诉统计、经营异常、行政处罚、股权冻结等风险摘要，构建工商+司法风险画像。覆盖非上市民企。",
        negative_boundaries=[
            "不含财务三大表（属 financial）",
            "不含法规全文（属 yuandian_legal）",
            "返回风险摘要，不返回完整裁判文书",
        ],
        accepts=["enterprise_name", "top_k"],
        relevance_contract="匹配到企业且返回风险项则高；无匹配则低",
        guidance_on_low_relevance="名称匹配失败 → 核对全称/统一社会信用代码；需法规全文走 yuandian_legal",
        fallback_to=["yuandian_legal", "listed_company_public_info"],
    ),

    # ------------------------------ Legal -----------------------------------
    ToolManifest(
        key="yuandian_legal",
        display_name="元典法规/案例检索",
        category="legal",
        entry="app.agents.tools.yuandian_legal_tool:build_legal_risk_profile",
        description="通过元典 Open Platform(MCP) 做法律法规语义检索、裁判文书/案例语义检索，构建企业司法风险画像(涉案金额、原被告、审理法院等级等结构化摘要)。",
        negative_boundaries=[
            "不返回完整文书内容，只返回结构化摘要",
            "不含财务/工商信息",
            "不输出授信结论或风险评级（那是报告引擎的事）",
        ],
        accepts=["enterprise_name", "query", "top_k"],
        relevance_contract="命中法规/案例则高；无匹配则低",
        guidance_on_low_relevance="需工商风险走 yuandian_company；需政策导向走 industry_market_data",
        fallback_to=["yuandian_company", "searxng_search"],
    ),

    # ------------------------------ Search ----------------------------------
    ToolManifest(
        key="bocha_search",
        display_name="Bocha 公开网页搜索",
        category="search",
        entry="app.agents.tools.bocha_search_tool:search_with_bocha",
        description="中文公开网络感知搜索，发现候选公开证据（新闻/官网/舆情）。配置 API Key 后使用。",
        negative_boundaries=[
            "只发现候选证据，不替代权威工商/司法/财务源",
            "不保证权威性与时效性，需交叉验证",
            "不含结构化财报/工商/法规",
        ],
        accepts=["query", "max_results", "freshness", "include", "exclude"],
        relevance_contract="返回结果数 + 域名匹配度；无结果=0.0",
        guidance_on_low_relevance="低相关 → 切 searxng_search 或 industry_market_data；权威信息请走对应领域工具",
        fallback_to=["searxng_search", "industry_market_data"],
    ),
    ToolManifest(
        key="searxng_search",
        display_name="SearXNG 聚合搜索",
        category="search",
        entry="app.agents.tools.searxng_search_tool:search_with_searxng",
        description="通过 SearXNG 实例聚合公开搜索，归一化结果，作为公开证据发现网关。",
        negative_boundaries=[
            "同 bocha：候选证据，不替代权威源",
            "依赖自建/第三方 SearXNG 实例可用性",
        ],
        accepts=["query", "max_results", "categories", "language", "base_url"],
        relevance_contract="返回结果数归一化；实例不可达则 success=False",
        guidance_on_low_relevance="实例不可用 → 用 bocha_search；需权威数据走领域工具",
        fallback_to=["bocha_search"],
    ),
    ToolManifest(
        key="mcp_search",
        display_name="可选 MCP 搜索(Exa 等)",
        category="search",
        entry="app.agents.tools.mcp_search_tool:search_with_mcp_providers",
        description="配置后通过 Exa 等 MCP 提供方补充公开尽调信号，结果归一化为统一形状。",
        negative_boundaries=[
            "可选能力，未配置则返回空",
            "不替代权威工商/司法/财务源",
        ],
        accepts=["query", "max_results", "providers"],
        relevance_contract="有配置且命中则中高；未配置=0.0",
        guidance_on_low_relevance="未配置 → 用 bocha_search / searxng_search",
        fallback_to=["bocha_search", "searxng_search"],
    ),

    # --------------------------- Infra / Resolve ----------------------------
    ToolManifest(
        key="cninfo_token_manager",
        display_name="巨潮 Token 管理器",
        category="infra",
        entry="app.agents.tools.cninfo_token_manager:get_cninfo_access_token",
        description="管理深证信 access_token 自动刷新与失效失效，供 cninfo_webapi 内部调用。",
        negative_boundaries=["不直接取业务数据，仅凭证管理", "不是 LLM 可选工具"],
        accepts=["(无)"],
        relevance_contract="返回有效 token 则高",
        guidance_on_low_relevance="401 时 invalidate 后重试",
        fallback_to=[],
        exposed_to_llm=False,
    ),
    ToolManifest(
        key="listed_company_resolver",
        display_name="上市公司解析器",
        category="resolve",
        entry="app.agents.tools.listed_company_tool:resolve_listed_company",
        description="根据企业名或股票代码解析 A 股上市公司证券信息（代码/交易所），供后续财务工具定位。",
        negative_boundaries=["不取财报；非上市返回空", "不做行业分类"],
        accepts=["enterprise_name", "stock_code", "stock_exchange"],
        relevance_contract="解析到证券信息则高；否则低",
        guidance_on_low_relevance="解析失败 → 视为非上市，走 yuandian_company 工商路径",
        fallback_to=["yuandian_company"],
    ),
    ToolManifest(
        key="yuandian_mcp_client",
        display_name="元典 MCP 客户端",
        category="infra",
        entry="app.agents.tools.yuandian_mcp_client:call_yuandian",
        description="元典 Open Platform 的 streamable-HTTP MCP 客户端，执行 initialize 握手并调用 law/case/company 端点。",
        negative_boundaries=["不直接对外，属基础设施", "不是 LLM 可选工具"],
        accepts=["endpoint", "payload"],
        relevance_contract="握手+调用成功则高",
        guidance_on_low_relevance="连接失败 → 对应 yuandian_* 工具降级返回结构化失败",
        fallback_to=[],
        exposed_to_llm=False,
    ),

    # --------------------------- Deprecated stubs ---------------------------
    ToolManifest(
        key="authoritative_business",
        display_name="权威工商(已移除 stub)",
        category="business",
        entry="app.agents.tools.authoritative_business_tool:(stub)",
        description="架构重构中已移除。当前仅返回结构化失败载荷，供 business/industry agent 降级。",
        negative_boundaries=["已废弃，不要调用", "不返回任何真实工商数据"],
        accepts=[],
        relevance_contract="恒为 success=False",
        guidance_on_low_relevance="改用 yuandian_company",
        fallback_to=["yuandian_company"],
        status="deprecated",
        exposed_to_llm=False,
    ),
    ToolManifest(
        key="authoritative_legal",
        display_name="权威司法(已移除 stub)",
        category="legal",
        entry="app.agents.tools.authoritative_legal_tool:(stub)",
        description="架构重构中已移除。当前仅返回结构化失败载荷，供 legal agent 降级。",
        negative_boundaries=["已废弃，不要调用", "不返回任何真实司法数据"],
        accepts=[],
        relevance_contract="恒为 success=False",
        guidance_on_low_relevance="改用 yuandian_legal",
        fallback_to=["yuandian_legal"],
        status="deprecated",
        exposed_to_llm=False,
    ),
    ToolManifest(
        key="business_search_tavily",
        display_name="工商搜索 Tavily(已移除 stub)",
        category="business",
        entry="app.agents.tools.business_search_tool:(stub)",
        description="架构重构中已移除(Tavily 版)。仅返回结构化失败，不伪造数据。",
        negative_boundaries=["已废弃，不要调用"],
        accepts=[],
        relevance_contract="恒为 success=False",
        guidance_on_low_relevance="改用 yuandian_company",
        fallback_to=["yuandian_company"],
        status="deprecated",
        exposed_to_llm=False,
    ),
    ToolManifest(
        key="legal_search_tavily",
        display_name="司法搜索 Tavily(已移除 stub)",
        category="legal",
        entry="app.agents.tools.legal_search_tool:(stub)",
        description="架构重构中已移除(Tavily 版)。仅返回结构化失败，不伪造数据。",
        negative_boundaries=["已废弃，不要调用"],
        accepts=[],
        relevance_contract="恒为 success=False",
        guidance_on_low_relevance="改用 yuandian_legal",
        fallback_to=["yuandian_legal"],
        status="deprecated",
        exposed_to_llm=False,
    ),
    ToolManifest(
        key="legacy_search_wrapper",
        display_name="旧版搜索兼容包装(已弃用)",
        category="search",
        entry="app.agents.tools.search_tool:(wrapper)",
        description="旧版 sub-agent 的兼容包装，保留导入兼容但不伪造业务/法律/财务事实，内部转调 DeepResearch 工具。",
        negative_boundaries=["不独立提供搜索能力", "仅兼容旧调用"],
        accepts=[],
        relevance_contract="转调结果",
        guidance_on_low_relevance="新代码直接用 bocha_search / searxng_search",
        fallback_to=["bocha_search", "searxng_search"],
        status="deprecated",
        exposed_to_llm=False,
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_manifest() -> List[ToolManifest]:
    """Return the full manifest (active + deprecated)."""
    return TOOL_MANIFEST


def active_tools() -> List[ToolManifest]:
    """Tools an LLM is allowed to select from."""
    return [t for t in TOOL_MANIFEST if t.status == "active" and t.exposed_to_llm]


def by_key(key: str) -> Optional[ToolManifest]:
    for t in TOOL_MANIFEST:
        if t.key == key:
            return t
    return None


def build_tool_result(
    success: bool,
    evidence: List[Dict[str, Any]],
    source: str,
    error: str = "",
    relevance_score: float = 0.0,
    guidance: str = "",
) -> Dict[str, Any]:
    """Standardize a tool's return value.

    Every tool should wrap its output in this shape so the orchestrator and any
    LLM fallback router can rely on a consistent ``relevance_score`` + ``guidance``
    contract (ACI principle: 返回语义化信息 + 结果反馈闭环).
    """
    return {
        "success": success,
        "evidence": evidence,
        "source": source,
        "error": error,
        "relevance_score": round(max(0.0, min(1.0, float(relevance_score))), 2),
        "guidance": guidance,
    }


def select_for_llm(
    query: str,
    category: Optional[str] = None,
    threshold: float = LOW_RELEVANCE_THRESHOLD,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Rank candidate tools for an LLM fallback router.

    Given an ambiguous user intent, return the best tools with their negative
    boundaries + guidance so the LLM can pick instead of guessing. Pure keyword
    + category scoring (no nested LLM call); the LLM consumes the output.

    Priority: exact-category active tools first, then cross-category ``search``
    tools as universal candidates, scored by keyword overlap with
    description + negative boundaries.
    """
    q = query.lower()
    candidates = active_tools()
    scored = []
    for t in candidates:
        # category match is a strong signal
        cat_bonus = 1.0 if (category and t.category == category) else 0.0
        # search tools are always reasonable universal candidates
        universal = 0.3 if t.category == "search" else 0.0
        text = (t.display_name + " " + t.description + " " +
                " ".join(t.negative_boundaries)).lower()
        overlap = sum(1 for tok in q.split() if tok and tok in text)
        score = cat_bonus + universal + 0.5 * overlap
        if score <= 0 and not (category and t.category == category):
            continue
        scored.append((score, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, t in scored[:top_k]:
        out.append({
            "key": t.key,
            "display_name": t.display_name,
            "category": t.category,
            "description": t.description,
            "negative_boundaries": t.negative_boundaries,
            "accepts": t.accepts,
            "guidance_on_low_relevance": t.guidance_on_low_relevance,
            "fallback_to": t.fallback_to,
            "match_score": round(score, 2),
        })
    return out


def render_markdown() -> str:
    """Render a human-readable manifest document (mirrors docs/tools_manifest.md)."""
    lines = ["# DDG Agent 工具 Manifest", ""]
    lines.append("> 单一事实来源：每个工具的**功能 / 负向边界 / 相关性分数契约 / 引导指令 / 降级工具**。"
                 "供 LLM 兜底路由(`select_for_llm`)与人工审阅使用。")
    lines.append("")
    lines.append(f"**相关性阈值**：`relevance_score < {LOW_RELEVANCE_THRESHOLD}` 时，应采纳工具的 `guidance_on_low_relevance`。")
    lines.append("")
    cats = ["financial", "industry", "business", "legal", "search", "infra", "resolve"]
    for cat in cats:
        group = [t for t in TOOL_MANIFEST if t.category == cat and t.status == "active"]
        if not group:
            continue
        lines.append(f"## {cat.capitalize()}")
        lines.append("")
        for t in group:
            exp = "" if t.exposed_to_llm else "  _(不暴露给 LLM)_"
            lines.append(f"### `{t.key}` — {t.display_name}{exp}")
            lines.append(f"- **功能**：{t.description}")
            if t.negative_boundaries:
                lines.append("- **负向边界**：")
                for nb in t.negative_boundaries:
                    lines.append(f"  - {nb}")
            if t.accepts:
                lines.append(f"- **入参**：{', '.join(t.accepts)}")
            lines.append(f"- **相关性契约**：{t.relevance_contract}")
            lines.append(f"- **低相关引导**：{t.guidance_on_low_relevance}")
            if t.fallback_to:
                lines.append(f"- **降级/互补**：{', '.join(t.fallback_to)}")
            lines.append(f"- **入口**：`{t.entry}`")
            lines.append("")
    deprecated = [t for t in TOOL_MANIFEST if t.status == "deprecated"]
    if deprecated:
        lines.append("## Deprecated (重构中已移除的 stub)")
        lines.append("")
        for t in deprecated:
            lines.append(f"- `{t.key}` — {t.display_name}：{t.description} 降级走 {', '.join(t.fallback_to) or '无'}。")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_markdown())
