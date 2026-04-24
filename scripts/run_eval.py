#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.data import get_test_rows, get_train_rows  # noqa: E402
from backend.app.review_runner import ReviewRunner  # noqa: E402


def score_band(score: int) -> str:
    if score >= 1500:
        return "elite_1500_plus"
    if score >= 1000:
        return "strong_1000_1499"
    if score >= 750:
        return "mid_750_999"
    return "early_below_750"


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def compute_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {}

    abs_errors = [abs(row["predicted_score"] - row["ground_truth_score"]) for row in rows]
    exact = sum(1 for row in rows if row["predicted_score"] == row["ground_truth_score"])
    within_250 = sum(1 for row in rows if abs(row["predicted_score"] - row["ground_truth_score"]) <= 250)
    band_accuracy = sum(1 for row in rows if row["predicted_score_band"] == row["ground_truth_band"])
    confidence_counts = Counter(row["confidence"] for row in rows)
    review_counts = Counter("yes" if row["needs_human_review"] else "no" for row in rows)
    source_counts = Counter(row.get("source", "unknown") for row in rows)

    error_by_confidence = {}
    for confidence in ("high", "medium", "low"):
        subset = [
            abs(row["predicted_score"] - row["ground_truth_score"])
            for row in rows
            if row["confidence"] == confidence
        ]
        error_by_confidence[confidence] = mean(subset) if subset else None

    return {
        "count": len(rows),
        "exact_score_accuracy": exact / len(rows),
        "within_250_accuracy": within_250 / len(rows),
        "mean_absolute_error": mean(abs_errors),
        "score_band_accuracy": band_accuracy / len(rows),
        "confidence_counts": dict(confidence_counts),
        "needs_human_review_counts": dict(review_counts),
        "source_counts": dict(source_counts),
        "mae_by_confidence": error_by_confidence,
    }


def _review_one(runner: ReviewRunner, submission, mode: str) -> dict:
    result = runner.review(submission, mode)
    return {
        "student_id": submission.student_id,
        "session": submission.session,
        "author": submission.author,
        "title": submission.primary_title,
        "ground_truth_score": submission.score,
        "ground_truth_band": submission.row_score_band,
        "predicted_score": result.predicted_score,
        "predicted_score_band": result.predicted_score_band,
        "confidence": result.confidence,
        "needs_human_review": result.needs_human_review,
        "model": result.model,
        "source": result.source,
        "summary": result.summary,
        "_full_result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "agent"], required=True)
    parser.add_argument("--split", choices=["train", "test"], default="test")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--run-name", default=None)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Parallel Gemini calls. 1 = sequential. Respect rate limits.",
    )
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help=(
            "Allow the runner to fall back to the evidence-less mock dossier when Gemini is not "
            "configured. By default the runner refuses so eval metrics never mix with fallback."
        ),
    )
    args = parser.parse_args()

    dataset = get_train_rows() if args.split == "train" else get_test_rows()
    if args.limit:
        dataset = dataset[: args.limit]

    runner = ReviewRunner()

    if not runner.configured and not args.allow_fallback:
        print(
            "ERROR: GEMINI_API_KEY is not configured. "
            "Refusing to run evaluation on fallback-only predictions. "
            "Set the key, or pass --allow-fallback if you explicitly want a fallback-only baseline "
            "(which will be clearly labelled source=fallback in the output).",
            file=sys.stderr,
        )
        return 2

    run_name = args.run_name or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = REPO_ROOT / "eval" / args.mode / run_name
    runs_dir = run_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict] = []

    if args.concurrency > 1 and runner.configured:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(_review_one, runner, sub, args.mode): sub for sub in dataset}
            for future in as_completed(futures):
                summary_rows.append(future.result())
    else:
        for submission in dataset:
            summary_rows.append(_review_one(runner, submission, args.mode))

    for row in summary_rows:
        full = row.pop("_full_result")
        result_path = runs_dir / f"{row['student_id']}_{row['session']}.json"
        result_path.write_text(
            json.dumps(full.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    metrics = compute_metrics(summary_rows)
    fallback_count = metrics.get("source_counts", {}).get("fallback", 0)
    metrics["fallback_row_count"] = fallback_count
    metrics["gemini_configured"] = runner.configured

    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    summary_csv_path = run_dir / "summary.csv"
    fieldnames = [
        "student_id",
        "session",
        "author",
        "title",
        "ground_truth_score",
        "ground_truth_band",
        "predicted_score",
        "predicted_score_band",
        "confidence",
        "needs_human_review",
        "model",
        "source",
        "summary",
    ]
    with summary_csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if summary_rows:
            writer.writeheader()
            writer.writerows(summary_rows)

    config_path = run_dir / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "mode": args.mode,
                "split": args.split,
                "count": len(dataset),
                "limit": args.limit,
                "run_name": run_name,
                "concurrency": args.concurrency,
                "allow_fallback": args.allow_fallback,
                "gemini_configured": runner.configured,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote eval run to {run_dir}")
    print(json.dumps(metrics, indent=2))

    if fallback_count and not args.allow_fallback:
        print(
            f"WARNING: {fallback_count} row(s) used fallback dossiers despite Gemini being configured. "
            "These are tagged source=fallback and should be excluded from serious comparisons.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
