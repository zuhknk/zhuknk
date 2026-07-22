"""通义千问 (Qwen) Provider — 使用 OpenAI 兼容接口"""

from llm_providers.openai_provider import OpenAIProvider


class QwenProvider(OpenAIProvider):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int):
        super().__init__(api_key=api_key, base_url=base_url, model=model, timeout=timeout)

    @property
    def name(self) -> str:
        return f"qwen/{self._model}"
