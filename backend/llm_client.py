"""LLM 调用基础设施"""

import json
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
async def analyze_batch(system_prompt: str, user_prompt: str,
                        temperature: float = 0.3, max_tokens: int = 4096, model: str = "") -> dict:
    client = get_client()
    response = await client.chat.completions.create(
        model=model or settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


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
