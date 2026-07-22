"""评论数据清洗模块 - 去重、规范化、语言检测"""

import re
import logging
from datetime import datetime
from typing import Optional

from langdetect import detect, LangDetectException

from models import ReviewRaw, ReviewCleaned

logger = logging.getLogger(__name__)

# 纯表情/纯符号模式
EMOJI_ONLY_PATTERN = re.compile(
    r"^[\U0001F300-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF"
    r"\U00002702-\U000027B0\U000024C2-\U0001F251\s\W]*$"
)

# 内容过短（少于2个词）
TOO_SHORT_PATTERN = re.compile(r"^\s*\w+(\s+\w+)?\s*$")


def clean_reviews(
    raw_reviews: list[ReviewRaw],
    progress_callback: Optional[callable] = None,
) -> list[ReviewCleaned]:
    """
    清洗评论数据：
    1. 精确去重（基于 review_id）
    2. 模糊去重（相同内容 + 评分 + 作者）
    3. 语言检测
    4. 过滤噪声评论
    """
    cleaned: list[ReviewCleaned] = []
    seen_ids: set[str] = set()
    content_fingerprints: set[str] = set()
    stats = {
        "total": len(raw_reviews),
        "exact_duplicates": 0,
        "fuzzy_duplicates": 0,
        "noise_removed": 0,
        "valid": 0,
    }

    for i, review in enumerate(raw_reviews):
        # 1. 精确去重
        if review.review_id in seen_ids:
            stats["exact_duplicates"] += 1

            # 标记为重复但保留（用于追溯）
            cleaned.append(ReviewCleaned(
                review_id=review.review_id,
                rating=review.rating,
                title=review.title,
                content=review.content,
                author=review.author,
                date=review.date,
                version=review.version,
                vote_sum=review.vote_sum,
                vote_count=review.vote_count,
                is_duplicate=True,
            ))
            continue

        seen_ids.add(review.review_id)

        # 2. 模糊去重
        fingerprint = _make_fingerprint(review)
        if fingerprint in content_fingerprints:
            stats["fuzzy_duplicates"] += 1

            cleaned.append(ReviewCleaned(
                review_id=review.review_id,
                rating=review.rating,
                title=review.title,
                content=review.content,
                author=review.author,
                date=review.date,
                version=review.version,
                vote_sum=review.vote_sum,
                vote_count=review.vote_count,
                is_duplicate=True,
            ))
            continue

        content_fingerprints.add(fingerprint)

        # 3. 噪声过滤
        if _is_noise(review.content):
            stats["noise_removed"] += 1

            cleaned.append(ReviewCleaned(
                review_id=review.review_id,
                rating=review.rating,
                title=review.title,
                content=review.content,
                author=review.author,
                date=review.date,
                version=review.version,
                vote_sum=review.vote_sum,
                vote_count=review.vote_count,
                is_duplicate=True,
            ))
            continue

        # 4. 语言检测
        lang = _detect_language(review.content)

        # 5. 有效评论
        stats["valid"] += 1
        cleaned.append(ReviewCleaned(
            review_id=review.review_id,
            rating=review.rating,
            title=review.title,
            content=review.content,
            author=review.author,
            date=review.date,
            version=review.version,
            vote_sum=review.vote_sum,
            vote_count=review.vote_count,
            language=lang,
            content_length=len(review.content),
            is_duplicate=False,
        ))

        if progress_callback and i % 50 == 0:
            _ = progress_callback(
                "cleaning",
                int((i + 1) / len(raw_reviews) * 100),
                f"清洗中: {stats['valid']} 有效, {stats['exact_duplicates']} 精确重复, "
                f"{stats['fuzzy_duplicates']} 模糊重复, {stats['noise_removed']} 噪声",
            )

    if progress_callback:
        _ = progress_callback(
            "cleaning",
            100,
            f"清洗完成: {stats['valid']} 条有效评论 (共 {stats['total']} 条原始)",
        )

    logger.info(f"Cleaning stats: {stats}")
    return cleaned


def _make_fingerprint(review: ReviewRaw) -> str:
    """生成评论内容指纹（用于模糊去重）"""
    normalized = review.content.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return f"{normalized}|{review.rating}"


def _is_noise(content: str) -> bool:
    """判断是否为噪声评论"""
    text = content.strip()

    # 空内容
    if not text:
        return True

    # 纯表情/符号
    if EMOJI_ONLY_PATTERN.match(text):
        return True

    # 极短内容（< 3 个字符）
    if len(text) < 3:
        return True

    return False


def _detect_language(text: str) -> str:
    """检测评论语言"""
    if not text or len(text.strip()) < 5:
        return "unknown"

    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def get_valid_reviews(cleaned: list[ReviewCleaned]) -> list[ReviewCleaned]:
    """获取有效（非重复、非噪声）的评论"""
    return [r for r in cleaned if not r.is_duplicate]


def get_cleaning_stats(cleaned: list[ReviewCleaned]) -> dict:
    """获取清洗统计信息"""
    total = len(cleaned)
    duplicates = sum(1 for r in cleaned if r.is_duplicate)
    valid = total - duplicates
    languages = {}
    for r in cleaned:
        if r.language and not r.is_duplicate:
            languages[r.language] = languages.get(r.language, 0) + 1

    return {
        "total": total,
        "duplicates": duplicates,
        "valid": valid,
        "languages": languages,
    }