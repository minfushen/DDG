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

    # LLM 配置 - 阿里云百炼 qwen3.7-max-preview（主 LLM）
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

    # 企业工商专项 API 配置（可选）
    # BUSINESS_REGISTRY_PROVIDER: auto | tianyancha | qichacha | none
    BUSINESS_REGISTRY_PROVIDER: str = "auto"
    TIANYANCHA_API_TOKEN: str = ""
    QICHACHA_API_KEY: str = ""
    QICHACHA_API_SECRET: str = ""

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
