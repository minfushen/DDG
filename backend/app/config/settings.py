# backend/app/config/settings.py
"""应用配置管理"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "DDG-Agent-Backend"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS 配置：生产环境请改为具体前端域名逗号分隔（如 https://a.com,https://b.com）。
    # 设为 "*" 时视为开发模式，自动关闭凭证跨域（避免任意站点带凭证调用）。
    CORS_ORIGINS: str = "*"

    # LLM 配置 - 主 LLM 供应商抽象（仿 embedding_config 的多 provider 模式）
    # 可选值：openai_compatible（默认，走 LLM_BASE_URL）/ openai / dashscope /
    # qwen / deepseek / ollama（以上均 ChatOpenAI 兼容网关，零额外依赖）；
    # zhipu / glm（需 langchain-community）、anthropic / claude
    # （需 langchain-anthropic）、gemini（需 langchain-google-genai）。
    # 原生 SDK 分支为延迟导入，缺依赖时给出明确安装指引。
    LLM_PROVIDER: str = "openai_compatible"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen3.7-max-preview"
    LLM_BASE_URL: str = "https://llm-4zstl2gr1cq1v43s.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    LLM_TIMEOUT_SECONDS: int = 180
    LLM_MAX_RETRIES: int = 2

    # 财务叙述备用 LLM（OpenAI 兼容，可选）
    FINANCIAL_NARRATIVE_BACKUP_LLM_API_KEY: str = ""
    FINANCIAL_NARRATIVE_BACKUP_LLM_BASE_URL: str = ""
    FINANCIAL_NARRATIVE_BACKUP_LLM_MODEL: str = ""
    INDUSTRY_CLASSIFICATION_LLM_TIMEOUT_SECONDS: int = 45

    # 分析诊断 LLM 池（深度归因/叙述竞速）
    # 复用 LLM_API_KEY / LLM_BASE_URL；逗号分隔多个模型 ID，按需竞速。
    # 用途：① 年报"经营情况讨论与分析"章节深度归因抽取；
    #       ② 财务/行业叙述多模型竞速，降低单模型失败与额度耗尽风险。
    ANALYSIS_LLM_MODELS: str = "qwen3.7-max-2026-06-08,qwen3.7-max-2026-05-17,qwen3.7-plus,qwen3.6-plus-2026-04-02"
    ANALYSIS_LLM_MAX_TOKENS: int = 8192
    ANALYSIS_LLM_TIMEOUT_SECONDS: int = 120

    # OpenAI 兼容配置（保留给需要 OpenAI 兼容接口的组件）
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""

    # LangGraph 配置
    LANGGRAPH_RECURSION_LIMIT: int = 25
    LANGGRAPH_CHECKPOINT_DIR: str = "./checkpoints"

    # RAG 配置
    CHROMA_DB_DIR: str = "./db/chroma"
    EMBEDDING_MODEL: str = "text-embedding-v4"

    # PDF 年报解析结果自动入库 RAG（搜索 Agent 拉取 PDF 后自动写入企业 collection）
    AUTO_INGEST_CNINFO_ANNUAL_REPORT: bool = True
    AUTO_INGEST_TIMEOUT_SECONDS: int = 60

    # MinerU 云端 PDF 解析服务配置
    MINERU_ENABLED: bool = True
    MINERU_API_TOKEN: str = ""
    MINERU_MODEL_VERSION: str = "vlm"  # pipeline | vlm | MinerU-HTML
    MINERU_ENABLE_OCR: bool = False
    MINERU_ENABLE_FORMULA: bool = True
    MINERU_ENABLE_TABLE: bool = True
    MINERU_LANGUAGE: str = "ch"
    MINERU_POLL_TIMEOUT_SECONDS: int = 300
    MINERU_POLL_INTERVAL_SECONDS: int = 5
    MINERU_MAX_FILE_SIZE_MB: int = 200
    MINERU_MAX_PAGES_PER_TASK: int = 200  # MinerU 精准解析单文件页数上限

    # Embedding 服务配置（SiliconFlow / OpenAI 兼容）
    EMBEDDING_PROVIDER: str = "siliconflow"  # dashscope | siliconflow
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL_ID: str = "BAAI/bge-large-zh-v1.5"

    # Rebecca 配置
    REBECCA_OUTPUT_DIR: str = "./output"

    # LangSmith 配置（可选）
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "ddg-agent"

    # 搜索工具配置
    TAVILY_API_KEY: str = ""
    BOCHA_API_KEY: str = ""
    BOCHA_SEARCH_TIMEOUT_SECONDS: int = 15
    ENABLE_SEARXNG_SEARCH: bool = False
    SEARXNG_BASE_URL: str = "http://127.0.0.1:8080"
    SEARXNG_TIMEOUT_SECONDS: int = 15
    SEARXNG_MAX_RESULTS: int = 8

    # 网页正文读取增强（可选；依赖 crawl4ai/Playwright，默认关闭）
    ENABLE_CRAWL4AI_READER: bool = False
    CRAWL4AI_TIMEOUT_SECONDS: int = 20
    CRAWL4AI_MAX_PAGES_PER_TASK: int = 3
    # 本地开发优先复用已安装的 Google Chrome，避免 Playwright Chromium 下载慢或失败。
    # 私有化部署可改为 chromium，并预装 Playwright 浏览器运行时。
    CRAWL4AI_CHROME_CHANNEL: str = "chrome"

    # MCP 搜索服务（可选，stdio 命令；例如 npx -y ...）
    EXA_MCP_URL: str = ""
    EXA_MCP_COMMAND: str = ""
    EXA_MCP_ARGS: str = ""
    EXA_MCP_TOOL: str = ""
    EXA_API_KEY: str = ""
    MCP_SEARCH_TIMEOUT_SECONDS: int = 20

    # Sequential Thinking MCP（可选；用于 DeepResearch 规划/反思增强）
    ENABLE_SEQUENTIAL_THINKING: bool = False
    SEQUENTIAL_THINKING_TRANSPORT: str = "stdio"  # stdio | streamable_http
    SEQUENTIAL_THINKING_REMOTE_URL: str = "http://127.0.0.1:38001/mcp"
    SEQUENTIAL_THINKING_MCP_COMMAND: str = "npx"
    SEQUENTIAL_THINKING_MCP_ARGS: str = "-y @modelcontextprotocol/server-sequential-thinking"
    SEQUENTIAL_THINKING_MCP_TIMEOUT_SECONDS: int = 20

    # DeepResearch LLM Planner（Plan-Execute 架构中的 plan 节点）- 阿里云百炼 qwen3.7-plus
    ENABLE_LLM_RESEARCH_PLANNER: bool = True
    RESEARCH_PLANNER_TIMEOUT_SECONDS: int = 90
    RESEARCH_PLANNER_MAX_TASKS: int = 6
    RESEARCH_PLANNER_LLM_API_KEY: str = ""
    RESEARCH_PLANNER_LLM_BASE_URL: str = "https://llm-4zstl2gr1cq1v43s.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    RESEARCH_PLANNER_LLM_MODEL: str = "qwen3.7-plus"

    # CodeAct 代码即工具（默认只启用白名单注册工具，不开放任意代码执行）
    ENABLE_CODEACT_TOOLS: bool = True
    ENABLE_CODEACT_ADHOC: bool = False
    CODEACT_DEFAULT_TIMEOUT_SECONDS: int = 30

    # 巨潮资讯 WebAPI（结构化财务/股东/司法数据）
    # 推荐用 Access Key/Secret 自动刷新短期 access_token（约 2h 有效期）；
    # 旧 CNINFO_ACCESS_TOKEN 仅作向后兼容回退，建议留空由系统自动续期。
    CNINFO_ACCESS_KEY: str = ""
    CNINFO_ACCESS_SECRET: str = ""
    CNINFO_ACCESS_TOKEN: str = ""  # 静态 token 回退；Key/Secret 未配且此处配了才生效
    CNINFO_TOKEN_REFRESH_URL: str = "https://data-auth.cninfo.com.cn/oauth2/token"
    CNINFO_TOKEN_REFRESH_BUFFER_SECONDS: int = 300  # 过期前 5 分钟提前续期
    CNINFO_TOKEN_CACHE_DIR: str = ""  # 空=仅内存缓存；填路径则重启后复用未过期 token

    # 元典法律/企业信息平台（MCP streamable-HTTP）
    YUANDIAN_API_KEY: str = ""
    YUANDIAN_LAW_MCP_URL: str = "https://open.chineselaw.com/mcp/law/stream"
    YUANDIAN_CASE_MCP_URL: str = "https://open.chineselaw.com/mcp/case/stream"
    YUANDIAN_COMPANY_MCP_URL: str = "https://open.chineselaw.com/mcp/company/stream"
    YUANDIAN_MCP_TIMEOUT_SECONDS: int = 30

    # 企业工商专项 API 配置（可选）
    # BUSINESS_REGISTRY_PROVIDER: auto | tianyancha | qichacha | none
    BUSINESS_REGISTRY_PROVIDER: str = "auto"
    TIANYANCHA_API_TOKEN: str = ""
    QICHACHA_API_KEY: str = ""
    QICHACHA_API_SECRET: str = ""

    # 缓存配置（减少重复外部 API / LLM 调用）
    ENABLE_TOOL_CACHE: bool = True
    ENABLE_LLM_CACHE: bool = True
    CACHE_DB_PATH: str = ""
    TOOL_CACHE_TTL_SECONDS: int = 86400
    LLM_CACHE_TTL_SECONDS: int = 3600
    TOOL_CACHE_TTL_BY_TOOL: str = ""
    CLEAR_CACHE_ON_START: bool = False

    # 记忆系统配置（Agent 记忆上下文管理，降低重复搜索和 LLM 调用成本）
    ENABLE_SHORT_TERM_MEMORY: bool = True
    ENABLE_LONG_TERM_MEMORY: bool = True
    MEMORY_DB_PATH: str = ""  # 空=默认路径 (db/memory/memory.sqlite3)
    MEMORY_FREEZE_DAYS: int = 3
    MEMORY_CONSOLIDATION_DAYS: int = 7
    MEMORY_STALE_DAYS: int = 30

    # Dify 集成配置（Dify 作为轻量入口和问答增强层）
    ENABLE_DIFY_INTEGRATION: bool = True
    DIFY_API_BASE_URL: str = ""  # Dify API 地址，如 https://api.dify.ai/v1
    DIFY_API_KEY: str = ""  # Dify API Key（用于向 Dify 推送知识库等）
    DIFY_APP_ID: str = ""  # Dify 应用 ID
    DIFY_WEB_APP_URL: str = ""  # Dify Web App 地址，供前端嵌入
    DIFY_AUTH_TOKEN: str = ""  # Dify 调用 ddg-agent API 的认证令牌
    DIFY_POLL_INTERVAL_SECONDS: int = 3  # Dify 轮询状态间隔
    DIFY_POLL_MAX_RETRIES: int = 200  # Dify 轮询最大重试次数

    # 行业市场数据工具配置
    INDUSTRY_MARKET_DATA_ENABLE_REFILL: bool = True

    # 路径配置
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    OUTPUT_DIR: Path = BASE_DIR / "output"
    DB_DIR: Path = BASE_DIR / "db"
    CHECKPOINT_DIR: Path = BASE_DIR / "checkpoints"

    class Config:
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


settings = get_settings()
