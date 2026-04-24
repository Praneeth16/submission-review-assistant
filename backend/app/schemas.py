from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


ScoreBand = Literal[
    "early_below_750",
    "mid_750_999",
    "strong_1000_1499",
    "elite_1500_plus",
]


ConfidenceLevel = Literal["high", "medium", "low"]


class DatasetSummary(BaseModel):
    train_rows: int
    test_rows: int
    students: int
    sessions: list[str]
    score_bands: dict[str, int]


class SubmissionRecord(BaseModel):
    student_id: str
    session: str
    author: str
    score: int
    primary_title: str
    primary_platform: str
    primary_video_url: str
    primary_thumbnail_url: str
    candidate_count: int
    all_titles: list[str]
    all_video_urls: list[str]
    all_platforms: list[str]
    selection_notes: list[str]
    split: str
    row_score_band: ScoreBand


class SubmissionListResponse(BaseModel):
    items: list[SubmissionRecord]
    total: int
    split: str
    session: Optional[str] = None
    query: Optional[str] = None


class ReviewCriterion(BaseModel):
    criterion: str
    finding: str
    evidence_source: str
    confidence: ConfidenceLevel
    provisional_score_band: Literal["low", "medium", "high"]


class ClaimVerification(BaseModel):
    confirmed_claims: list[str]
    weak_claims: list[str]
    unsupported_claims: list[str]
    open_questions: list[str]


class TraceStep(BaseModel):
    step: int
    current_question: str
    selected_tool: str
    tool_result_summary: str
    belief_update: str
    next_step: str


class ReviewPreview(BaseModel):
    student_id: str
    session: str
    mode: Literal["baseline", "agent"]
    model: str
    predicted_score: int = Field(ge=0, le=2500)
    predicted_score_band: ScoreBand
    confidence: ConfidenceLevel
    needs_human_review: bool
    summary: str
    criterion_evidence: list[ReviewCriterion]
    claim_verification: ClaimVerification
    trace: list[TraceStep]
