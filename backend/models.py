"""应用数据模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewRaw(BaseModel):
    """原始评论数据"""
    review_id: str
    rating: int
    title: str
    content: str
    author: str
    date: datetime
    version: str
    vote_sum: int = 0
    vote_count: int = 0


class ReviewCleaned(BaseModel):
    """清洗后的评论数据"""
    review_id: str
    rating: int
    title: str
    content: str
    author: str
    date: datetime
    version: str
    vote_sum: int
    vote_count: int
    language: str = ""
    content_length: int = 0
    is_duplicate: bool = False


class ReviewFinding(BaseModel):
    """分析发现"""
    finding_id: str
    topic: str
    description: str
    severity: str  # critical / high / medium / low
    sentiment: str  # positive / negative / neutral / mixed
    sample_count: int
    review_ids: list[str] = []
    excerpts: list[str] = []
    confidence: float = 0.0  # 0.0 ~ 1.0
    evidence_level: str = "insufficient"  # sufficient / limited / insufficient
    conflicting_feedback: list[str] = []
    source: str = "llm"  # llm / statistical / rule
    uncertainty: str = ""


class Requirement(BaseModel):
    """PRD 需求"""
    req_id: str
    title: str
    description: str
    user_story: str = ""
    priority: str = "P1"  # P0 / P1 / P2
    version: str = "v1.0"
    related_finding_ids: list[str] = []
    related_review_ids: list[str] = []
    acceptance_criteria: list[str] = []
    is_assumption: bool = False


class TestCase(BaseModel):
    """测试用例"""
    case_id: str
    req_id: str
    title: str
    preconditions: list[str] = []
    steps: list[str] = []
    expected_result: str = ""
    source_review_ids: list[str] = []
    priority: str = "P1"


class AnalysisRequest(BaseModel):
    """分析请求"""
    app_url: str
    goal: str = ""
    constraint: str = ""
    max_reviews: int = 500


class AnalysisProgress(BaseModel):
    """分析进度"""
    stage: str  # collecting / cleaning / analyzing / evidence / prd / testcase / validating / done / error
    progress: int = 0  # 0-100
    message: str = ""
    data: Optional[dict] = None
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    """最终分析结果"""
    app_id: str
    app_name: str = ""
    total_reviews: int = 0
    cleaned_reviews: int = 0
    findings: list[ReviewFinding] = []
    requirements: list[Requirement] = []
    test_cases: list[TestCase] = []
    validation_report: dict = {}
    data_limitations: list[str] = []
    warnings: list[str] = []