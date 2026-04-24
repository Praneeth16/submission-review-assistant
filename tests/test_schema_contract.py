from __future__ import annotations

import pytest

from backend.app.mock_review import build_review_preview
from backend.app.schema_validation import (
    ReviewResultSchemaError,
    validate_review_result,
)
from backend.app.schemas import SubmissionRecord


def _submission() -> SubmissionRecord:
    return SubmissionRecord(
        student_id="123",
        session="S1",
        author="A",
        score=900,
        primary_title="Demo",
        primary_platform="YouTube",
        primary_video_url="https://youtu.be/abc",
        primary_thumbnail_url="https://i.ytimg.com/vi/abc/default.jpg",
        candidate_count=1,
        all_titles=["Demo"],
        all_video_urls=["https://youtu.be/abc"],
        all_platforms=["YouTube"],
        selection_notes=[],
        split="test",
        row_score_band="mid_750_999",
    )


def test_fallback_preview_matches_shared_schema() -> None:
    preview = build_review_preview(_submission(), "agent", model_name="m")
    validate_review_result(preview.model_dump())


def test_missing_source_is_rejected() -> None:
    payload = build_review_preview(_submission(), "agent", model_name="m").model_dump()
    payload.pop("source")
    with pytest.raises(ReviewResultSchemaError):
        validate_review_result(payload)


def test_invalid_confidence_is_rejected() -> None:
    payload = build_review_preview(_submission(), "agent", model_name="m").model_dump()
    payload["confidence"] = "uncertain"
    with pytest.raises(ReviewResultSchemaError):
        validate_review_result(payload)
