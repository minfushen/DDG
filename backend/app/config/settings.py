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

    # LLM 配置 - Xiaomi Mimo
    LLM_PROVIDER: str = "openai_compatible"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_BASE_URL: str = "https://token-plan-cn.xiaomimimo.com/v1"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3

    # OpenAI 兼容配置（CrewAI 使用）
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""

    # LangGraph 配置
    LANGGRAPH_RECURSION_LIMIT: int = 25
    LANGGRAPH_CHECKPOINT_DIR: str = "./checkpoints"

    # RAG 配置
    CHROMA_DB_DIR: str = "./db/chroma"
    EMBEDDING_MODEL: str = "text-embedding-v4"

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
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


settings = get_settings()
