"""FastAPI 主应用 — SSE 流式分析管道"""

import json, re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from models import (
    AnalysisRequest, ReviewRaw, ReviewCleaned, ReviewFinding,
    Requirement, TestCase, ValidationReport,
)
from collectors.app_store import collect_reviews, collect_reviews_from_file, parse_app_store_url
from cleaners.review_cleaner import clean_reviews, get_valid_reviews, get_cleaning_stats
from analyzers.review_analyzer import discover_topics, topics_to_findings, validate_evidence
from generators.prd_generator import generate_requirements
from generators.testcase_generator import generate_test_cases
from validators.result_validator import validate_results, generate_placeholder

app = FastAPI(title="LaienTech iOS App Review Analyzer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse_event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "llm_configured": bool(settings.OPENAI_API_KEY)}


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    async def event_stream():
        try:
            # ===== 阶段 1: parsing =====
            yield sse_event("parsing", {"stage": "parsing", "progress": 5, "message": "\u6b63\u5728\u89e3\u6790\u8bf7\u6c42..."})

            analysis_goal = request.analysis_goal or ""
            if analysis_goal:
                yield sse_event("parsing", {"stage": "parsing", "progress": 8,
                               "message": f"\u5206\u6790\u76ee\u6807: {analysis_goal}"})

            # ===== 阶段 2: collecting =====
            yield sse_event("collecting", {"stage": "collecting", "progress": 10, "message": "\u6b63\u5728\u91c7\u96c6\u8bc4\u8bba..."})

            if request.file_data:
                reviews = await collect_reviews_from_file(request.file_data)
            elif request.app_store_url:
                # 从 URL 提取 app_id
                try:
                    country, app_id = parse_app_store_url(request.app_store_url)
                except ValueError as e:
                    yield sse_event("error", {"message": str(e)})
                    return

                reviews = await collect_reviews(
                    app_id=app_id,
                    sort=request.sort or "mostrecent",
                    country=settings.RSS_COUNTRY,
                    max_pages=settings.RSS_MAX_PAGES,
                )
            else:
                yield sse_event("error", {"message": "\u8bf7\u63d0\u4f9b App Store URL \u6216\u4e0a\u4f20\u8bc4\u8bba\u6587\u4ef6"})
                return

            if not reviews:
                yield sse_event("error", {"message": "\u672a\u91c7\u96c6\u5230\u4efb\u4f55\u8bc4\u8bba\uff0c\u8bf7\u5c1d\u8bd5\u4e0a\u4f20\u6587\u4ef6\u5bfc\u5165"})
                return

            yield sse_event("collecting", {"stage": "collecting", "progress": 30,
                            "message": f"\u91c7\u96c6\u5b8c\u6210\uff0c\u5171 {len(reviews)} \u6761\u8bc4\u8bba"})

            # ===== 阶段 3: cleaning =====
            yield sse_event("cleaning", {"stage": "cleaning", "progress": 35, "message": "\u6b63\u5728\u6e05\u6d17\u6570\u636e..."})
            cleaned = clean_reviews(reviews)
            valid = get_valid_reviews(cleaned)
            stats = get_cleaning_stats(cleaned)
            yield sse_event("cleaning", {"stage": "cleaning", "progress": 45,
                            "stats": stats, "message": f"\u6e05\u6d17\u5b8c\u6210\uff0c\u6709\u6548\u8bc4\u8bba {len(valid)} \u6761"})

            # ===== 阶段 4-8: LLM / 统计模式 =====
            if settings.OPENAI_API_KEY:
                # 阶段 4: analyzing
                yield sse_event("analyzing", {"stage": "analyzing", "progress": 50, "message": "LLM \u4e3b\u9898\u53d1\u73b0\u4e2d..."})
                topics = await discover_topics(valid, analysis_goal)
                findings = topics_to_findings(topics)

                # 阶段 5: evidence
                yield sse_event("evidence", {"stage": "evidence", "progress": 65, "message": "\u8bc1\u636e\u9a8c\u8bc1\u4e2d..."})
                findings = await validate_evidence(findings, valid)

                # 阶段 6: prd
                yield sse_event("prd", {"stage": "prd", "progress": 75, "message": "\u751f\u6210 PRD \u9700\u6c42..."})
                requirements = await generate_requirements(findings, analysis_goal)

                # 阶段 7: testcase
                yield sse_event("testcase", {"stage": "testcase", "progress": 85, "message": "\u751f\u6210\u6d4b\u8bd5\u7528\u4f8b..."})
                test_cases = await generate_test_cases(requirements, analysis_goal)

                # 阶段 8: validating
                yield sse_event("validating", {"stage": "validating", "progress": 95, "message": "\u751f\u6210\u6821\u9a8c\u62a5\u544a..."})
                validation_report = await validate_results(findings, requirements, test_cases)
            else:
                yield sse_event("analyzing", {"stage": "analyzing", "progress": 50,
                                "message": "\u672a\u914d\u7f6e API Key\uff0c\u4f7f\u7528\u7edf\u8ba1\u6a21\u5f0f..."})
                findings, requirements, test_cases, validation_report = generate_placeholder(valid)

                yield sse_event("evidence", {"stage": "evidence", "progress": 65,
                                "message": f"\u7edf\u8ba1\u8bc1\u636e\u5df2\u751f\u6210\uff0c\u53d1\u73b0 {len(findings)} \u4e2a\u4e3b\u9898"})
                yield sse_event("prd", {"stage": "prd", "progress": 75,
                                "message": f"\u7edf\u8ba1\u6a21\u5f0f\u751f\u6210 {len(requirements)} \u6761\u9700\u6c42"})
                yield sse_event("testcase", {"stage": "testcase", "progress": 85,
                                "message": f"\u7edf\u8ba1\u6a21\u5f0f\u751f\u6210 {len(test_cases)} \u4e2a\u6d4b\u8bd5\u7528\u4f8b"})
                yield sse_event("validating", {"stage": "validating", "progress": 95,
                                "message": "\u7edf\u8ba1\u6a21\u5f0f\u6821\u9a8c\u5b8c\u6210"})

            # ===== done =====
            yield sse_event("done", {
                "reviews": [r.model_dump() for r in valid],
                "findings": [f.model_dump() for f in findings],
                "requirements": [r.model_dump() for r in requirements],
                "test_cases": [t.model_dump() for t in test_cases],
                "validation_report": validation_report.model_dump() if isinstance(validation_report, ValidationReport) else validation_report,
                "analysis_goal": analysis_goal,
                "data_limitations": [
                    "RSS API \u6700\u591a\u8fd4\u56de 500 \u6761\u8bc4\u8bba",
                    "\u4ec5\u91c7\u96c6 US \u533a\u8bc4\u8bba\u6570\u636e",
                ],
                "warnings": [] if settings.OPENAI_API_KEY else [
                    "\u672a\u914d\u7f6e OpenAI API Key\uff0c\u5206\u6790\u7ed3\u679c\u57fa\u4e8e\u7edf\u8ba1\u6a21\u5f0f\u751f\u6210\uff0c\u4ec5\u4f9b\u53c2\u8003",
                ],
            })

        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
