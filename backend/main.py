"""FastAPI 主应用 — SSE 流式分析管道"""

import json, re, uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

from config import settings
from models import (
    AnalysisRequest, ReviewRaw, ReviewCleaned, ReviewFinding,
    Requirement, TestCase, ValidationReport,
)
from collectors.app_store import collect_reviews_from_file
from collectors import collect_from_url
from cleaners.review_cleaner import clean_reviews, get_valid_reviews, get_cleaning_stats
from analyzers.review_analyzer import discover_topics, topics_to_findings, validate_evidence
from validators.result_validator import generate_placeholder
from prompts import ANALYSIS_PIPELINE_SYSTEM, ALL_IN_ONE_SYSTEM
from llm_client import analyze_batch, format_reviews_for_llm

app = FastAPI(title="LaienTech iOS App Review Analyzer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据库
from database import init_db
init_db()

# 模块级 LLM 可用性缓存（仅检查一次）
_llm_available_cache = None


def _check_llm_available() -> bool:
    """检查 LLM 是否可用，结果缓存"""
    global _llm_available_cache
    if _llm_available_cache is not None:
        return _llm_available_cache
    provider = settings.LLM_PROVIDER.lower()
    if provider == "ollama":
        _llm_available_cache = True
    elif provider == "openai" and settings.OPENAI_API_KEY:
        _llm_available_cache = True
    elif provider == "deepseek" and settings.DEEPSEEK_API_KEY:
        _llm_available_cache = True
    elif provider == "qwen" and settings.QWEN_API_KEY:
        _llm_available_cache = True
    else:
        _llm_available_cache = False
    return _llm_available_cache


def sse_event(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@app.get("/api/health")
async def health():
    from llm_providers import get_provider
    provider_name = "none"
    try:
        provider = get_provider()
        provider_name = provider.name
    except Exception:
        pass
    return {
        "status": "ok",
        "version": "0.1.0",
        "llm_configured": _check_llm_available(),
        "llm_provider": provider_name,
    }


@app.post("/api/analyze")
async def analyze(request: AnalysisRequest):
    from config import settings

    async def event_stream():
        try:
            # ===== 快速校验 =====
            target_url = request.url or request.app_store_url or request.google_play_url
            if not request.file_data and not target_url:
                yield sse_event("error", {"message": "请提供网址或上传评论文件"})
                return

            # ===== 阶段 1: parsing =====
            yield sse_event("parsing", {"stage": "parsing", "progress": 5, "message": "正在解析请求..."})

            analysis_goal = request.analysis_goal or ""
            if analysis_goal:
                yield sse_event("parsing", {"stage": "parsing", "progress": 8,
                               "message": f"\u5206\u6790\u76ee\u6807: {analysis_goal}"})

            # ===== 阶段 2: collecting =====
            yield sse_event("collecting", {"stage": "collecting", "progress": 10, "message": "正在识别网站并采集评论..."})

            site_type = "unknown"

            if request.file_data:
                reviews = await collect_reviews_from_file(request.file_data)
                site_type = "file"
            elif target_url:
                reviews, site_type = await collect_from_url(target_url, max_pages=settings.RSS_MAX_PAGES)
            else:
                yield sse_event("error", {"message": "请提供网址或上传评论文件"})
                return

            if not reviews:
                yield sse_event("error", {"message": "未采集到任何评论，请尝试其他 URL 或上传文件"})
                return

            yield sse_event("collecting", {"stage": "collecting", "progress": 30,
                            "message": f"采集完成，共 {len(reviews)} 条评论（来源: {site_type}）"})

            # ===== 阶段 3: cleaning =====
            yield sse_event("cleaning", {"stage": "cleaning", "progress": 35, "message": "\u6b63\u5728\u6e05\u6d17\u6570\u636e..."})
            cleaned = clean_reviews(reviews)
            valid = get_valid_reviews(cleaned)
            stats = get_cleaning_stats(cleaned)
            yield sse_event("cleaning", {"stage": "cleaning", "progress": 45,
                            "stats": stats, "message": f"\u6e05\u6d17\u5b8c\u6210\uff0c\u6709\u6548\u8bc4\u8bba {len(valid)} \u6761"})

            # ===== 阶段 4-8: LLM / 统计模式 =====
            llm_available = _check_llm_available()

            if llm_available:
                # 小数据集（≤50条）：单次 LLM 调用完成全部任务
                if len(valid) <= 50:
                    yield sse_event("analyzing", {"stage": "analyzing", "progress": 50,
                                 "message": f"LLM 一体化分析中（{len(valid)} 条评论）..."})

                    reviews_json = format_reviews_for_llm(valid)
                    goal_hint = f"\n\n分析目标: {analysis_goal}。" if analysis_goal else ""
                    user_prompt = json.dumps(reviews_json, ensure_ascii=False, indent=2) + goal_hint

                    try:
                        result = await analyze_batch(ALL_IN_ONE_SYSTEM, user_prompt, max_tokens=4096)
                    except Exception as e:
                        print(f"All-in-one LLM failed: {e}")
                        result = {}

                    # 解析 topics → findings
                    findings = []
                    for topic in result.get("topics", []):
                        findings.append(ReviewFinding(
                            finding_id=str(uuid.uuid4())[:8],
                            topic=topic.get("topic", "Unknown"),
                            description=topic.get("description", ""),
                            severity=topic.get("severity", "medium"),
                            sentiment=topic.get("sentiment", "neutral"),
                            sample_count=len(topic.get("review_ids", [])),
                            review_ids=topic.get("review_ids", []),
                            excerpts=topic.get("excerpts", []),
                            confidence=topic.get("confidence", 0.5),
                            evidence_level="sufficient",
                            conflicting_feedback=topic.get("conflicting_feedback", []),
                            source="llm", uncertainty="",
                        ))

                    # 证据验证（本地）
                    yield sse_event("evidence", {"stage": "evidence", "progress": 65, "message": "证据验证中..."})
                    findings = await validate_evidence(findings, valid)

                    # 解析需求
                    yield sse_event("prd", {"stage": "prd", "progress": 75, "message": "生成需求与测试用例..."})
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

                    # 解析测试用例
                    test_cases = []
                    for i, tc in enumerate(result.get("test_cases", [])):
                        req_id = tc.get("req_id", "")
                        source_review_ids = tc.get("source_review_ids", [])
                        if not source_review_ids:
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

                    # 解析校验报告
                    val = result.get("validation", {})
                    validation_report = ValidationReport(
                        validation_passed=val.get("validation_passed", True),
                        issues=val.get("issues", []),
                        traceability=val.get("traceability", {}),
                        summary=val.get("summary", ""),
                    )

                    # 推送 testcase + validating 阶段
                    yield sse_event("testcase", {"stage": "testcase", "progress": 85, "message": f"生成 {len(test_cases)} 个测试用例"})
                    yield sse_event("validating", {"stage": "validating", "progress": 95, "message": "校验可追溯性..."})

                else:
                    # 大数据集：两步 LLM 调用
                    # 阶段 4: analyzing (并发批次)
                    yield sse_event("analyzing", {"stage": "analyzing", "progress": 50, "message": "LLM 主题发现中..."})
                    topics = await discover_topics(valid, analysis_goal)
                    findings = topics_to_findings(topics)

                    # 阶段 5: evidence (纯本地，瞬间完成)
                    yield sse_event("evidence", {"stage": "evidence", "progress": 65, "message": "证据验证中..."})
                    findings = await validate_evidence(findings, valid)

                    # 阶段 6-8: PRD + 测试用例 + 校验 (合并为一次 LLM 调用)
                    yield sse_event("prd", {"stage": "prd", "progress": 75, "message": "LLM 生成需求、测试用例与校验中..."})
                    findings_json = [{
                        "finding_id": f.finding_id, "topic": f.topic, "description": f.description,
                        "severity": f.severity, "sentiment": f.sentiment, "sample_count": f.sample_count,
                        "review_ids": f.review_ids[:10], "excerpts": f.excerpts[:3],
                    } for f in findings]
                    goal_hint = f"\n\n分析目标: {analysis_goal}。" if analysis_goal else ""

                    try:
                        result = await analyze_batch(ANALYSIS_PIPELINE_SYSTEM,
                            json.dumps(findings_json, ensure_ascii=False) + goal_hint,
                            max_tokens=4096)
                    except Exception as e:
                        print(f"Combined analysis failed: {e}")
                        result = {}

                    # 解析需求
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

                    # 解析测试用例
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

                    # 解析校验报告
                    val = result.get("validation", {})
                    validation_report = ValidationReport(
                        validation_passed=val.get("validation_passed", True),
                        issues=val.get("issues", []),
                        traceability=val.get("traceability", {}),
                        summary=val.get("summary", ""),
                    )

                    # 推送 testcase + validating 阶段
                    yield sse_event("testcase", {"stage": "testcase", "progress": 85, "message": f"生成 {len(test_cases)} 个测试用例"})
                    yield sse_event("validating", {"stage": "validating", "progress": 95, "message": "校验可追溯性..."})

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
            done_data = {
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
                "warnings": [] if llm_available else [
                    "\u672a\u914d\u7f6e LLM \u63d0\u4f9b\u5546\uff0c\u5206\u6790\u7ed3\u679c\u57fa\u4e8e\u7edf\u8ba1\u6a21\u5f0f\u751f\u6210\uff0c\u4ec5\u4f9b\u53c2\u8003",
                ],
            }

            # 自动保存到历史记录
            try:
                from database import save_analysis
                ratings = [r.rating for r in valid]
                avg_rating = sum(ratings) / len(ratings) if ratings else 0
                source_url = request.url or request.app_store_url or request.google_play_url or ""
                source_type = site_type
                # 从 URL 提取应用名
                app_name = ""
                try:
                    if source_url:
                        import re
                        m = re.search(r'/app/([^/]+)/', source_url)
                        if m:
                            app_name = m.group(1).replace('-', ' ').title()
                except Exception:
                    pass
                save_analysis({
                    "app_name": app_name,
                    "source_url": source_url,
                    "source_type": source_type,
                    "analysis_goal": analysis_goal,
                    "reviews_count": len(valid),
                    "findings_count": len(findings),
                    "requirements_count": len(requirements),
                    "testcases_count": len(test_cases),
                    "avg_rating": avg_rating,
                    "result": done_data,
                })
            except Exception as e:
                print(f"Failed to save analysis: {e}")

            yield sse_event("done", done_data)

        except Exception as e:
            yield sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ===== 历史记录 API =====

@app.get("/api/history")
async def get_history():
    from database import list_analyses
    return {"history": list_analyses()}


@app.get("/api/history/{analysis_id}")
async def get_history_detail(analysis_id: int):
    from database import get_analysis
    result = get_analysis(analysis_id)
    if not result:
        return {"error": "Not found"}
    return result


@app.delete("/api/history/{analysis_id}")
async def delete_history(analysis_id: int):
    from database import delete_analysis
    success = delete_analysis(analysis_id)
    return {"success": success}


# ===== LLM 设置 API =====

LLM_PROVIDERS_INFO = [
    {"key": "openai", "name": "OpenAI", "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"], "requires_key": True,
     "default_base_url": "https://api.openai.com/v1"},
    {"key": "deepseek", "name": "DeepSeek", "models": ["deepseek-chat", "deepseek-coder"], "requires_key": True,
     "default_base_url": "https://api.deepseek.com/v1"},
    {"key": "qwen", "name": "通义千问 Qwen", "models": ["qwen-turbo", "qwen-plus", "qwen-max"], "requires_key": True,
     "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"key": "ollama", "name": "Ollama (本地)", "models": ["qwen2.5:7b", "llama3", "mistral"], "requires_key": False,
     "default_base_url": "http://localhost:11434/v1"},
]


@app.get("/api/settings/llm")
async def get_llm_settings():
    from config import settings
    from llm_providers import get_provider

    provider_key = settings.LLM_PROVIDER.lower()
    api_key_set = False
    if provider_key == "ollama":
        api_key_set = True
    elif provider_key == "openai":
        api_key_set = bool(settings.OPENAI_API_KEY)
    elif provider_key == "deepseek":
        api_key_set = bool(settings.DEEPSEEK_API_KEY)
    elif provider_key == "qwen":
        api_key_set = bool(settings.QWEN_API_KEY)

    # 获取当前模型
    model = settings.LLM_MODEL
    if provider_key == "ollama":
        model = settings.OLLAMA_MODEL

    # 获取 base_url
    base_url = settings.OPENAI_BASE_URL
    if provider_key == "deepseek":
        base_url = settings.DEEPSEEK_BASE_URL
    elif provider_key == "qwen":
        base_url = settings.QWEN_BASE_URL
    elif provider_key == "ollama":
        base_url = settings.OLLAMA_BASE_URL

    return {
        "providers": LLM_PROVIDERS_INFO,
        "current": {
            "provider": provider_key,
            "model": model,
            "api_key_set": api_key_set,
            "base_url": base_url,
            "timeout": settings.LLM_TIMEOUT,
        },
    }


@app.put("/api/settings/llm")
async def update_llm_settings(request: Request):
    from config import settings
    from llm_providers import reset_provider
    import importlib

    data = await request.json()
    provider = data.get("provider", "openai")
    model = data.get("model", "")
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "")
    timeout = data.get("timeout", 120)

    # 更新 settings 内存
    settings.LLM_PROVIDER = provider
    settings.LLM_TIMEOUT = timeout

    if provider == "ollama":
        settings.OLLAMA_MODEL = model or "qwen2.5:7b"
        settings.OLLAMA_BASE_URL = base_url or "http://localhost:11434/v1"
    else:
        settings.LLM_MODEL = model or "gpt-4o-mini"
        if provider == "openai":
            settings.OPENAI_API_KEY = api_key
            settings.OPENAI_BASE_URL = base_url or "https://api.openai.com/v1"
        elif provider == "deepseek":
            settings.DEEPSEEK_API_KEY = api_key
            settings.DEEPSEEK_BASE_URL = base_url or "https://api.deepseek.com/v1"
        elif provider == "qwen":
            settings.QWEN_API_KEY = api_key
            settings.QWEN_BASE_URL = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 持久化到 .env 文件
    _save_env_file(provider, model, api_key, base_url, timeout)

    # 重置 LLM 可用性缓存
    global _llm_available_cache
    _llm_available_cache = None

    # 重置 provider 单例
    reset_provider()

    return {"success": True, "provider": provider, "model": model}


def _save_env_file(provider: str, model: str, api_key: str, base_url: str, timeout: int):
    """将 LLM 配置写入 .env 文件持久化"""
    from pathlib import Path

    env_path = Path(__file__).parent / ".env"

    # 读取现有 .env 内容
    kv = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    kv[k.strip()] = v

    # 更新配置项
    kv["LLM_PROVIDER"] = provider
    kv["LLM_TIMEOUT"] = str(timeout)

    if provider == "ollama":
        kv["OLLAMA_MODEL"] = model or "qwen2.5:7b"
        kv["OLLAMA_BASE_URL"] = base_url or "http://localhost:11434/v1"
    else:
        kv["LLM_MODEL"] = model or "gpt-4o-mini"
        if provider == "openai":
            if api_key:
                kv["OPENAI_API_KEY"] = api_key
            kv["OPENAI_BASE_URL"] = base_url or "https://api.openai.com/v1"
        elif provider == "deepseek":
            if api_key:
                kv["DEEPSEEK_API_KEY"] = api_key
            kv["DEEPSEEK_BASE_URL"] = base_url or "https://api.deepseek.com/v1"
        elif provider == "qwen":
            if api_key:
                kv["QWEN_API_KEY"] = api_key
            kv["QWEN_BASE_URL"] = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # 写回 .env
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in kv.items():
            f.write(f"{k}={v}\n")


@app.post("/api/settings/llm/test")
async def test_llm_connection(request: Request):
    from config import settings
    import time

    # 先尝试从请求体获取配置（支持未保存时测试）
    try:
        body = await request.json()
    except Exception:
        body = {}
    print(f"[TEST] Received body: provider={body.get('provider')}, api_key={'set' if body.get('api_key') else 'empty'}")

    provider_key = body.get("provider", settings.LLM_PROVIDER).lower()
    api_key = body.get("api_key", "")
    base_url = body.get("base_url", "")
    model = body.get("model", "")

    # 检查 API key（优先用请求体中的）
    if provider_key != "ollama":
        if not api_key:
            # 从 settings 中获取
            if provider_key == "openai":
                api_key = settings.OPENAI_API_KEY
            elif provider_key == "deepseek":
                api_key = settings.DEEPSEEK_API_KEY
            elif provider_key == "qwen":
                api_key = settings.QWEN_API_KEY
        if not api_key:
            return {"success": False, "error": "未配置 API Key", "latency_ms": 0}

    # 临时创建 provider 进行测试
    try:
        from llm_providers.openai_provider import OpenAIProvider
        from llm_providers import get_provider

        if api_key or provider_key == "ollama":
            # 用请求体的配置创建临时 provider
            if provider_key == "deepseek":
                test_provider = OpenAIProvider(
                    api_key=api_key,
                    base_url=base_url or settings.DEEPSEEK_BASE_URL,
                    model=model or "deepseek-chat",
                    timeout=settings.LLM_TIMEOUT,
                )
                test_provider._name = "deepseek"
            elif provider_key == "qwen":
                test_provider = OpenAIProvider(
                    api_key=api_key,
                    base_url=base_url or settings.QWEN_BASE_URL,
                    model=model or "qwen-turbo",
                    timeout=settings.LLM_TIMEOUT,
                )
                test_provider._name = "qwen"
            elif provider_key == "ollama":
                test_provider = OpenAIProvider(
                    api_key="",
                    base_url=base_url or settings.OLLAMA_BASE_URL,
                    model=model or settings.OLLAMA_MODEL,
                    timeout=settings.LLM_TIMEOUT,
                )
                test_provider._name = "ollama"
            else:
                test_provider = OpenAIProvider(
                    api_key=api_key,
                    base_url=base_url or settings.OPENAI_BASE_URL,
                    model=model or "gpt-4o-mini",
                    timeout=settings.LLM_TIMEOUT,
                )
                test_provider._name = "openai"
        else:
            test_provider = get_provider()

        start = time.time()
        result = await test_provider.chat(
            "You are a helpful assistant.",
            "Reply with exactly: OK",
            temperature=0,
            max_tokens=10,
            response_format_json=False,
        )
        latency = int((time.time() - start) * 1000)

        return {"success": True, "provider": provider_key, "latency_ms": latency, "response": str(result)}
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'last_attempt') and hasattr(e.last_attempt, 'exception'):
            cause = e.last_attempt.exception()
            if cause:
                error_msg = str(cause)
        elif hasattr(e, '__cause__') and e.__cause__:
            error_msg = str(e.__cause__)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        return {"success": False, "error": error_msg, "latency_ms": 0}


# ===== 导出 API =====

@app.post("/api/export/pdf")
async def export_pdf(request: Request):
    data = await request.json()
    from exporters.pdf_exporter import export_pdf
    pdf_bytes = export_pdf(data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=app-review-analysis.pdf"},
    )


@app.post("/api/export/docx")
async def export_docx(request: Request):
    data = await request.json()
    from exporters.docx_exporter import export_docx
    docx_bytes = export_docx(data)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=app-review-analysis.docx"},
    )


@app.post("/api/export/xlsx")
async def export_xlsx(request: Request):
    data = await request.json()
    from exporters.xlsx_exporter import export_xlsx
    xlsx_bytes = export_xlsx(data)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=app-review-analysis.xlsx"},
    )


# ===== 启动时自动保存分析结果 =====

@app.post("/api/save")
async def save_analysis_result(request: Request):
    data = await request.json()
    from database import save_analysis
    analysis_id = save_analysis(data)
    return {"id": analysis_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
