"""Pydantic 数据模型"""
from typing import Optional
from pydantic import BaseModel


# ===== 请求模型 =====

class AnalysisRequest(BaseModel):
    """分析请求"""
    app_store_url: str = ""
    sort: str = "mostrecent"
    file_data: Optional[list[dict]] = None
    file_format: str = "json"
    analysis_goal: str = ""


# ===== 评论模型 =====

class ReviewRaw(BaseModel):
    review_id: str
    rating: int
    title: str
    content: str
    author: str
    version: str
    date: str = ""
    vote_sum: int
    vote_count: int


class ReviewCleaned(ReviewRaw):
    is_duplicate: bool = False
    is_noise: bool = False
    language: str = "unknown"
    fingerprint: str = ""


# ===== 分析结果模型 =====

class ReviewFinding(BaseModel):
    finding_id: str
    topic: str
    description: str
    severity: str
    sentiment: str
    sample_count: int
    review_ids: list[str]
    excerpts: list[str]
    confidence: float
    evidence_level: str
    conflicting_feedback: list[str] = []
    source: str = "llm"
    uncertainty: str = ""


class Requirement(BaseModel):
    req_id: str
    title: str
    description: str
    user_story: str
    priority: str
    version: str = "v1.0"
    related_finding_ids: list[str] = []
    related_review_ids: list[str] = []
    acceptance_criteria: list[str] = []
    is_assumption: bool = False


class TestCase(BaseModel):
    case_id: str
    req_id: str
    title: str
    preconditions: list[str] = []
    steps: list[str] = []
    expected_result: str = ""
    source_review_ids: list[str] = []
    priority: str = "P1"


# ===== 校验模型 =====

class ValidationReport(BaseModel):
    validation_passed: bool = True
    issues: list[dict] = []
    traceability: dict = {}
    summary: str = ""
