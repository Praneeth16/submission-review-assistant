from __future__ import annotations

import csv
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .schemas import DatasetSummary, SubmissionRecord


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
TRAIN_PATH = DATA_DIR / "submission_gallery_analysis_units_train.csv"
TEST_PATH = DATA_DIR / "submission_gallery_analysis_units_test.csv"
PROGRESSION_PATH = DATA_DIR / "submission_gallery_student_progression.csv"
EVAL_DIR = REPO_ROOT / "eval"


def _split_field(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(" || ") if part.strip()]


def _load_rows(path: Path) -> list[SubmissionRecord]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        raw_rows = list(csv.DictReader(csv_file))

    rows: list[SubmissionRecord] = []
    for row in raw_rows:
        rows.append(
            SubmissionRecord(
                student_id=row["student_id"],
                session=row["session"],
                author=row["author"],
                score=int(row["score"]),
                primary_title=row["primary_title"],
                primary_platform=row["primary_platform"],
                primary_video_url=row["primary_video_url"],
                primary_thumbnail_url=row["primary_thumbnail_url"],
                candidate_count=int(row["candidate_count"]),
                all_titles=_split_field(row["all_titles"]),
                all_video_urls=_split_field(row["all_video_urls"]),
                all_platforms=_split_field(row["all_platforms"]),
                selection_notes=[part.strip() for part in row["selection_notes"].split(",") if part.strip()],
                split=row["split"],
                row_score_band=row["row_score_band"],
            )
        )
    return rows


@lru_cache(maxsize=1)
def get_train_rows() -> list[SubmissionRecord]:
    return _load_rows(TRAIN_PATH)


@lru_cache(maxsize=1)
def get_test_rows() -> list[SubmissionRecord]:
    return _load_rows(TEST_PATH)


@lru_cache(maxsize=1)
def get_all_rows() -> list[SubmissionRecord]:
    return get_train_rows() + get_test_rows()


@lru_cache(maxsize=1)
def get_progression_rows() -> list[dict[str, str]]:
    with PROGRESSION_PATH.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def get_dataset_summary() -> DatasetSummary:
    rows = get_all_rows()
    bands = Counter(row.row_score_band for row in rows)
    sessions = sorted({row.session for row in rows})
    students = len({row.student_id for row in rows})
    return DatasetSummary(
        train_rows=len(get_train_rows()),
        test_rows=len(get_test_rows()),
        students=students,
        sessions=sessions,
        score_bands=dict(sorted(bands.items())),
    )


def list_submissions(split: str = "test", session: str | None = None, query: str | None = None) -> list[SubmissionRecord]:
    base = get_train_rows() if split == "train" else get_test_rows()
    rows = base
    if session:
        rows = [row for row in rows if row.session == session]
    if query:
        q = query.lower().strip()
        rows = [
            row
            for row in rows
            if q in row.primary_title.lower()
            or q in row.author.lower()
            or q in row.student_id
        ]
    return rows


def get_submission(student_id: str, session: str) -> SubmissionRecord | None:
    for row in get_all_rows():
        if row.student_id == student_id and row.session == session:
            return row
    return None


def get_progression(student_id: str) -> dict[str, str] | None:
    for row in get_progression_rows():
        if row["student_id"] == student_id:
            return row
    return None


def find_similar_examples(target: SubmissionRecord, limit: int = 3) -> list[SubmissionRecord]:
    candidates = [
        row
        for row in get_train_rows()
        if not (row.student_id == target.student_id and row.session == target.session)
    ]

    def similarity_key(row: SubmissionRecord):
        same_band = 1 if row.row_score_band == target.row_score_band else 0
        same_session = 1 if row.session == target.session else 0
        same_platform = 1 if row.primary_platform == target.primary_platform else 0
        candidate_gap = abs(row.candidate_count - target.candidate_count)
        score_gap = abs(row.score - target.score)
        return (
            -same_band,
            -same_session,
            -same_platform,
            candidate_gap,
            score_gap,
            row.primary_title.lower(),
        )

    return sorted(candidates, key=similarity_key)[:limit]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_eval_runs(mode: str) -> list[dict]:
    mode_dir = EVAL_DIR / mode
    if not mode_dir.exists():
        return []

    runs = []
    for run_dir in sorted([path for path in mode_dir.iterdir() if path.is_dir()], reverse=True):
        metrics_path = run_dir / "metrics.json"
        config_path = run_dir / "run_config.json"
        if not metrics_path.exists() or not config_path.exists():
            continue
        metrics = _read_json(metrics_path)
        config = _read_json(config_path)
        runs.append(
            {
                "mode": mode,
                "run_name": run_dir.name,
                "created_at": run_dir.name,
                "count": metrics.get("count", 0),
                "exact_score_accuracy": metrics.get("exact_score_accuracy"),
                "within_250_accuracy": metrics.get("within_250_accuracy"),
                "score_band_accuracy": metrics.get("score_band_accuracy"),
                "mean_absolute_error": metrics.get("mean_absolute_error"),
                "gemini_configured": config.get("gemini_configured", False),
            }
        )
    return runs


def get_eval_run(mode: str, run_name: str) -> dict | None:
    run_dir = EVAL_DIR / mode / run_name
    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "run_config.json"
    summary_path = run_dir / "summary.csv"
    if not metrics_path.exists() or not config_path.exists() or not summary_path.exists():
        return None

    with summary_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    return {
        "mode": mode,
        "run_name": run_name,
        "metrics": _read_json(metrics_path),
        "config": _read_json(config_path),
        "rows": rows,
    }


def list_comparisons() -> list[dict]:
    compare_dir = EVAL_DIR / "compare"
    if not compare_dir.exists():
        return []

    items = []
    for run_dir in sorted([path for path in compare_dir.iterdir() if path.is_dir()], reverse=True):
        comparison_path = run_dir / "comparison.json"
        if not comparison_path.exists():
            continue
        payload = _read_json(comparison_path)
        items.append(
            {
                "comparison_name": run_dir.name,
                "created_at": run_dir.name,
                "label_a": payload.get("label_a", "run_a"),
                "label_b": payload.get("label_b", "run_b"),
                "shared_count": payload.get("shared_count", 0),
                "metric_deltas": payload.get("metric_deltas", {}),
            }
        )
    return items


def get_comparison(comparison_name: str) -> dict | None:
    comparison_path = EVAL_DIR / "compare" / comparison_name / "comparison.json"
    if not comparison_path.exists():
        return None
    payload = _read_json(comparison_path)
    payload["comparison_name"] = comparison_name
    return payload
