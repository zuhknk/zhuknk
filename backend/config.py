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

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT: int = 120

    # 清理
    REVIEW_MIN_LENGTH: int = 5
    BATCH_SIZE: int = 40
    MIN_EVIDENCE_COUNT: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
