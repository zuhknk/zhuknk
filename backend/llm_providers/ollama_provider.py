"""本地 Ollama Provider — 使用 OpenAI 兼容接口"""

from llm_providers.openai_provider import OpenAIProvider


class OllamaProvider(OpenAIProvider):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int):
        # Ollama 不需要 API Key，使用占位符
        super().__init__(api_key=api_key or "ollama", base_url=base_url, model=model, timeout=timeout)

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"
