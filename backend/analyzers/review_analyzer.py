"""评论语义分析模块 — 主题发现 + 证据验证"""

import json
import logging
from typing import Optional

from models import ReviewCleaned, ReviewFinding
from llm_client import analyze_batch, analyze_batched, format_reviews_for_llm
from prompts import (
    TOPIC_DISCOVERY_SYSTEM,
    TOPIC_DISCOVERY_USER,
    EVIDENCE_VALIDATION_SYSTEM,
    EVIDENCE_VALIDATION_USER,
)

logger = logging.getLogger(__name__)

# 每批最大评论数（控制 token 消耗）
TOPIC_BATCH_SIZE = 40


async def discover_topics(
    reviews: list[ReviewCleaned],
    progress_callback: Optional[callable] = None,
) -> list[dict]:
    """
    阶段 3: 语义主题发现

    分批将评论发送给 LLM，发现用户讨论的主题聚类。
    不做硬编码分类，完全由 LLM 自主发现。

    Args:
        reviews: 清洗后的有效评论
        progress_callback: 进度回调 (progress, message)

    Returns:
        原始 topic 列表（未验证）
    """
    if not reviews:
        return []

    total = len(reviews)
    logger.info(f"Starting topic discovery on {total} reviews")

    # 格式化评论
    formatted = format_reviews_for_llm(reviews)

    # 分批分析
    all_topics = []
    seen_topic_names = set()

    for i in range(0, len(formatted), TOPIC_BATCH_SIZE):
        batch = formatted[i : i + TOPIC_BATCH_SIZE]
        batch_num = i // TOPIC_BATCH_SIZE + 1
        total_batches = (len(formatted) + TOPIC_BATCH_SIZE - 1) // TOPIC_BATCH_SIZE

        user_prompt = TOPIC_DISCOVERY_USER.format(items=json.dumps(batch, ensure_ascii=False))

        try:
            result = await analyze_batch(
                TOPIC_DISCOVERY_SYSTEM,
                user_prompt,
                temperature=0.3,
            )
            topics = result.get("topics", [])
            logger.info(f"Batch {batch_num}/{total_batches}: found {len(topics)} topics")
            all_topics.extend(topics)
        except Exception as e:
            logger.error(f"Batch {batch_num} topic discovery failed: {e}")

        if progress_callback:
            await progress_callback(
                int(batch_num / total_batches * 90),
                f"主题发现: {batch_num}/{total_batches} 批",
            )

    # 合并相同主题的批次结果
    merged = _merge_topics(all_topics)
    logger.info(f"Topic discovery complete: {len(all_topics)} raw → {len(merged)} merged")

    return merged


def _merge_topics(topics: list[dict]) -> list[dict]:
    """合并跨批次的相同主题"""
    if len(topics) <= 1:
        return topics

    merged = []
    name_map = {}

    for topic in topics:
        name = topic.get("topic_name", "").strip().lower()
        if not name:
            merged.append(topic)
            continue

        if name in name_map:
            existing = name_map[name]
            existing["sample_count"] += topic.get("sample_count", 0)
            existing["review_ids"].extend(topic.get("review_ids", []))
            existing["excerpts"].extend(topic.get("excerpts", [])[:2])
            # 取平均置信度
            existing["confidence"] = (
                existing["confidence"] + topic.get("confidence", 0.5)
            ) / 2
            # 合并冲突反馈
            if topic.get("conflicting_feedback"):
                existing.setdefault("conflicting_feedback", []).extend(
                    topic["conflicting_feedback"]
                )
        else:
            name_map[name] = topic
            merged.append(topic)

    # 去重 excerpt 和 review_ids
    for topic in merged:
        topic["review_ids"] = list(set(topic["review_ids"]))
        topic["excerpts"] = list(set(topic["excerpts"]))[:5]

    return merged


async def validate_evidence(
    topics: list[dict],
    reviews: list[ReviewCleaned],
    progress_callback: Optional[callable] = None,
) -> list[dict]:
    """
    阶段 4: 证据验证

    交叉验证每个发现是否有足够的原始评论支撑。
    调整置信度，标记证据不足的发现。

    Args:
        topics: 阶段 3 发现的主题列表
        reviews: 原始评论
        progress_callback: 进度回调

    Returns:
        验证后的主题列表
    """
    if not topics:
        return []

    formatted = format_reviews_for_llm(reviews)
    findings_json = json.dumps(topics, ensure_ascii=False)

    user_prompt = EVIDENCE_VALIDATION_USER.format(
        findings_json=findings_json,
        items=json.dumps(formatted[:30], ensure_ascii=False),  # 只送前 30 条作为参考
    )

    try:
        result = await analyze_batch(
            EVIDENCE_VALIDATION_SYSTEM,
            user_prompt,
            temperature=0.2,
        )
        validated = result.get("validated_findings", [])

        # 将验证结果合并回原始 topic
        for v in validated:
            tid = v.get("topic_id", "")
            for topic in topics:
                if topic.get("topic_id") == tid:
                    topic["confidence"] = v.get("adjusted_confidence", topic["confidence"])
                    topic["evidence_level"] = v.get("evidence_level", topic["evidence_level"])
                    if v.get("recommendation") == "drop":
                        topic["_dropped"] = True
                    break

        if progress_callback:
            await progress_callback(100, f"证据验证完成: {len(validated)} 项")

        logger.info(f"Evidence validation: {len(validated)} findings validated")
        return validated

    except Exception as e:
        logger.error(f"Evidence validation failed: {e}")
        return []


def topics_to_findings(topics: list[dict]) -> list[ReviewFinding]:
    """将 LLM 返回的 topic 字典转换为 ReviewFinding 模型"""
    findings = []
    for i, topic in enumerate(topics):
        if topic.get("_dropped"):
            continue

        findings.append(ReviewFinding(
            finding_id=topic.get("topic_id", f"F-{i+1:03d}"),
            topic=topic.get("topic_name", "Unknown"),
            description=topic.get("description", ""),
            severity=topic.get("severity", "medium"),
            sentiment=topic.get("sentiment", "neutral"),
            sample_count=topic.get("sample_count", 0),
            review_ids=topic.get("review_ids", [])[:20],  # 限制数量
            excerpts=topic.get("excerpts", [])[:5],
            confidence=topic.get("confidence", 0.5),
            evidence_level=topic.get("evidence_level", "limited"),
            conflicting_feedback=topic.get("conflicting_feedback", []),
            source="llm",
            uncertainty=topic.get("uncertainty", ""),
        ))

    logger.info(f"Converted {len(findings)} topics to ReviewFinding models")
    return findings