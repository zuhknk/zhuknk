"""LLM 调用基础设施 — 通过 Provider 注册表支持多模型"""

from llm_providers import get_provider


async def analyze_batch(system_prompt: str, user_prompt: str,
                        temperature: float = 0.3, max_tokens: int = 4096, model: str = "") -> dict:
    """调用当前配置的 LLM Provider 进行分析"""
    provider = get_provider()
    return await provider.chat(system_prompt, user_prompt, temperature, max_tokens)


def format_reviews_for_llm(reviews: list) -> list[dict]:
    return [
        {
            "id": r.review_id,
            "rating": r.rating,
            "title": r.title,
            "content": r.content,
            "version": r.version,
        }
        for r in reviews
    ]
