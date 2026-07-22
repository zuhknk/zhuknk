"""Extractor 基类 — 所有网站评论提取器的抽象接口"""

from abc import ABC, abstractmethod
from models import ReviewRaw


class BaseExtractor(ABC):
    """所有网站 Extractor 的基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """网站名称标识"""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """判断是否能处理此 URL"""
        pass

    @abstractmethod
    async def extract(self, url: str, max_pages: int = 5) -> list[ReviewRaw]:
        """提取评论，返回统一格式的 ReviewRaw 列表"""
        pass
