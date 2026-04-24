from __future__ import annotations

import pytest

from backend.app.mock_review import build_review_preview, fallback_predicted_score
from backend.app.schemas import SubmissionRecord


BAND_CASES = [
    ("early_below_750", 500, 700),
    ("mid_750_999", 875, 900),
    ("strong_1000_1499", 1250, 1400),
    ("elite_1500_plus", 1750, 2200),
]


def _make_submission(band: str, score: int) -> SubmissionRecord:
    return SubmissionRecord(
        student_id="999",
        session="S1",
        author="Test Author",
        score=score,
        primary_title="Example project",
        primary_platform="YouTube",
        primary_video_url="https://youtu.be/abc",
        primary_thumbnail_url="https://i.ytimg.com/vi/abc/default.jpg",
        candidate_count=1,
        all_titles=["Example project"],
        all_video_urls=["https://youtu.be/abc"],
        all_platforms=["YouTube"],
        selection_notes=[],
        split="test",
        row_score_band=band,
    )


@pytest.mark.parametrize("band,expected_midpoint,ground_truth", BAND_CASES)
def test_fallback_uses_band_midpoint_not_ground_truth(
    band: str, expected_midpoint: int, ground_truth: int
) -> None:
    submission = _make_submission(band, ground_truth)
    preview = build_review_preview(submission, "agent", model_name="test-model")

    assert preview.source == "fallback"
    assert preview.confidence == "low"
    assert preview.needs_human_review is True
    assert preview.predicted_score == expected_midpoint
    assert preview.predicted_score != ground_truth or ground_truth == expected_midpoint
    assert fallback_predicted_score(band) == expected_midpoint


def test_fallback_never_derives_score_from_ground_truth() -> None:
    low_gt = _make_submission("mid_750_999", 750)
    high_gt = _make_submission("mid_750_999", 999)
    a = build_review_preview(low_gt, "agent", model_name="m")
    b = build_review_preview(high_gt, "agent", model_name="m")
    assert a.predicted_score == b.predicted_score, (
        "Fallback must be blind to submission.score — both mid-band samples "
        "should produce the same predicted score."
    )
