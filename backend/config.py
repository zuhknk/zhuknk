"""配置管理"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # RSS Feed
    RSS_COUNTRY: str = "us"
    RSS_MAX_PAGES: int = 10
    RSS_REQUEST_INTERVAL: float = 1.0
    RSS_TIMEOUT: int = 30

    # LLM — 提供商选择: openai | deepseek | qwen | ollama
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT: int = 120

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    # 通义千问 (Qwen)
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Ollama (本地)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # 清理
    REVIEW_MIN_LENGTH: int = 5
    BATCH_SIZE: int = 80
    MIN_EVIDENCE_COUNT: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
