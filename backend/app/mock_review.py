from .schemas import ClaimVerification, ReviewCriterion, ReviewPreview, SubmissionRecord, TraceStep


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


def build_review_preview(submission: SubmissionRecord, mode: str) -> ReviewPreview:
    delta = -100 if mode == "baseline" else 0
    if submission.candidate_count > 1 and mode == "agent":
        delta += 50
    predicted_score = clamp(submission.score + delta)
    confidence = "high" if submission.candidate_count == 1 else "medium"
    if "generic_title_fallback" in submission.selection_notes:
        confidence = "low" if mode == "baseline" else "medium"

    summary = (
        f"{submission.primary_title} is treated as the primary artifact for {submission.author}. "
        f"The {mode} preview is driven by dataset evidence today, with Gemini Flash 3.1 review to follow."
    )

    criteria = [
        ReviewCriterion(
            criterion="Problem clarity",
            finding=f"The title suggests a concrete product direction: {submission.primary_title}.",
            evidence_source="primary_title",
            confidence=confidence,
            provisional_score_band="medium" if submission.score < 1000 else "high",
        ),
        ReviewCriterion(
            criterion="Demo quality",
            finding=f"Primary platform is {submission.primary_platform} with {submission.candidate_count} candidate artifact(s).",
            evidence_source="primary_platform,candidate_count",
            confidence="medium",
            provisional_score_band="medium",
        ),
        ReviewCriterion(
            criterion="Completeness and polish",
            finding=f"The submission sits in the {submission.row_score_band} band in the historical dataset.",
            evidence_source="row_score_band",
            confidence="medium",
            provisional_score_band="low" if submission.score < 750 else "high",
        ),
    ]

    claims = ClaimVerification(
        confirmed_claims=[
            f"Primary review target resolved to {submission.primary_video_url}.",
            f"Session is {submission.session} and split is {submission.split}.",
        ],
        weak_claims=[
            "Feature-level verification has not yet been run against code or video transcript."
        ],
        unsupported_claims=[
            "No runtime proof has been collected yet."
        ],
        open_questions=[
            "Does the repo back up the headline demo claims?",
            "Should alternate artifacts change the confidence for this submission?",
        ],
    )

    trace = [
        TraceStep(
            step=1,
            current_question="What is the primary artifact for this submission?",
            selected_tool="read_submission_page",
            tool_result_summary=f"Selected {submission.primary_platform} artifact with {submission.candidate_count} candidate option(s).",
            belief_update="Primary artifact locked for review input.",
            next_step="Inspect the primary video URL.",
        ),
        TraceStep(
            step=2,
            current_question="How much evidence is available before video or repo analysis?",
            selected_tool="dataset_context",
            tool_result_summary=f"Historical band is {submission.row_score_band}; selection notes are {', '.join(submission.selection_notes)}.",
            belief_update="Confidence starts from metadata strength rather than full artifact verification.",
            next_step="Run Gemini Flash 3.1 on the video and then verify claims against code.",
        ),
    ]

    if mode == "agent":
        trace.append(
            TraceStep(
                step=3,
                current_question="Which follow-up source should resolve uncertainty fastest?",
                selected_tool="planner",
                tool_result_summary="The repo and video transcript are the next evidence sources because the current dossier is metadata-heavy.",
                belief_update="Agent path is staged for evidence collection instead of scoring directly.",
                next_step="Inspect demo video, then inspect repo.",
            )
        )

    return ReviewPreview(
        student_id=submission.student_id,
        session=submission.session,
        mode=mode,  # type: ignore[arg-type]
        model="gemini-flash-3.1",
        predicted_score=predicted_score,
        predicted_score_band=band_for_score(predicted_score),  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        needs_human_review=confidence == "low",
        summary=summary,
        criterion_evidence=criteria,
        claim_verification=claims,
        trace=trace,
    )
