"""LLM 驱动的主题发现 + 证据验证"""

import uuid, json
from config import settings
from llm_client import analyze_batch, format_reviews_for_llm
from prompts import TOPIC_DISCOVERY_SYSTEM
from models import ReviewFinding, ReviewCleaned


async def discover_topics(reviews: list[ReviewCleaned], analysis_goal: str = "") -> list[dict]:
    """分批调用 LLM 发现主题，跨批次合并相同主题"""
    batch_size = settings.BATCH_SIZE
    all_topics = {}

    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        reviews_json = format_reviews_for_llm(batch)
        user_prompt = json.dumps(reviews_json, ensure_ascii=False, indent=2)

        goal_hint = ""
        if analysis_goal:
            goal_hint = f"\n\n分析目标: {analysis_goal}。请重点关注与目标相关的反馈。"

        try:
            result = await analyze_batch(TOPIC_DISCOVERY_SYSTEM, user_prompt + goal_hint)
            for topic in result.get("topics", []):
                name = topic.get("topic", "").strip().lower()
                if name in all_topics:
                    # 合并：合并 review_ids 和 excerpts
                    existing = all_topics[name]
                    existing["review_ids"] = list(set(existing.get("review_ids", []) + topic.get("review_ids", [])))
                    existing["excerpts"] = list(set(existing.get("excerpts", []) + topic.get("excerpts", [])))
                    existing["sample_count"] = len(existing["review_ids"])
                    existing["confidence"] = max(existing.get("confidence", 0), topic.get("confidence", 0))
                else:
                    topic["sample_count"] = len(topic.get("review_ids", []))
                    all_topics[name] = topic
        except Exception as e:
            print(f"Batch {i // batch_size + 1} LLM failed: {e}")
            continue

    return list(all_topics.values())


def topics_to_findings(topics: list[dict]) -> list[ReviewFinding]:
    """将 LLM 返回的主题列表转换为 ReviewFinding 对象"""
    findings = []
    for topic in topics:
        findings.append(ReviewFinding(
            finding_id=str(uuid.uuid4())[:8],
            topic=topic.get("topic", "Unknown"),
            description=topic.get("description", ""),
            severity=topic.get("severity", "medium"),
            sentiment=topic.get("sentiment", "neutral"),
            sample_count=topic.get("sample_count", len(topic.get("review_ids", []))),
            review_ids=topic.get("review_ids", []),
            excerpts=topic.get("excerpts", []),
            confidence=topic.get("confidence", 0.5),
            evidence_level="sufficient",
            conflicting_feedback=topic.get("conflicting_feedback", []),
            source="llm",
            uncertainty="",
        ))
    return findings


async def validate_evidence(findings: list[ReviewFinding], reviews: list[ReviewCleaned]) -> list[ReviewFinding]:
    """验证每条发现的证据充分性，不足 3 条评论支撑的降级"""
    for f in findings:
        if f.sample_count < settings.MIN_EVIDENCE_COUNT:
            f.evidence_level = "insufficient"
            f.uncertainty = f"仅 {f.sample_count} 条评论支撑，证据不足"
            f.confidence = min(f.confidence, 0.3)
        elif f.sample_count < 5:
            f.evidence_level = "limited"
            f.uncertainty = f"仅 {f.sample_count} 条评论支撑，证据有限"
            f.confidence = min(f.confidence, 0.6)
        else:
            f.evidence_level = "sufficient"
            f.uncertainty = ""

        # 验证 review_ids 是否存在
        valid_ids = {r.review_id for r in reviews}
        f.review_ids = [rid for rid in f.review_ids if rid in valid_ids]
        f.sample_count = len(f.review_ids)

    return findings
