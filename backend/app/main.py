from __future__ import annotations

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
from .schemas import SubmissionListResponse
from .review_runner import ReviewRunner


app = FastAPI(title="Submission Review Copilot API", version="0.1.0")
review_runner = ReviewRunner(GeminiClient())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    session: Optional[str] = Query(default=None, pattern="^(S1|S2)$"),
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
    return review_runner.review(submission, mode)


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
