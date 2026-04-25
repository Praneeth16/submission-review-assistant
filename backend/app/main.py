from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .data import (
    get_comparison,
    get_dataset_summary,
    get_eval_run,
    get_progression,
    get_submission,
    list_comparisons,
    list_eval_runs,
    list_submissions,
)
from .gemini_client import GeminiClient
from .schemas import AdhocReviewRequest, SubmissionListResponse, SubmissionRecord
from .review_runner import ReviewRunner
from .schema_validation import validate_review_result


app = FastAPI(title="Submission Review Assistant API", version="0.1.0")
review_runner = ReviewRunner(GeminiClient())


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": review_runner.configured,
        "model": review_runner.client.model,
    }


@app.get("/api/datasets/summary")
def dataset_summary():
    return get_dataset_summary()


@app.get("/api/submissions", response_model=SubmissionListResponse)
def submissions(
    split: str = Query(default="test", pattern="^(train|test)$"),
    session: Optional[str] = Query(default=None, pattern=r"^[\w\- ]{1,64}$"),
    query: Optional[str] = None,
    limit: int = Query(default=40, ge=1, le=200),
):
    items = list_submissions(split=split, session=session, query=query)
    return SubmissionListResponse(
        items=items[:limit],
        total=len(items),
        split=split,
        session=session,
        query=query,
    )


@app.get("/api/submissions/{student_id}/{session}")
def submission_detail(student_id: str, session: str):
    submission = get_submission(student_id=student_id, session=session)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "submission": submission,
        "progression": get_progression(student_id),
    }


@app.get("/api/submissions/{student_id}/{session}/review-preview")
def submission_review_preview(student_id: str, session: str, mode: str = Query(default="agent", pattern="^(baseline|agent)$")):
    submission = get_submission(student_id=student_id, session=session)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    preview = review_runner.review(submission, mode)
    payload = preview.model_dump()
    # Enforce the shared output contract at the boundary so any drift between
    # the Pydantic model and schemas/review_result.schema.json shows up in CI.
    validate_review_result(payload)
    return payload


@app.post("/api/submissions/review-adhoc")
def submission_review_adhoc(payload: AdhocReviewRequest):
    submission = SubmissionRecord(
        student_id=payload.student_id or "adhoc",
        session=payload.session,
        author=payload.author,
        score=None,
        primary_title=payload.title,
        primary_platform=payload.platform,
        primary_video_url=payload.video_url,
        primary_thumbnail_url=payload.thumbnail_url,
        candidate_count=1,
        all_titles=[payload.title],
        all_video_urls=[payload.video_url],
        all_platforms=[payload.platform],
        selection_notes=["adhoc_submission"],
        split="adhoc",
        row_score_band=None,
    )
    preview = review_runner.review(submission, payload.mode)
    body = preview.model_dump()
    validate_review_result(body)
    return body


@app.get("/api/eval/runs")
def eval_runs(mode: str = Query(default="baseline", pattern="^(baseline|agent)$")):
    return {"items": list_eval_runs(mode), "mode": mode}


@app.get("/api/eval/runs/{mode}/{run_name}")
def eval_run_detail(mode: str, run_name: str):
    item = get_eval_run(mode, run_name)
    if not item:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return item


@app.get("/api/eval/comparisons")
def eval_comparisons():
    return {"items": list_comparisons()}


@app.get("/api/eval/comparisons/{comparison_name}")
def eval_comparison_detail(comparison_name: str):
    item = get_comparison(comparison_name)
    if not item:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return item
