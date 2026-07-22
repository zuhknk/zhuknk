"""PRD 需求生成模块"""

import json
import logging
from typing import Optional

from models import ReviewFinding, Requirement
from llm_client import analyze_batch
from prompts import PRD_GENERATION_SYSTEM, PRD_GENERATION_USER

logger = logging.getLogger(__name__)


async def generate_requirements(
    findings: list[ReviewFinding],
    app_context: str = "",
    goal: str = "",
    constraint: str = "",
    progress_callback: Optional[callable] = None,
) -> list[Requirement]:
    """
    阶段 5: PRD 需求生成

    基于验证后的分析发现，生成产品需求文档。

    Args:
        findings: 验证后的分析发现
        app_context: 应用上下文
        goal: 用户分析目标
        constraint: 用户约束
        progress_callback: 进度回调

    Returns:
        PRD 需求列表
    """
    if not findings:
        logger.warning("No findings to generate requirements from")
        return []

    # 构造 findings JSON
    findings_json = json.dumps(
        [f.model_dump() for f in findings],
        ensure_ascii=False,
    )

    goal_context = f"Analysis goal: {goal}" if goal else ""
    constraint_context = f"Constraints: {constraint}" if constraint else ""

    user_prompt = PRD_GENERATION_USER.format(
        findings_json=findings_json,
        app_context=app_context or "iOS mobile application",
        goal_context=goal_context,
        constraint_context=constraint_context,
    )

    try:
        result = await analyze_batch(
            PRD_GENERATION_SYSTEM,
            user_prompt,
            temperature=0.5,
            max_tokens=4096,
        )

        requirements = []
        for req_data in result.get("requirements", []):
            requirements.append(Requirement(
                req_id=req_data.get("req_id", f"REQ-{len(requirements)+1:03d}"),
                title=req_data.get("title", ""),
                description=req_data.get("description", ""),
                user_story=req_data.get("user_story", ""),
                priority=req_data.get("priority", "P1"),
                version=req_data.get("version", "v1.0"),
                related_finding_ids=req_data.get("related_finding_ids", []),
                related_review_ids=req_data.get("related_review_ids", []),
                acceptance_criteria=req_data.get("acceptance_criteria", []),
                is_assumption=req_data.get("is_assumption", False),
            ))

        if progress_callback:
            await progress_callback(100, f"PRD 生成完成: {len(requirements)} 条需求")

        logger.info(f"Generated {len(requirements)} requirements")
        return requirements

    except Exception as e:
        logger.error(f"PRD generation failed: {e}")
        return []