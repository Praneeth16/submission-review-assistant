from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import ValidationError

from .artifact_utils import extract_direct_repo_candidates
from .data import find_similar_examples
from .gemini_client import GeminiClient, GeminiClientError
from .mock_review import band_for_score, build_review_preview, clamp
from .prompt_templates import load_prompt_templates
from .rubric import RUBRIC_V1
from .video_utils import fetch_youtube_transcript
from .schemas import (
    ClaimVerification,
    ReviewCriterion,
    ReviewPreview,
    SubmissionRecord,
    TraceStep,
)


logger = logging.getLogger(__name__)


# Gemini v1beta tool configs. These keys (`url_context`, `google_search`) are
# tied to the v1beta generateContent surface. If you bump GEMINI_API_BASE to a
# stable v1 surface or a different model family, re-verify tool schemas before
# shipping — Gemini has renamed tool keys between previews in the past.
URL_CONTEXT_TOOL = [{"url_context": {}}]
GOOGLE_SEARCH_TOOL = [{"google_search": {}}]


@dataclass
class StepResult:
    question: str
    tool_name: str
    result_summary: str
    belief_update: str
    next_step: str


def _normalize_confidence(value: str | None) -> str:
    mapping = {
        "high": "high",
        "medium": "medium",
        "mid": "medium",
        "med": "medium",
        "low": "low",
    }
    if not value:
        logger.warning("Empty confidence from model; defaulting to low")
        return "low"
    normalized = mapping.get(value.strip().lower())
    if normalized is None:
        logger.warning("Unknown confidence value %r from model; defaulting to low", value)
        return "low"
    return normalized


def _normalize_score_band(value: str | None) -> str:
    mapping = {
        "low": "low",
        "medium": "medium",
        "mid": "medium",
        "med": "medium",
        "high": "high",
    }
    if not value:
        logger.warning("Empty provisional_score_band from model; defaulting to medium")
        return "medium"
    normalized = mapping.get(value.strip().lower())
    if normalized is None:
        logger.warning("Unknown score_band value %r from model; defaulting to medium", value)
        return "medium"
    return normalized


class ReviewRunner:
    def __init__(self, client: GeminiClient | None = None, prompt_templates: dict[str, str] | None = None):
        self.client = client or GeminiClient()
        self.prompt_templates = prompt_templates or load_prompt_templates()

    @property
    def configured(self) -> bool:
        return self.client.configured

    def review(self, submission: SubmissionRecord, mode: str) -> ReviewPreview:
        if not self.configured:
            return build_review_preview(
                submission,
                mode,
                model_name=self.client.model,
                reason="GEMINI_API_KEY is not set — fallback dossier only.",
            )

        try:
            return self._review(submission, mode)
        except (GeminiClientError, KeyError, ValidationError, json.JSONDecodeError) as exc:
            logger.exception("Gemini review failed for %s/%s", submission.student_id, submission.session)
            return build_review_preview(
                submission,
                mode,
                model_name=self.client.model,
                reason=f"Gemini request failed: {type(exc).__name__}: {exc}",
            )

    def _review(self, submission: SubmissionRecord, mode: str) -> ReviewPreview:
        trace_steps: list[StepResult] = []

        plan = self._plan_review(submission, mode)
        trace_steps.append(plan["trace"])

        video_review = self._inspect_primary_video(submission, mode)
        trace_steps.append(video_review["trace"])

        if mode == "agent":
            repo_review = self._inspect_repo_artifacts(submission)
            trace_steps.append(repo_review["trace"])
            repo_summary = repo_review["repo_summary"]
        else:
            repo_summary = {
                "repo_signal": "not_run",
                "repo_url": "",
                "stack_signals": [],
                "implementation_signals": [],
                "limitations": ["Repo inspection is disabled in baseline mode."],
            }

        similar_examples = self._retrieve_similar_examples(submission)
        trace_steps.append(similar_examples["trace"])

        if mode == "agent" and submission.candidate_count > 1:
            alternate_review = self._inspect_alternate_artifacts(submission)
            trace_steps.append(alternate_review["trace"])
            alternate_summary = alternate_review["artifact_summary"]
        else:
            alternate_summary = {
                "alternate_signal": "not_run",
                "confidence_adjustment": "none",
                "notes": ["Alternate artifact inspection was skipped in this run."],
            }

        synthesis = self._synthesize_review(
            submission=submission,
            mode=mode,
            review_plan=plan["review_plan"],
            video_summary=video_review["video_summary"],
            repo_summary=repo_summary,
            similar_examples=similar_examples["examples"],
            alternate_summary=alternate_summary,
        )
        trace_steps.append(synthesis["trace"])

        preview = self._build_review_preview(
            submission=submission,
            mode=mode,
            synthesis=synthesis["review_result"],
            trace_steps=trace_steps,
        )
        return preview

    def _plan_review(self, submission: SubmissionRecord, mode: str) -> dict:
        prompt = self.prompt_templates["plan_review"].format(
            mode=mode,
            student_id=submission.student_id,
            session=submission.session,
            author=submission.author,
            primary_title=submission.primary_title,
            primary_platform=submission.primary_platform,
            primary_video_url=submission.primary_video_url,
            candidate_count=submission.candidate_count,
            selection_notes=", ".join(submission.selection_notes) or "none",
            rubric_lines="\n".join(f"- {criterion}" for criterion in RUBRIC_V1),
        )
        data = self.client.generate_json(prompt)
        return {
            "review_plan": data["review_plan"],
            "trace": StepResult(
                question="What evidence should this review collect first?",
                tool_name="plan_review",
                result_summary=data["trace"]["result_summary"],
                belief_update=data["trace"]["belief_update"],
                next_step=data["trace"]["next_step"],
            ),
        }

    def _inspect_primary_video(self, submission: SubmissionRecord, mode: str) -> dict:
        transcript_result = fetch_youtube_transcript(submission.primary_video_url)
        transcript_block = transcript_result.as_prompt_block()
        if transcript_block:
            transcript_section = (
                "Verbatim YouTube transcript (timestamps in [MM:SS]). Ground your claims in these "
                "quotes when possible and cite timestamps in the result summary:\n"
                f"{transcript_block}"
            )
        else:
            transcript_section = (
                "No YouTube transcript was retrievable for this URL. "
                f"Reason: {transcript_result.error or 'unknown'}. "
                "Rely on url_context-sourced metadata, captions, and description, and lower "
                "confidence accordingly."
            )

        prompt = self.prompt_templates["inspect_demo_video"].format(
            primary_video_url=submission.primary_video_url,
            primary_title=submission.primary_title,
            author=submission.author,
            session=submission.session,
            mode=mode,
            transcript_section=transcript_section,
        )
        data = self.client.generate_json(prompt, tools=URL_CONTEXT_TOOL)
        trace_summary = data["trace"]["result_summary"]
        if transcript_result.available and transcript_result.language:
            trace_summary = (
                f"{trace_summary} (transcript fetched: language={transcript_result.language}, "
                f"{len(transcript_result.snippets)} snippets)"
            )
        return {
            "video_summary": data["video_summary"],
            "transcript_available": transcript_result.available,
            "trace": StepResult(
                question="What does the primary video URL actually show?",
                tool_name="inspect_demo_video",
                result_summary=trace_summary,
                belief_update=data["trace"]["belief_update"],
                next_step=data["trace"]["next_step"],
            ),
        }

    def _inspect_alternate_artifacts(self, submission: SubmissionRecord) -> dict:
        prompt = self.prompt_templates["inspect_alternate_artifacts"].format(
            primary_title=submission.primary_title,
            all_titles=submission.all_titles,
            all_video_urls=submission.all_video_urls,
            all_platforms=submission.all_platforms,
        )
        data = self.client.generate_json(prompt, tools=URL_CONTEXT_TOOL)
        return {
            "artifact_summary": data["artifact_summary"],
            "trace": StepResult(
                question="Do alternate artifacts strengthen or weaken confidence?",
                tool_name="inspect_external_artifacts",
                result_summary=data["trace"]["result_summary"],
                belief_update=data["trace"]["belief_update"],
                next_step=data["trace"]["next_step"],
            ),
        }

    def _inspect_repo_artifacts(self, submission: SubmissionRecord) -> dict:
        known_artifact_urls = [submission.primary_video_url, *submission.all_video_urls]
        direct_repo_candidates = extract_direct_repo_candidates(known_artifact_urls)

        prompt = self.prompt_templates["inspect_repo_artifacts"].format(
            primary_title=submission.primary_title,
            author=submission.author,
            session=submission.session,
            all_video_urls=known_artifact_urls,
            direct_repo_candidates=direct_repo_candidates,
        )

        tools = URL_CONTEXT_TOOL if direct_repo_candidates else GOOGLE_SEARCH_TOOL
        data = self.client.generate_json(prompt, tools=tools)
        return {
            "repo_summary": data["repo_summary"],
            "trace": StepResult(
                question="What code evidence exists for this submission?",
                tool_name="inspect_repo",
                result_summary=data["trace"]["result_summary"],
                belief_update=data["trace"]["belief_update"],
                next_step=data["trace"]["next_step"],
            ),
        }

    def _retrieve_similar_examples(self, submission: SubmissionRecord) -> dict:
        examples = find_similar_examples(submission, limit=3)
        summary = [
            {
                "student_id": row.student_id,
                "session": row.session,
                "title": row.primary_title,
                "score": row.score,
                "platform": row.primary_platform,
                "score_band": row.row_score_band,
            }
            for row in examples
        ]
        result_summary = (
            "Retrieved "
            f"{len(summary)} train-set anchors with similar score band and artifact shape."
        )
        return {
            "examples": summary,
            "trace": StepResult(
                question="Which historical examples provide a useful score anchor?",
                tool_name="retrieve_similar_scored_examples",
                result_summary=result_summary,
                belief_update="Historical anchors are available for calibration, but they do not override fresh evidence.",
                next_step="Synthesize the dossier with evidence, uncertainty, and a provisional score.",
            ),
        }

    def _synthesize_review(
        self,
        *,
        submission: SubmissionRecord,
        mode: str,
        review_plan: dict,
        video_summary: dict,
        repo_summary: dict,
        similar_examples: list[dict],
        alternate_summary: dict,
    ) -> dict:
        prompt = self.prompt_templates["synthesize_review"].format(
            mode=mode,
            student_id=submission.student_id,
            session=submission.session,
            author=submission.author,
            primary_title=submission.primary_title,
            split=submission.split,
            row_score_band=submission.row_score_band,
            rubric_lines="\n".join(f"- {criterion}" for criterion in RUBRIC_V1),
            review_plan=review_plan,
            video_summary=video_summary,
            repo_summary=repo_summary,
            alternate_summary=alternate_summary,
            similar_examples=similar_examples,
        )

        data = self.client.generate_json(prompt, tools=GOOGLE_SEARCH_TOOL)
        return {
            "review_result": data,
            "trace": StepResult(
                question="What score and dossier are justified by the gathered evidence?",
                tool_name="synthesize_dossier",
                result_summary=data["trace"]["result_summary"],
                belief_update=data["trace"]["belief_update"],
                next_step=data["trace"]["next_step"],
            ),
        }

    def _build_review_preview(
        self,
        *,
        submission: SubmissionRecord,
        mode: str,
        synthesis: dict,
        trace_steps: list[StepResult],
    ) -> ReviewPreview:
        predicted_score = clamp(int(synthesis["predicted_score"]))
        confidence = _normalize_confidence(synthesis.get("confidence"))

        criterion_evidence = []
        for criterion in synthesis["criterion_evidence"]:
            normalized = dict(criterion)
            normalized["confidence"] = _normalize_confidence(criterion.get("confidence"))
            normalized["provisional_score_band"] = _normalize_score_band(
                criterion.get("provisional_score_band")
            )
            criterion_evidence.append(ReviewCriterion(**normalized))
        claim_verification = ClaimVerification(**synthesis["claim_verification"])
        trace = [
            TraceStep(
                step=index,
                current_question=step.question,
                selected_tool=step.tool_name,
                tool_result_summary=step.result_summary,
                belief_update=step.belief_update,
                next_step=step.next_step,
            )
            for index, step in enumerate(trace_steps, start=1)
        ]

        return ReviewPreview(
            student_id=submission.student_id,
            session=submission.session,
            mode=mode,  # type: ignore[arg-type]
            model=self.client.model,
            source="gemini",
            predicted_score=predicted_score,
            predicted_score_band=band_for_score(predicted_score),  # type: ignore[arg-type]
            confidence=confidence,  # type: ignore[arg-type]
            needs_human_review=bool(synthesis["needs_human_review"]),
            summary=synthesis["summary"],
            criterion_evidence=criterion_evidence,
            claim_verification=claim_verification,
            trace=trace,
        )
