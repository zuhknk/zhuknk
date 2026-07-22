"""测试用例生成（保留兼容，实际已合并到 main.py 的组合调用）"""

from models import TestCase


def parse_test_cases(result: dict, requirements: list) -> list[TestCase]:
    """从 LLM 结果解析测试用例"""
    test_cases = []
    for i, tc in enumerate(result.get("test_cases", [])):
        req_id = tc.get("req_id", "")
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
