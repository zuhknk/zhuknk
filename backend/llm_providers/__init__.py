"""LLM Provider 注册表 — 根据配置自动选择提供商"""

from config import settings
from llm_providers.base import LLMProvider

_provider_instance: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """获取当前配置的 LLM Provider（单例）"""
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "deepseek":
        from llm_providers.deepseek_provider import DeepSeekProvider
        _provider_instance = DeepSeekProvider(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT,
        )
    elif provider_name == "qwen":
        from llm_providers.qwen_provider import QwenProvider
        _provider_instance = QwenProvider(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT,
        )
    elif provider_name == "ollama":
        from llm_providers.ollama_provider import OllamaProvider
        _provider_instance = OllamaProvider(
            api_key="",
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.LLM_TIMEOUT,
        )
    else:
        # 默认 OpenAI
        from llm_providers.openai_provider import OpenAIProvider
        _provider_instance = OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT,
        )

    return _provider_instance


def reset_provider():
    """重置 Provider 实例（配置变更后调用）"""
    global _provider_instance
    _provider_instance = None
