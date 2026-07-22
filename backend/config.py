"""应用配置管理，所有敏感信息从环境变量读取"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    """应用配置"""

    # ---- 项目路径 ----
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    SAMPLE_DATA_DIR: Path = PROJECT_ROOT / "sample_data"

    # ---- App Store RSS ----
    RSS_COUNTRY: str = "us"  # 硬编码美区，确保评论数据来自美国 App Store
    RSS_BASE_URL: str = "https://itunes.apple.com/{country}/rss/customerreviews"
    RSS_PAGE_SIZE: int = 50
    RSS_MAX_PAGES: int = 10
    RSS_MAX_REVIEWS: int = RSS_MAX_PAGES * RSS_PAGE_SIZE  # 500
    RSS_REQUEST_INTERVAL: float = 1.0  # 请求间隔（秒）

    # ---- LLM 配置 ----
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE_CLASSIFY: float = 0.2
    LLM_TEMPERATURE_GENERATE: float = 0.6
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: float = 60.0

    # ---- 服务端口 ----
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()