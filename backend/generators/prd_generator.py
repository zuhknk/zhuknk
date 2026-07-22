"""PRD 生成（保留兼容，实际已合并到 main.py 的组合调用）"""

from models import Requirement


def parse_requirements(result: dict, findings: list) -> list[Requirement]:
    """从 LLM 结果解析需求"""
    requirements = []
    for i, req in enumerate(result.get("requirements", [])):
        related_ids = req.get("related_finding_ids", [])
        related_review_ids = []
        for fid in related_ids:
            for f in findings:
                if f.finding_id == fid:
                    related_review_ids.extend(f.review_ids)
                    break
        requirements.append(Requirement(
            req_id=req.get("req_id", f"REQ-{i+1:03d}"),
            title=req.get("title", ""),
            description=req.get("description", ""),
            user_story=req.get("user_story", ""),
            priority=req.get("priority", "P2"),
            acceptance_criteria=req.get("acceptance_criteria", []),
            related_finding_ids=related_ids,
            related_review_ids=list(set(related_review_ids))[:10],
            is_assumption=req.get("is_assumption", False),
        ))
    return requirements
