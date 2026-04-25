#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.data import get_train_rows
from backend.app.gemini_client import GeminiClient
from backend.app.review_runner import ReviewRunner
from backend.app.schemas import SubmissionRecord


def split_train_for_optimization(seed: int = 7, val_ratio: float = 0.2):
    rows = get_train_rows()
    by_student = defaultdict(list)
    for row in rows:
        by_student[row.student_id].append(row)

    student_ids = list(by_student.keys())
    random.Random(seed).shuffle(student_ids)
    val_count = max(1, round(len(student_ids) * val_ratio))
    val_students = set(student_ids[:val_count])

    trainset = []
    valset = []
    for row in rows:
        example = {
            "student_id": row.student_id,
            "session": row.session,
            "author": row.author,
            "score": row.score,
            "row_score_band": row.row_score_band,
            "primary_title": row.primary_title,
            "primary_platform": row.primary_platform,
            "primary_video_url": row.primary_video_url,
            "primary_thumbnail_url": row.primary_thumbnail_url,
            "candidate_count": row.candidate_count,
            "all_titles": row.all_titles,
            "all_video_urls": row.all_video_urls,
            "all_platforms": row.all_platforms,
            "selection_notes": row.selection_notes,
            "split": row.split,
        }
        if row.student_id in val_students:
            valset.append(example)
        else:
            trainset.append(example)
    return trainset, valset


def score_result(result: dict, example: dict) -> float:
    ground_truth = int(example["score"])
    predicted = int(result["predicted_score"])
    mae = abs(predicted - ground_truth)
    mae_component = max(0.0, 1.0 - (mae / 1000.0))
    band_component = 1.0 if result["predicted_score_band"] == example["row_score_band"] else 0.0
    review_penalty = 0.1 if result.get("needs_human_review") else 0.0
    return max(0.0, min(1.0, 0.65 * mae_component + 0.35 * band_component - review_penalty))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed-file",
        default=str(REPO_ROOT / "prompts" / "seed_prompt_templates.json"),
    )
    parser.add_argument("--max-metric-calls", type=int, default=40)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    try:
        import gepa.optimize_anything as oa
        from gepa.optimize_anything import EngineConfig, GEPAConfig, optimize_anything
    except ImportError as exc:
        raise SystemExit(
            "GEPA is not installed. Install it with `pip install gepa` before running this script."
        ) from exc

    reflection_lm = os.getenv("GEPA_REFLECTION_LM")
    if not reflection_lm:
        raise SystemExit(
            "Set GEPA_REFLECTION_LM to the reflection model GEPA should use, for example an OpenAI or Gemini-compatible LiteLLM model string."
        )

    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY before running GEPA optimization.")

    seed_path = Path(args.seed_file)
    seed_candidate = json.loads(seed_path.read_text(encoding="utf-8"))
    trainset, valset = split_train_for_optimization()

    def evaluator(candidate, example):
        prompt_templates = dict(seed_candidate)
        prompt_templates.update(candidate)
        runner = ReviewRunner(client=GeminiClient(), prompt_templates=prompt_templates)

        submission = SubmissionRecord(
            student_id=example["student_id"],
            session=example["session"],
            author=example["author"],
            score=int(example["score"]),
            primary_title=example["primary_title"],
            primary_platform=example["primary_platform"],
            primary_video_url=example["primary_video_url"],
            primary_thumbnail_url=example["primary_thumbnail_url"],
            candidate_count=int(example["candidate_count"]),
            all_titles=list(example["all_titles"]),
            all_video_urls=list(example["all_video_urls"]),
            all_platforms=list(example["all_platforms"]),
            selection_notes=list(example["selection_notes"]),
            split=example["split"],
            row_score_band=example["row_score_band"],
        )
        result = runner.review(submission, "agent")

        score = score_result(result.model_dump(), example)
        side_info = {
            "title": example["primary_title"],
            "ground_truth_score": example["score"],
            "predicted_score": result.predicted_score,
            "ground_truth_band": example["row_score_band"],
            "predicted_band": result.predicted_score_band,
            "confidence": result.confidence,
            "needs_human_review": result.needs_human_review,
        }
        oa.log(
            f"title={example['primary_title']} gt={example['score']} pred={result.predicted_score} "
            f"gt_band={example['row_score_band']} pred_band={result.predicted_score_band}"
        )
        return score, side_info

    config = GEPAConfig(engine=EngineConfig(max_metric_calls=args.max_metric_calls))
    config.reflection.reflection_lm = reflection_lm

    result = optimize_anything(
        seed_candidate=seed_candidate,
        evaluator=evaluator,
        dataset=trainset,
        valset=valset,
        objective=(
            "Optimize the prompt templates for Submission Review Assistant so the agent produces "
            "more accurate and better-calibrated review dossiers from project demo artifacts."
        ),
        background=(
            "The candidate is a dict of prompt templates for a handwritten review runner. "
            "The evaluator scores candidates using score error, score-band accuracy, and cautious "
            "abstention behavior on a leak-safe train/validation split."
        ),
        config=config,
    )

    run_name = args.run_name or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = REPO_ROOT / "eval" / "gepa" / run_name
    output_dir.mkdir(parents=True, exist_ok=True)

    best_candidate = result.best_candidate
    (output_dir / "optimized_prompt_templates.json").write_text(
        json.dumps(best_candidate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "seed_prompt_templates.json").write_text(
        json.dumps(seed_candidate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    metadata = {
        "train_examples": len(trainset),
        "val_examples": len(valset),
        "max_metric_calls": args.max_metric_calls,
        "reflection_lm": reflection_lm,
        "seed_file": str(seed_path),
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote GEPA outputs to {output_dir}")


if __name__ == "__main__":
    main()
