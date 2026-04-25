from __future__ import annotations

import pytest

from backend.app.schemas import AdhocReviewRequest, SubmissionRecord


def test_adhoc_request_defaults() -> None:
    req = AdhocReviewRequest(title="Demo", video_url="https://youtu.be/abc")
    assert req.session == "S1"
    assert req.mode == "agent"
    assert req.platform == "YouTube"
    assert req.author == "unknown"
    assert req.student_id == "adhoc"


def test_adhoc_request_enforces_session_enum() -> None:
    with pytest.raises(ValueError):
        AdhocReviewRequest(title="Demo", video_url="https://youtu.be/abc", session="S3")  # type: ignore[arg-type]


def test_submission_record_accepts_none_score() -> None:
    record = SubmissionRecord(
        student_id="adhoc",
        session="S1",
        author="a",
        score=None,
        primary_title="t",
        primary_platform="YouTube",
        primary_video_url="https://youtu.be/abc",
        primary_thumbnail_url="",
        candidate_count=1,
        all_titles=["t"],
        all_video_urls=["https://youtu.be/abc"],
        all_platforms=["YouTube"],
        selection_notes=["adhoc_submission"],
        split="adhoc",
        row_score_band=None,
    )
    assert record.score is None
    assert record.row_score_band is None
