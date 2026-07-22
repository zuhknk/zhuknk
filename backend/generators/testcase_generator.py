"""LLM 驱动的测试用例生成"""

import uuid, json
from llm_client import analyze_batch
from prompts import TESTCASE_GENERATION_SYSTEM
from models import TestCase, Requirement


async def generate_test_cases(requirements: list[Requirement], analysis_goal: str = "") -> list[TestCase]:
    """基于需求生成可追溯的测试用例"""
    reqs_json = []
    for r in requirements:
        reqs_json.append({
            "req_id": r.req_id,
            "title": r.title,
            "description": r.description,
            "user_story": r.user_story,
            "acceptance_criteria": r.acceptance_criteria,
            "priority": r.priority,
        })

    user_prompt = json.dumps(reqs_json, ensure_ascii=False, indent=2)
    goal_hint = ""
    if analysis_goal:
        goal_hint = f"\n\n分析目标: {analysis_goal}。"

    try:
        result = await analyze_batch(TESTCASE_GENERATION_SYSTEM, user_prompt + goal_hint)
        test_cases = []
        for i, tc in enumerate(result.get("test_cases", [])):
            req_id = tc.get("req_id", "")
            # 找到对应需求的 source_review_ids
            source_review_ids = []
            for r in requirements:
                if r.req_id == req_id:
                    source_review_ids = r.related_review_ids[:5]
                    break

            test_cases.append(TestCase(
                case_id=tc.get("case_id", f"TC-{i+1:03d}"),
                req_id=req_id,
                title=tc.get("title", ""),
                preconditions=tc.get("preconditions", []),
                steps=tc.get("steps", []),
                expected_result=tc.get("expected_result", ""),
                source_review_ids=source_review_ids,
                priority=tc.get("priority", "P1"),
            ))
        return test_cases
    except Exception as e:
        print(f"Test case generation failed: {e}")
        return []
