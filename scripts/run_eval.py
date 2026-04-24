#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.data import get_test_rows, get_train_rows
from backend.app.review_runner import ReviewRunner


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
        "mae_by_confidence": error_by_confidence,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "agent"], required=True)
    parser.add_argument("--split", choices=["train", "test"], default="test")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    dataset = get_train_rows() if args.split == "train" else get_test_rows()
    if args.limit:
        dataset = dataset[: args.limit]

    runner = ReviewRunner()

    run_name = args.run_name or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = REPO_ROOT / "eval" / args.mode / run_name
    runs_dir = run_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for submission in dataset:
        result = runner.review(submission, args.mode)

        row = {
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
            "summary": result.summary,
        }
        summary_rows.append(row)

        result_path = runs_dir / f"{submission.student_id}_{submission.session}.json"
        result_path.write_text(
            json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    metrics = compute_metrics(summary_rows)
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    summary_csv_path = run_dir / "summary.csv"
    with summary_csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(summary_rows[0].keys()) if summary_rows else [])
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
                "gemini_configured": runner.configured,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote eval run to {run_dir}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
