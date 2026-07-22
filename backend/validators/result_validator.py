"""结果校验模块 — 可追溯性 + 一致性验证"""

import json
import logging
from typing import Optional

from models import ReviewFinding, Requirement, TestCase
from llm_client import analyze_batch
from prompts import VALIDATION_SYSTEM, VALIDATION_USER

logger = logging.getLogger(__name__)


async def validate_results(
    findings: list[ReviewFinding],
    requirements: list[Requirement],
    test_cases: list[TestCase],
    review_count: int = 0,
    app_context: str = "",
    progress_callback: Optional[callable] = None,
) -> dict:
    """
    阶段 7: 最终校验

    验证整个分析链路的可追溯性和一致性。

    Returns:
        校验报告 dict
    """
    # 先做确定性校验（不需要 LLM）
    deterministic_issues = _deterministic_check(findings, requirements, test_cases)

    # LLM 语义校验
    llm_issues = []
    if findings and requirements:
        try:
            findings_json = json.dumps(
                [f.model_dump() for f in findings], ensure_ascii=False
            )
            requirements_json = json.dumps(
                [r.model_dump() for r in requirements], ensure_ascii=False
            )
            test_cases_json = json.dumps(
                [t.model_dump() for t in test_cases], ensure_ascii=False
            )

            user_prompt = VALIDATION_USER.format(
                findings_json=findings_json,
                requirements_json=requirements_json,
                test_cases_json=test_cases_json,
                review_count=review_count,
                app_context=app_context or "iOS application",
            )

            result = await analyze_batch(
                VALIDATION_SYSTEM, user_prompt, temperature=0.2
            )
            llm_issues = result.get("issues", [])
        except Exception as e:
            logger.error(f"LLM validation failed: {e}")

    # 合并结果
    all_issues = deterministic_issues + llm_issues

    # 构建可追溯性矩阵
    traceability = _build_traceability_matrix(findings, requirements, test_cases)

    validation_report = {
        "validation_passed": len([i for i in all_issues if i.get("severity") == "error"]) == 0,
        "issues": all_issues,
        "traceability": traceability,
        "data_quality": _data_quality_notes(findings, review_count),
        "recommendations": _generate_recommendations(all_issues, traceability),
    }

    if progress_callback:
        await progress_callback(100, f"校验完成: {len(all_issues)} 个问题")

    logger.info(f"Validation: {len(all_issues)} issues, passed={validation_report['validation_passed']}")
    return validation_report


def _deterministic_check(
    findings: list[ReviewFinding],
    requirements: list[Requirement],
    test_cases: list[TestCase],
) -> list[dict]:
    """确定性校验（不依赖 LLM）"""
    issues = []

    # 所有 finding IDs
    finding_ids = {f.finding_id for f in findings}

    # 所有 requirement IDs
    req_ids = {r.req_id for r in requirements}

    # 检查需求是否可追溯
    for r in requirements:
        if not r.related_finding_ids:
            issues.append({
                "type": "broken_traceability",
                "severity": "warning",
                "description": f"需求 {r.req_id} 没有关联任何分析发现",
                "affected_items": [r.req_id],
                "suggestion": "为该需求补充 related_finding_ids",
            })
        else:
            # 检查引用的 finding 是否存在
            missing = set(r.related_finding_ids) - finding_ids
            if missing:
                issues.append({
                    "type": "broken_traceability",
                    "severity": "error",
                    "description": f"需求 {r.req_id} 引用了不存在的发现: {missing}",
                    "affected_items": [r.req_id],
                    "suggestion": "修正 related_finding_ids 引用",
                })

    # 检查测试用例是否可追溯
    for tc in test_cases:
        if tc.req_id and tc.req_id not in req_ids:
            issues.append({
                "type": "broken_traceability",
                "severity": "error",
                "description": f"测试用例 {tc.case_id} 引用了不存在的需求: {tc.req_id}",
                "affected_items": [tc.case_id],
                "suggestion": "修正 req_id 引用",
            })

    # 检查是否有孤立需求
    orphaned_reqs = [r.req_id for r in requirements if not r.related_finding_ids]
    if orphaned_reqs:
        issues.append({
            "type": "coverage_gap",
            "severity": "warning",
            "description": f"以下需求缺乏用户反馈支撑: {orphaned_reqs}",
            "affected_items": orphaned_reqs,
            "suggestion": "为这些需求补充用户反馈来源，或标记为 is_assumption",
        })

    return issues


def _build_traceability_matrix(
    findings: list[ReviewFinding],
    requirements: list[Requirement],
    test_cases: list[TestCase],
) -> dict:
    """构建可追溯性矩阵"""
    finding_ids = {f.finding_id for f in findings}
    req_ids = {r.req_id for r in requirements}

    return {
        "total_findings": len(findings),
        "total_requirements": len(requirements),
        "total_test_cases": len(test_cases),
        "requirements_with_findings": sum(1 for r in requirements if r.related_finding_ids),
        "test_cases_with_requirements": sum(1 for t in test_cases if t.req_id in req_ids),
        "orphaned_requirements": [
            r.req_id for r in requirements if not r.related_finding_ids
        ],
        "orphaned_test_cases": [
            t.case_id for t in test_cases if t.req_id not in req_ids
        ],
    }


def _data_quality_notes(findings: list[ReviewFinding], review_count: int) -> list[str]:
    """数据质量评估"""
    notes = []

    if review_count < 50:
        notes.append(f"评论数量较少 ({review_count} 条)，分析结果可能不够全面")
    if review_count > 0 and review_count < 30:
        notes.append(f"样本量不足 ({review_count} 条)，发现置信度较低")

    # 检查低置信度发现
    low_confidence = [f for f in findings if f.confidence < 0.5]
    if low_confidence:
        notes.append(f"{len(low_confidence)} 个发现置信度低于 0.5，建议更多数据验证")

    return notes


def _generate_recommendations(issues: list[dict], traceability: dict) -> list[str]:
    """生成整体建议"""
    recs = []

    errors = [i for i in issues if i.get("severity") == "error"]
    if errors:
        recs.append(f"存在 {len(errors)} 个可追溯性错误，建议优先修复")

    if traceability.get("orphaned_requirements"):
        recs.append("部分需求缺乏用户反馈支撑，建议标记为假设或补充数据")

    if traceability.get("total_requirements", 0) == 0:
        recs.append("未生成任何需求，建议检查分析流程是否正常")

    return recs