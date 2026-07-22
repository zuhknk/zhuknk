"""LLM Provider 抽象基类"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, system_prompt: str, user_prompt: str,
                   temperature: float = 0.3, max_tokens: int = 4096) -> dict:
        """发送对话请求，返回解析后的 JSON dict"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
