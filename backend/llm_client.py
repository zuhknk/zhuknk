"""LLM 调用基础设施 — OpenAI 兼容 client + 重试 + 限流"""

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import settings

logger = logging.getLogger(__name__)

# 全局异步客户端（单例）
_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """获取或创建 OpenAI 异步客户端"""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
    return _client


# 需要重试的异常
RETRYABLE = (Exception,)


def _is_throttle(exception: Exception) -> bool:
    """判断是否为限流错误"""
    msg = str(exception).lower()
    return any(kw in msg for kw in ("rate", "throttle", "429", "too many"))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RETRYABLE),
)
async def _call_llm(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
    model: str = "",
) -> dict:
    """底层 LLM 调用（带重试）"""
    client = get_client()
    try:
        response = await client.chat.completions.create(
            model=model or settings.LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        if _is_throttle(e):
            logger.warning(f"LLM rate limited, retrying: {e}")
        raise


async def analyze_batch(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    model: str = "",
) -> dict:
    """
    单次 LLM 调用（JSON 模式）

    Args:
        system_prompt: 系统提示
        user_prompt: 用户提示（包含数据）
        temperature: 温度参数
        max_tokens: 最大 token 数
        model: 模型名称（可选）

    Returns:
        LLM 返回的 JSON 对象
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return await _call_llm(messages, temperature, max_tokens, model)


async def analyze_batched(
    items: list,
    system_prompt: str,
    user_prompt_template: str,
    batch_size: int = 50,
    temperature: float = 0.3,
    model: str = "",
    progress_callback: Optional[callable] = None,
) -> list[dict]:
    """
    分批 LLM 调用，聚合结果

    Args:
        items: 待分析的数据项列表
        system_prompt: 系统提示
        user_prompt_template: 用户提示模板（{items} 占位）
        batch_size: 每批数量
        temperature: 温度参数
        model: 模型名称
        progress_callback: 进度回调

    Returns:
        聚合后的 JSON 结果列表
    """
    all_results = []
    total_batches = (len(items) + batch_size - 1) // batch_size

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_num = i // batch_size + 1

        logger.info(f"LLM batch {batch_num}/{total_batches}: {len(batch)} items")

        # 构造用户提示
        batch_items_str = json.dumps(batch, ensure_ascii=False, indent=2)
        user_prompt = user_prompt_template.format(items=batch_items_str)

        try:
            result = await analyze_batch(
                system_prompt, user_prompt, temperature, model=model
            )
            all_results.append(result)
        except Exception as e:
            logger.error(f"LLM batch {batch_num} failed: {e}")
            all_results.append({"error": str(e), "batch": batch_num})

        if progress_callback:
            await progress_callback(
                int(batch_num / total_batches * 100),
                f"LLM 分析中: {batch_num}/{total_batches}",
            )

        # 批次间限流
        if batch_num < total_batches:
            await asyncio.sleep(1.0)

    return all_results


def format_reviews_for_llm(reviews) -> list[dict]:
    """将评论对象格式化为 LLM 友好的结构"""
    return [
        {
            "id": r.review_id,
            "rating": r.rating,
            "title": r.title,
            "content": r.content,
            "version": r.version,
            "date": str(r.date)[:10] if hasattr(r, "date") else "",
        }
        for r in reviews
    ]


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（英文: ~4 chars/token, 中文: ~1.5 chars/token）"""
    return len(text) // 3