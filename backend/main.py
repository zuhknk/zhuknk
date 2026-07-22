"""FastAPI 主应用 - 提供 SSE 流式分析接口"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from models import (
    AnalysisProgress,
    AnalysisRequest,
    AnalysisResult,
    ReviewFinding,
    Requirement,
    TestCase,
)
from collectors.app_store import parse_app_store_url, collect_reviews, collect_reviews_from_file
from cleaners.review_cleaner import clean_reviews, get_valid_reviews, get_cleaning_stats
from analyzers.review_analyzer import discover_topics, validate_evidence, topics_to_findings
from generators.prd_generator import generate_requirements
from generators.testcase_generator import generate_test_cases
from validators.result_validator import validate_results

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("main")

app = FastAPI(
    title="LaienTech iOS App Review Analyzer",
    version="0.1.0",
    description="iOS App Store 评论分析与版本规划评估工具",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 数据模型 ----

class AnalysisRequestExt(BaseModel):
    """扩展分析请求（支持文件导入）"""
    app_url: str = ""
    goal: str = ""
    constraint: str = ""
    max_reviews: int = 500
    sort_by: str = "mostrecent"  # mostrecent | mosthelpful
    file_data: str = ""  # base64 或 JSON 字符串
    file_format: str = ""  # json / csv


# ---- SSE 工具 ----

def _sse_event(event: str, data: dict) -> str:
    """构造 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def _send_progress(queue: asyncio.Queue, stage: str, progress: int, message: str, **kwargs):
    """向 SSE 队列推送进度"""
    payload = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        **kwargs,
    }
    await queue.put(payload)


# ---- 健康检查 ----

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "llm_configured": bool(settings.OPENAI_API_KEY),
    }


# ---- 核心分析接口 ----

@app.post("/api/analyze")
async def analyze(request: AnalysisRequestExt):
    """
    启动评论分析流程，通过 SSE 流式返回进度。

    流程: 采集 → 清洗 → 分析 → 证据验证 → PRD 生成 → 测试用例生成 → 校验
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # === 阶段 0: 解析输入 ===
            await _send_progress(queue, "parsing", 0, "正在解析输入...")

            if request.file_data:
                # 文件导入模式
                reviews = await collect_reviews_from_file(
                    request.file_data,
                    request.file_format or "json",
                    progress_callback=lambda s, p, m: _send_progress(queue, s, p, m),
                )
                app_id = "imported"
                app_name = "导入数据"
                country = "unknown"
            else:
                # URL 解析模式
                if not request.app_url:
                    await _send_progress(queue, "error", 0, "请提供 App Store 链接或文件数据")
                    yield _sse_event("error", {"message": "请提供 App Store 链接或文件数据"})
                    return

                country, app_id = parse_app_store_url(request.app_url)
                app_name = f"App {app_id}"
                await _send_progress(queue, "parsing", 10, f"解析成功: app_id={app_id}, country={country}")

                # === 阶段 1: 数据采集 ===
                await _send_progress(queue, "collecting", 15, "开始采集评论数据...")

                max_pages = min(request.max_reviews // 50, settings.RSS_MAX_PAGES)
                reviews = await collect_reviews(
                    app_id=app_id,
                    sort=request.sort_by or "mostrecent",
                    country="us",
                    max_pages=max_pages,
                    progress_callback=lambda s, p, m: _send_progress(queue, s, p, m),
                )

            if not reviews:
                await _send_progress(queue, "error", 0, "未采集到任何评论数据")
                yield _sse_event("error", {"message": "未采集到任何评论数据"})
                return

            await _send_progress(
                queue, "collecting", 30,
                f"采集完成: 共 {len(reviews)} 条评论",
                data={"total_reviews": len(reviews)},
            )

            # === 阶段 2: 数据清洗 ===
            await _send_progress(queue, "cleaning", 35, "开始清洗数据...")

            # 异步执行清洗（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            cleaned = await loop.run_in_executor(
                None,
                clean_reviews,
                reviews,
                lambda s, p, m: asyncio.run_coroutine_threadsafe(
                    _send_progress(queue, s, p, m), loop
                ),
            )

            valid_reviews = get_valid_reviews(cleaned)
            clean_stats = get_cleaning_stats(cleaned)

            await _send_progress(
                queue, "cleaning", 50,
                f"清洗完成: {clean_stats['valid']} 条有效评论",
                data={"cleaning_stats": clean_stats},
            )

            # === 阶段 3-7: LLM 分析管线 ===
            llm_available = bool(settings.OPENAI_API_KEY)
            app_context = f"App ID: {app_id}"

            if llm_available:
                await _run_llm_pipeline(queue, valid_reviews, app_id, app_context, request)
            else:
                await _send_progress(queue, "analyzing", 55, "未配置 LLM API Key，使用统计模式")
                findings = _generate_placeholder_findings(valid_reviews)
                requirements = _generate_placeholder_requirements(findings)
                test_cases = _generate_placeholder_test_cases(requirements)
                validation_report = {}
                warnings = ["未配置 OPENAI_API_KEY，使用统计模式（非 LLM 语义分析）"]

            # === 结果汇总 ===
            if llm_available:
                findings = pipeline_result["findings"]
                requirements = pipeline_result["requirements"]
                test_cases = pipeline_result["test_cases"]
                validation_report = pipeline_result["validation_report"]
                warnings = pipeline_result.get("warnings", [])
                if not findings:
                    warnings.append("LLM 分析未产生发现，请检查 API Key 配置")

            # === 完成 ===
            sort_label = "最有帮助" if request.sort_by == "mosthelpful" else "最新"
            data_limitations = [
                f"RSS Feed 最多返回 {settings.RSS_MAX_PAGES * 50} 条评论",
                f"排序模式: {sort_label} ({request.sort_by or 'mostrecent'})",
            ]
            if not llm_available:
                data_limitations.append("LLM 语义分析未启用（未配置 API Key）")

            # 序列化评论数据（仅有效评论）供前端展示
            reviews_data = [
                r.model_dump() for r in valid_reviews
            ]

            await _send_progress(
                queue, "done", 100,
                "分析完成",
                data={
                    "app_id": app_id,
                    "app_name": app_name,
                    "total_reviews": len(reviews),
                    "cleaned_reviews": clean_stats["valid"],
                    "reviews": reviews_data,
                    "findings": [f.model_dump() for f in findings],
                    "requirements": [r.model_dump() for r in requirements],
                    "test_cases": [t.model_dump() for t in test_cases],
                    "validation_report": validation_report,
                    "data_limitations": data_limitations,
                    "warnings": warnings,
                },
            )

            yield _sse_event("done", {
                "stage": "done",
                "progress": 100,
                "message": "分析完成",
            })

        except ValueError as e:
            await _send_progress(queue, "error", 0, str(e))
            yield _sse_event("error", {"message": str(e)})
        except Exception as e:
            logger.exception("Analysis failed")
            await _send_progress(queue, "error", 0, f"分析失败: {str(e)}")
            yield _sse_event("error", {"message": f"分析失败: {str(e)}"})

    # 启动 SSE 流
    async def sse_wrapper():
        # 先启动后台任务
        bg_task = asyncio.create_task(_run_analysis(queue, event_stream))
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=300)
                    yield _sse_event("progress", msg)
                    if msg.get("stage") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield _sse_event("error", {"message": "分析超时"})
                    break
        finally:
            bg_task.cancel()

    return StreamingResponse(
        sse_wrapper(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_analysis(queue: asyncio.Queue, event_stream):
    """运行分析流程并将事件写入队列"""
    async for event in event_stream():
        pass  # 事件在 event_stream 内部已通过 queue 处理


# ---- LLM 分析管线 ----

async def _run_llm_pipeline(
    queue: asyncio.Queue,
    reviews,
    app_id: str,
    app_context: str,
    request,
) -> None:
    """
    执行完整的 LLM 分析管线：
    阶段 3: 主题发现 → 阶段 4: 证据验证 → 阶段 5: PRD → 阶段 6: 测试用例 → 阶段 7: 校验
    """
    global pipeline_result

    warnings = []
    progress_base = 55

    # === 阶段 3: 语义主题发现 ===
    await _send_progress(queue, "analyzing", progress_base, "LLM 正在分析评论语义...")

    async def topic_progress(pct, msg):
        await _send_progress(queue, "analyzing", progress_base + int(pct * 0.2), msg)

    raw_topics = await discover_topics(reviews, progress_callback=topic_progress)
    logger.info(f"Stage 3 - Topic discovery: {len(raw_topics)} topics found")

    if not raw_topics:
        warnings.append("LLM 未发现任何主题，可能评论数量不足或 API 异常")

    # === 阶段 4: 证据验证 ===
    await _send_progress(queue, "evidence", 75, "正在交叉验证证据...")

    validated = await validate_evidence(raw_topics, reviews)
    findings = topics_to_findings(raw_topics)
    logger.info(f"Stage 4 - Evidence validation: {len(findings)} findings")

    await _send_progress(
        queue, "evidence", 80,
        f"证据验证完成: {len(findings)} 项发现",
    )

    # === 阶段 5: PRD 生成 ===
    await _send_progress(queue, "prd", 83, "正在生成 PRD 需求...")

    requirements = await generate_requirements(
        findings,
        app_context=app_context,
        goal=request.goal,
        constraint=request.constraint,
    )
    logger.info(f"Stage 5 - PRD: {len(requirements)} requirements")

    await _send_progress(
        queue, "prd", 88,
        f"PRD 生成完成: {len(requirements)} 条需求",
    )

    # === 阶段 6: 测试用例生成 ===
    await _send_progress(queue, "testcase", 90, "正在生成测试用例...")

    test_cases = await generate_test_cases(
        requirements,
        app_context=app_context,
    )
    logger.info(f"Stage 6 - Test cases: {len(test_cases)} generated")

    await _send_progress(
        queue, "testcase", 93,
        f"测试用例生成完成: {len(test_cases)} 条",
    )

    # === 阶段 7: 最终校验 ===
    await _send_progress(queue, "validating", 95, "正在校验结果一致性...")

    validation_report = await validate_results(
        findings,
        requirements,
        test_cases,
        review_count=len(reviews),
        app_context=app_context,
    )
    logger.info(f"Stage 7 - Validation: {len(validation_report.get('issues', []))} issues")

    await _send_progress(
        queue, "validating", 98,
        f"校验完成: {'通过' if validation_report.get('validation_passed') else '发现问题'}",
    )

    # 存储结果到全局变量供 event_stream 使用
    pipeline_result = {
        "findings": findings,
        "requirements": requirements,
        "test_cases": test_cases,
        "validation_report": validation_report,
        "warnings": warnings,
    }


# 全局变量，存储 LLM 管线结果
pipeline_result = {}


# ---- 占位分析函数（LLM 不可用时的回退）----

def _generate_placeholder_findings(valid_reviews) -> list[ReviewFinding]:
    """生成占位分析发现（后续由 LLM 替代）"""
    if not valid_reviews:
        return []

    total = len(valid_reviews)
    avg_rating = sum(r.rating for r in valid_reviews) / total

    findings = [
        ReviewFinding(
            finding_id="F-001",
            topic="整体评分分布",
            description=f"共 {total} 条有效评论，平均评分 {avg_rating:.1f}/5",
            severity="medium",
            sentiment="neutral",
            sample_count=total,
            review_ids=[r.review_id for r in valid_reviews[:5]],
            excerpts=[r.content[:100] for r in valid_reviews[:3]],
            confidence=0.9,
            evidence_level="sufficient",
            source="statistical",
            uncertainty="LLM 语义分析尚未实现，仅基于统计指标",
        ),
    ]

    # 按评分分组
    ratings = [r.rating for r in valid_reviews]
    low_ratings = [r for r in valid_reviews if r.rating <= 2]
    if low_ratings:
        findings.append(ReviewFinding(
            finding_id="F-002",
            topic="低分评论聚类",
            description=f"共 {len(low_ratings)} 条低分评论（1-2星），占比 {len(low_ratings)/total*100:.1f}%",
            severity="high",
            sentiment="negative",
            sample_count=len(low_ratings),
            review_ids=[r.review_id for r in low_ratings[:5]],
            excerpts=[r.content[:100] for r in low_ratings[:3]],
            confidence=0.7,
            evidence_level="limited",
            source="statistical",
            uncertainty="需要 LLM 进行语义聚类分析以识别具体问题",
        ))

    return findings


def _generate_placeholder_requirements(findings: list[ReviewFinding]) -> list[Requirement]:
    """生成占位 PRD 需求（后续由 LLM 替代）"""
    if not findings:
        return []

    return [
        Requirement(
            req_id="REQ-001",
            title="评论语义分析",
            description="对采集到的用户评论进行语义聚类分析，识别高频问题和用户诉求",
            user_story="作为产品经理，我希望看到评论的语义分类结果，以便确定版本优化优先级",
            priority="P0",
            related_finding_ids=[f.finding_id for f in findings],
            related_review_ids=[],
            acceptance_criteria=[
                "评论按主题自动分类",
                "每个主题显示支持度（样本量）",
                "可追溯每类主题对应的原始评论",
            ],
            is_assumption=True,
        ),
    ]


def _generate_placeholder_test_cases(requirements: list[Requirement]) -> list[TestCase]:
    """生成占位测试用例（后续由 LLM 替代）"""
    if not requirements:
        return []

    return [
        TestCase(
            case_id="TC-001",
            req_id="REQ-001",
            title="验证评论语义分析结果的准确性",
            preconditions=["已采集不少于 50 条有效评论"],
            steps=[
                "启动评论分析流程",
                "等待 LLM 语义分析完成",
                "检查分析结果中每个主题的样本评论",
            ],
            expected_result="每个主题至少有 3 条样本评论，语义一致",
            source_review_ids=[],
            priority="P0",
        ),
    ]


# ---- 启动入口 ----

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)