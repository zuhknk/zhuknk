"""测试用例生成模块"""

import json
import logging
from typing import Optional

from models import Requirement, TestCase
from llm_client import analyze_batch
from prompts import TESTCASE_GENERATION_SYSTEM, TESTCASE_GENERATION_USER

logger = logging.getLogger(__name__)


async def generate_test_cases(
    requirements: list[Requirement],
    app_context: str = "",
    progress_callback: Optional[callable] = None,
) -> list[TestCase]:
    """
    阶段 6: 测试用例生成

    基于 PRD 需求，生成可执行的测试用例。

    Args:
        requirements: PRD 需求列表
        app_context: 应用上下文
        progress_callback: 进度回调

    Returns:
        测试用例列表
    """
    if not requirements:
        logger.warning("No requirements to generate test cases from")
        return []

    requirements_json = json.dumps(
        [r.model_dump() for r in requirements],
        ensure_ascii=False,
    )

    user_prompt = TESTCASE_GENERATION_USER.format(
        requirements_json=requirements_json,
        app_context=app_context or "iOS mobile application",
    )

    try:
        result = await analyze_batch(
            TESTCASE_GENERATION_SYSTEM,
            user_prompt,
            temperature=0.4,
            max_tokens=4096,
        )

        test_cases = []
        for tc_data in result.get("test_cases", []):
            test_cases.append(TestCase(
                case_id=tc_data.get("case_id", f"TC-{len(test_cases)+1:03d}"),
                req_id=tc_data.get("req_id", ""),
                title=tc_data.get("title", ""),
                preconditions=tc_data.get("preconditions", []),
                steps=tc_data.get("steps", []),
                expected_result=tc_data.get("expected_result", ""),
                source_review_ids=tc_data.get("source_review_ids", []),
                priority=tc_data.get("priority", "P1"),
            ))

        if progress_callback:
            await progress_callback(100, f"测试用例生成完成: {len(test_cases)} 条")

        logger.info(f"Generated {len(test_cases)} test cases")
        return test_cases

    except Exception as e:
        logger.error(f"Test case generation failed: {e}")
        return []