#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def read_summary(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    return {(row["student_id"], row["session"]): row for row in rows}


def row_error(row: dict) -> int:
    return abs(int(row["predicted_score"]) - int(row["ground_truth_score"]))


def metric_snapshot(rows: dict[tuple[str, str], dict]) -> dict:
    values = list(rows.values())
    if not values:
        return {}
    exact = sum(1 for row in values if int(row["predicted_score"]) == int(row["ground_truth_score"]))
    within_250 = sum(1 for row in values if row_error(row) <= 250)
    band_accuracy = sum(1 for row in values if row["predicted_score_band"] == row["ground_truth_band"])
    mae = sum(row_error(row) for row in values) / len(values)
    return {
        "count": len(values),
        "exact_score_accuracy": exact / len(values),
        "within_250_accuracy": within_250 / len(values),
        "score_band_accuracy": band_accuracy / len(values),
        "mean_absolute_error": mae,
    }


def compare_runs(run_a: dict[tuple[str, str], dict], run_b: dict[tuple[str, str], dict]) -> dict:
    run_a_metrics = metric_snapshot(run_a)
    run_b_metrics = metric_snapshot(run_b)
    shared_keys = sorted(set(run_a.keys()) & set(run_b.keys()))
    comparisons = []
    for key in shared_keys:
        a = run_a[key]
        b = run_b[key]
        a_error = row_error(a)
        b_error = row_error(b)
        comparisons.append(
            {
                "student_id": key[0],
                "session": key[1],
                "title": a["title"],
                "ground_truth_score": int(a["ground_truth_score"]),
                "run_a_predicted_score": int(a["predicted_score"]),
                "run_b_predicted_score": int(b["predicted_score"]),
                "run_a_error": a_error,
                "run_b_error": b_error,
                "error_delta": a_error - b_error,
                "run_a_confidence": a["confidence"],
                "run_b_confidence": b["confidence"],
            }
        )

    b_better = sorted(
        [row for row in comparisons if row["error_delta"] > 0],
        key=lambda row: row["error_delta"],
        reverse=True,
    )
    a_better = sorted(
        [row for row in comparisons if row["error_delta"] < 0],
        key=lambda row: row["error_delta"],
    )

    return {
        "shared_count": len(shared_keys),
        "run_a_metrics": run_a_metrics,
        "run_b_metrics": run_b_metrics,
        "metric_deltas": {
            "exact_score_accuracy": run_b_metrics.get("exact_score_accuracy", 0.0)
            - run_a_metrics.get("exact_score_accuracy", 0.0),
            "within_250_accuracy": run_b_metrics.get("within_250_accuracy", 0.0)
            - run_a_metrics.get("within_250_accuracy", 0.0),
            "score_band_accuracy": run_b_metrics.get("score_band_accuracy", 0.0)
            - run_a_metrics.get("score_band_accuracy", 0.0),
            "mean_absolute_error": run_b_metrics.get("mean_absolute_error", 0.0)
            - run_a_metrics.get("mean_absolute_error", 0.0),
        },
        "run_b_best_wins": b_better[:10],
        "run_a_best_wins": a_better[:10],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", required=True, help="Path to first eval run directory")
    parser.add_argument("--run-b", required=True, help="Path to second eval run directory")
    parser.add_argument("--label-a", default="run_a")
    parser.add_argument("--label-b", default="run_b")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    run_a_dir = Path(args.run_a)
    run_b_dir = Path(args.run_b)
    run_a_summary = read_summary(run_a_dir / "summary.csv")
    run_b_summary = read_summary(run_b_dir / "summary.csv")

    result = compare_runs(run_a_summary, run_b_summary)
    result["label_a"] = args.label_a
    result["label_b"] = args.label_b
    result["run_a_path"] = str(run_a_dir)
    result["run_b_path"] = str(run_b_dir)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        repo_root = Path(__file__).resolve().parents[1]
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = repo_root / "eval" / "compare" / name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "comparison.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote comparison to {output_path}")
    print(json.dumps(result["metric_deltas"], indent=2))


if __name__ == "__main__":
    main()
