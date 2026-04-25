from __future__ import annotations

from .schemas import (
    ClaimVerification,
    ReviewCriterion,
    ReviewPreview,
    SubmissionRecord,
    TraceStep,
)


BAND_MIDPOINTS: dict[str, int] = {
    "early_below_750": 500,
    "mid_750_999": 875,
    "strong_1000_1499": 1250,
    "elite_1500_plus": 1750,
}


def band_for_score(score: int) -> str:
    if score >= 1500:
        return "elite_1500_plus"
    if score >= 1000:
        return "strong_1000_1499"
    if score >= 750:
        return "mid_750_999"
    return "early_below_750"


def clamp(value: int, lower: int = 0, upper: int = 2500) -> int:
    return max(lower, min(upper, value))


def fallback_predicted_score(band: str | None) -> int:
    """Band midpoint — intentionally ignores ground-truth score to avoid leak.

    Unknown or missing band defaults to the mid_750_999 midpoint so ad-hoc
    submissions without historical anchors still produce a valid response.
    """

    if not band:
        return BAND_MIDPOINTS["mid_750_999"]
    return BAND_MIDPOINTS.get(band, 875)


def build_review_preview(
    submission: SubmissionRecord,
    mode: str,
    *,
    model_name: str,
    reason: str = "Gemini is not configured, so no evidence was collected.",
) -> ReviewPreview:
    """Evidence-less fallback dossier.

    The fallback MUST NOT read submission.score. It returns a band-anchored
    placeholder, marks confidence low, and forces human review so downstream
    metrics cannot confuse this with a real Gemini run.
    """

    predicted_score = fallback_predicted_score(submission.row_score_band)
    band_label = submission.row_score_band or "unknown (ad-hoc submission)"

    summary = (
        f"No artifact evidence was collected for '{submission.primary_title}'. "
        f"This fallback dossier reports the midpoint of the {band_label} band as a placeholder. "
        f"Reason: {reason}"
    )

    criteria = [
        ReviewCriterion(
            criterion="Problem clarity",
            finding=(
                f"Title '{submission.primary_title}' is the only signal available; "
                "no video or code was inspected."
            ),
            evidence_source="primary_title",
            confidence="low",
            provisional_score_band="medium",
        ),
        ReviewCriterion(
            criterion="Demo quality",
            finding=(
                f"Primary platform is {submission.primary_platform} with "
                f"{submission.candidate_count} candidate artifact(s); none inspected."
            ),
            evidence_source="primary_platform,candidate_count",
            confidence="low",
            provisional_score_band="medium",
        ),
        ReviewCriterion(
            criterion="Completeness and polish",
            finding="No implementation evidence gathered in fallback mode.",
            evidence_source="none",
            confidence="low",
            provisional_score_band="medium",
        ),
    ]

    claims = ClaimVerification(
        confirmed_claims=[],
        weak_claims=[],
        unsupported_claims=[
            "Fallback mode did not verify any project claim against video or code."
        ],
        open_questions=[
            "What does the primary video actually demonstrate?",
            "Does a code artifact exist that supports the title?",
        ],
    )

    trace = [
        TraceStep(
            step=1,
            current_question="Is Gemini configured for evidence collection?",
            selected_tool="config_check",
            tool_result_summary=reason,
            belief_update="No artifact evidence can be gathered; dossier is a placeholder.",
            next_step="Route this submission to a human reviewer.",
        ),
        TraceStep(
            step=2,
            current_question="What is the weakest safe placeholder for a score?",
            selected_tool="band_midpoint",
            tool_result_summary=(
                f"Used midpoint of historical band {submission.row_score_band} → {predicted_score}."
            ),
            belief_update="Placeholder carries no artifact evidence. Do not compare against agent runs.",
            next_step="Re-run with Gemini configured.",
        ),
    ]

    return ReviewPreview(
        student_id=submission.student_id,
        session=submission.session,
        mode=mode,  # type: ignore[arg-type]
        model=model_name,
        source="fallback",
        predicted_score=clamp(predicted_score),
        predicted_score_band=band_for_score(predicted_score),  # type: ignore[arg-type]
        confidence="low",
        needs_human_review=True,
        summary=summary,
        criterion_evidence=criteria,
        claim_verification=claims,
        trace=trace,
    )
