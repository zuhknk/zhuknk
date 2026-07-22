"""数据清洗：去重 + 噪声过滤 + 语言检测"""

import re
from langdetect import detect
from models import ReviewCleaned


def clean_reviews(raw_reviews: list, progress_callback=None) -> list[ReviewCleaned]:
    cleaned = []
    seen_ids = set()
    fingerprints = set()
    total = len(raw_reviews)

    for i, r in enumerate(raw_reviews):
        result = ReviewCleaned(**r.model_dump())

        if r.review_id in seen_ids:
            result.is_duplicate = True
        seen_ids.add(r.review_id)

        fp = _make_fingerprint(r)
        if fp in fingerprints:
            result.is_duplicate = True
        fingerprints.add(fp)
        result.fingerprint = fp

        if _is_noise(r.content):
            result.is_noise = True

        result.language = _detect_language(r.content)

        cleaned.append(result)

        if progress_callback and i % 10 == 0:
            progress_callback("cleaning", int((i + 1) / total * 100),
                              f"\u6e05\u6d17\u7b2c {i + 1}/{total} \u6761")

    return cleaned


def _make_fingerprint(review) -> str:
    content = (review.content or "").strip().lower()[:50]
    return f"{content}|{review.rating}"


def _is_noise(content: str) -> bool:
    if not content or not content.strip():
        return True
    stripped = content.strip()
    if len(stripped) < 5:
        return True
    text_only = re.sub(r'[\U0001F000-\U0001FFFF\u2600-\u27FF\u2B50\u2700-\u27BF\uFE0F\u200D]', '', stripped)
    if len(text_only.strip()) < 2:
        return True
    return False


def _detect_language(text: str) -> str:
    try:
        return detect(text or "")
    except Exception:
        return "unknown"


def get_valid_reviews(cleaned: list[ReviewCleaned]) -> list[ReviewCleaned]:
    return [c for c in cleaned if not c.is_duplicate and not c.is_noise]


def get_cleaning_stats(cleaned: list[ReviewCleaned]) -> dict:
    return {
        "total": len(cleaned),
        "valid": len(get_valid_reviews(cleaned)),
        "duplicates": sum(1 for c in cleaned if c.is_duplicate),
        "noise": sum(1 for c in cleaned if c.is_noise),
    }
