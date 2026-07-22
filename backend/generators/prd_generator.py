"""LLM 驱动的 PRD 生成"""

import uuid, json
from llm_client import analyze_batch
from prompts import PRD_GENERATION_SYSTEM
from models import Requirement, ReviewFinding


async def generate_requirements(findings: list[ReviewFinding], analysis_goal: str = "") -> list[Requirement]:
    """基于分析发现生成产品需求"""
    findings_json = []
    for f in findings:
        findings_json.append({
            "finding_id": f.finding_id,
            "topic": f.topic,
            "description": f.description,
            "severity": f.severity,
            "sentiment": f.sentiment,
            "sample_count": f.sample_count,
            "evidence_level": f.evidence_level,
            "excerpts": f.excerpts[:5],
            "review_ids": f.review_ids,
        })

    user_prompt = json.dumps(findings_json, ensure_ascii=False, indent=2)
    goal_hint = ""
    if analysis_goal:
        goal_hint = f"\n\n分析目标: {analysis_goal}。请基于此目标设定优先级。"

    try:
        result = await analyze_batch(PRD_GENERATION_SYSTEM, user_prompt + goal_hint)
        requirements = []
        for i, req in enumerate(result.get("requirements", [])):
            related_ids = req.get("related_finding_ids", [])
            # 收集关联 finding 的 review_ids
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
    except Exception as e:
        print(f"PRD generation failed: {e}")
        return []
