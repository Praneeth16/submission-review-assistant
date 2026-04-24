#!/usr/bin/env python3

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path


TEST_RATIO = 0.2
SEED = 42


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def student_mean_band(scores):
    mean_score = sum(scores) / len(scores)
    if mean_score >= 1500:
        return "elite_1500_plus"
    if mean_score >= 1000:
        return "strong_1000_1499"
    if mean_score >= 750:
        return "mid_750_999"
    return "early_below_750"


def row_score_band(score):
    score = int(score)
    if score >= 1500:
        return "elite_1500_plus"
    if score >= 1000:
        return "strong_1000_1499"
    if score >= 750:
        return "mid_750_999"
    return "early_below_750"


def choose_test_students(student_scores, ratio, seed):
    rng = random.Random(seed)
    by_band = defaultdict(list)
    for student_id, scores in student_scores.items():
        by_band[student_mean_band(scores)].append(student_id)

    test_students = set()
    for band, student_ids in by_band.items():
        student_ids = list(student_ids)
        rng.shuffle(student_ids)
        if len(student_ids) <= 1:
            test_count = 0
        else:
            test_count = max(1, round(len(student_ids) * ratio))
            test_count = min(test_count, len(student_ids) - 1)
        test_students.update(student_ids[:test_count])

    return test_students


def build_split_rows(analysis_rows, test_students):
    train_rows = []
    test_rows = []

    for row in analysis_rows:
        enriched = dict(row)
        enriched["split"] = "test" if row["student_id"] in test_students else "train"
        enriched["row_score_band"] = row_score_band(row["score"])
        target = test_rows if enriched["split"] == "test" else train_rows
        target.append(enriched)

    return train_rows, test_rows


def build_manifest_rows(analysis_rows, test_students):
    by_student = defaultdict(list)
    for row in analysis_rows:
        by_student[row["student_id"]].append(row)

    manifest_rows = []
    for student_id, items in sorted(by_student.items(), key=lambda pair: int(pair[0])):
        scores = [int(item["score"]) for item in items]
        manifest_rows.append(
            {
                "student_id": student_id,
                "split": "test" if student_id in test_students else "train",
                "student_mean_score": round(sum(scores) / len(scores), 2),
                "student_mean_band": student_mean_band(scores),
                "unit_count": len(items),
                "sessions_present": ",".join(sorted({item["session"] for item in items})),
            }
        )
    return manifest_rows


def print_summary(train_rows, test_rows, manifest_rows):
    def summarize(rows):
        return dict(sorted(Counter(row["row_score_band"] for row in rows).items()))

    student_split_counts = Counter(row["split"] for row in manifest_rows)
    print(f"Train rows: {len(train_rows)}")
    print(f"Test rows: {len(test_rows)}")
    print(f"Train students: {student_split_counts.get('train', 0)}")
    print(f"Test students: {student_split_counts.get('test', 0)}")
    print(f"Train row score bands: {summarize(train_rows)}")
    print(f"Test row score bands: {summarize(test_rows)}")


def main():
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"
    analysis_path = data_dir / "submission_gallery_analysis_units.csv"

    analysis_rows = read_csv(analysis_path)
    student_scores = defaultdict(list)
    for row in analysis_rows:
        student_scores[row["student_id"]].append(int(row["score"]))

    test_students = choose_test_students(student_scores, TEST_RATIO, SEED)
    train_rows, test_rows = build_split_rows(analysis_rows, test_students)
    manifest_rows = build_manifest_rows(analysis_rows, test_students)

    output_fieldnames = list(train_rows[0].keys()) if train_rows else list(analysis_rows[0].keys()) + ["split", "row_score_band"]
    manifest_fieldnames = [
        "student_id",
        "split",
        "student_mean_score",
        "student_mean_band",
        "unit_count",
        "sessions_present",
    ]

    write_csv(data_dir / "submission_gallery_analysis_units_train.csv", output_fieldnames, train_rows)
    write_csv(data_dir / "submission_gallery_analysis_units_test.csv", output_fieldnames, test_rows)
    write_csv(data_dir / "submission_gallery_split_manifest.csv", manifest_fieldnames, manifest_rows)

    print_summary(train_rows, test_rows, manifest_rows)


if __name__ == "__main__":
    main()
