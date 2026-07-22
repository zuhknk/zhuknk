"""OpenAI / GPT Provider"""

import json
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from llm_providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._model = model

    @property
    def name(self) -> str:
        return f"openai/{self._model}"

    @retry(stop=stop_after_attempt(1), wait=wait_exponential(multiplier=0.5, min=1, max=3))
    async def chat(self, system_prompt: str, user_prompt: str,
                   temperature: float = 0.3, max_tokens: int = 4096,
                   response_format_json: bool = True) -> dict:
        kwargs = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # DeepSeek/Qwen 只在 prompt 包含 "json" 时支持 response_format
        if response_format_json:
            combined = (system_prompt + user_prompt).lower()
            if "json" in combined or "openai" in self._model:
                kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 尝试解析 JSON，失败则返回纯文本
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {"text": content}
