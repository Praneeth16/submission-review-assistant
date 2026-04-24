#!/usr/bin/env python3

import csv
import html
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path


GALLERIES = [
    (
        "S1",
        "https://s3.us-east-1.amazonaws.com/theschoolof.ai/eagv3assignments/S1_Assignment_Gallery.html",
    ),
    (
        "S2",
        "https://s3.us-east-1.amazonaws.com/theschoolof.ai/eagv3assignments/S2_Assignment_Gallery.html",
    ),
]


PLATFORM_PRIORITY = {
    "YouTube": 60,
    "Loom": 50,
    "GitHub video": 40,
    "Google Drive": 35,
    "Direct demo": 30,
    "Animated demo": 25,
}


GENERIC_TITLE_PATTERNS = [
    r"^assignment(?:\s+\d+)?\b",
    r"assignment demo",
    r"^demo\b",
    r"\bdemo$",
    r"^screen recording\b",
    r"^session\s*\d+\b",
    r"^\d{4}\s+\d{2}\s+\d{2}",
    r"^\d{1,2}\s+[A-Za-z]+\s+\d{4}$",
    r"chrome extension video",
    r"video demo link",
    r"^first project$",
]


CARD_RE = re.compile(
    r"""<article\s+class="card">\s*
        <div\s+class="thumb(?:\s+placeholder)?"
        (?:\s+style="background-image:\s*url\('(?P<thumb>[^']*)'\);")?>
        </div>\s*
        <div\s+class="overlay"></div>\s*
        <div\s+class="content">\s*
        <div\s+class="title"><a\s+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a></div>\s*
        <div\s+class="meta">(?P<meta>.*?)</div>
        .*?
        </div>\s*
        </article>""",
    re.VERBOSE | re.DOTALL,
)


META_RE = re.compile(
    r"^(?P<author>.*?)\s+•\s+Score\s+(?P<score>\d+)\s+•\s+(?P<platform>.*?)\s+•\s+Student\s+(?P<student_id>\d+)$"
)


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8", errors="ignore")


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return " ".join(text.split())


def parse_gallery(session_name: str, source_url: str):
    html = fetch_text(source_url)
    rows = []

    for index, match in enumerate(CARD_RE.finditer(html), start=1):
        meta_raw = strip_html(match.group("meta"))
        meta_match = META_RE.match(meta_raw)
        if not meta_match:
            raise ValueError(f"Could not parse meta for {session_name} card {index}: {meta_raw}")

        rows.append(
            {
                "session": session_name,
                "source_url": source_url,
                "entry_index": index,
                "title": strip_html(match.group("title")),
                "author": meta_match.group("author"),
                "score": int(meta_match.group("score")),
                "platform": meta_match.group("platform"),
                "student_id": int(meta_match.group("student_id")),
                "video_url": match.group("url"),
                "thumbnail_url": match.group("thumb") or "",
            }
        )

    return rows


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_submission_rows(rows):
    grouped = {}

    for row in rows:
        key = (
            row["session"],
            row["student_id"],
            row["title"],
            row["video_url"],
        )
        if key not in grouped:
            grouped[key] = {
                "session": row["session"],
                "student_id": row["student_id"],
                "author": row["author"],
                "title": row["title"],
                "score": row["score"],
                "platform": row["platform"],
                "video_url": row["video_url"],
                "thumbnail_url": row["thumbnail_url"],
                "source_url": row["source_url"],
                "first_entry_index": row["entry_index"],
                "duplicate_count": 1,
            }
        else:
            grouped[key]["duplicate_count"] += 1

    return sorted(
        grouped.values(),
        key=lambda item: (item["student_id"], item["session"], item["first_entry_index"]),
    )


def build_student_rows(submission_rows):
    grouped = defaultdict(list)
    for row in submission_rows:
        grouped[row["student_id"]].append(row)

    student_rows = []
    for student_id, items in sorted(grouped.items(), key=lambda pair: pair[0]):
        author_variants = sorted({item["author"] for item in items})
        sessions_present = sorted({item["session"] for item in items})
        s1_items = [item for item in items if item["session"] == "S1"]
        s2_items = [item for item in items if item["session"] == "S2"]

        student_rows.append(
            {
                "student_id": student_id,
                "primary_author": author_variants[0],
                "author_variants": " || ".join(author_variants),
                "sessions_present": ",".join(sessions_present),
                "unique_submission_count": len(items),
                "s1_submission_count": len(s1_items),
                "s2_submission_count": len(s2_items),
                "s1_titles": " || ".join(item["title"] for item in s1_items),
                "s2_titles": " || ".join(item["title"] for item in s2_items),
                "s1_video_urls": " || ".join(item["video_url"] for item in s1_items),
                "s2_video_urls": " || ".join(item["video_url"] for item in s2_items),
                "score_values": ",".join(str(item["score"]) for item in items),
                "platform_values": ",".join(sorted({item["platform"] for item in items})),
            }
        )

    return student_rows


def is_generic_title(title: str) -> bool:
    lowered = title.lower().strip()
    for pattern in GENERIC_TITLE_PATTERNS:
        if re.search(pattern, lowered):
            return True
    if re.fullmatch(r"[\d\s:_-]+", lowered):
        return True
    return False


def title_quality_score(title: str) -> int:
    score = min(len(title.strip()), 80) // 4
    if is_generic_title(title):
        score -= 15
    if " - " in title or " | " in title or " — " in title:
        score += 2
    if re.search(r"[A-Za-z]{4,}", title):
        score += 2
    return score


def candidate_rank(row) -> tuple:
    platform_score = PLATFORM_PRIORITY.get(row["platform"], 20)
    title_score = title_quality_score(row["title"])
    duplicate_bonus = min(int(row["duplicate_count"]), 3)
    total = platform_score + title_score + duplicate_bonus
    return (total, platform_score, title_score, -int(row["first_entry_index"]))


def build_student_session_primary_rows(submission_rows):
    grouped = defaultdict(list)
    for row in submission_rows:
        grouped[(row["student_id"], row["session"])].append(row)

    analysis_rows = []
    for (student_id, session), items in sorted(grouped.items(), key=lambda pair: (int(pair[0][0]), pair[0][1])):
        ranked = sorted(items, key=candidate_rank, reverse=True)
        primary = ranked[0]

        selection_notes = []
        if primary["platform"] == "YouTube":
            selection_notes.append("preferred_youtube")
        else:
            selection_notes.append(f"preferred_platform_{primary['platform'].lower().replace(' ', '_')}")
        if not is_generic_title(primary["title"]):
            selection_notes.append("descriptive_title")
        else:
            selection_notes.append("generic_title_fallback")
        if len(items) > 1:
            selection_notes.append("chosen_from_multiple_candidates")

        analysis_rows.append(
            {
                "student_id": student_id,
                "session": session,
                "author": primary["author"],
                "score": primary["score"],
                "primary_title": primary["title"],
                "primary_platform": primary["platform"],
                "primary_video_url": primary["video_url"],
                "primary_thumbnail_url": primary["thumbnail_url"],
                "candidate_count": len(items),
                "all_titles": " || ".join(item["title"] for item in items),
                "all_video_urls": " || ".join(item["video_url"] for item in items),
                "all_platforms": " || ".join(item["platform"] for item in items),
                "selection_notes": ",".join(selection_notes),
            }
        )

    return analysis_rows


def build_progression_rows(analysis_rows):
    grouped = defaultdict(dict)
    for row in analysis_rows:
        grouped[row["student_id"]][row["session"]] = row

    progression_rows = []
    for student_id, sessions in sorted(grouped.items(), key=lambda pair: int(pair[0])):
        s1 = sessions.get("S1", {})
        s2 = sessions.get("S2", {})
        author = s1.get("author") or s2.get("author") or ""

        progression_rows.append(
            {
                "student_id": student_id,
                "author": author,
                "has_s1": "yes" if s1 else "no",
                "has_s2": "yes" if s2 else "no",
                "s1_score": s1.get("score", ""),
                "s2_score": s2.get("score", ""),
                "s1_primary_title": s1.get("primary_title", ""),
                "s2_primary_title": s2.get("primary_title", ""),
                "s1_primary_video_url": s1.get("primary_video_url", ""),
                "s2_primary_video_url": s2.get("primary_video_url", ""),
                "s1_candidate_count": s1.get("candidate_count", 0),
                "s2_candidate_count": s2.get("candidate_count", 0),
            }
        )

    return progression_rows


def main():
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = output_dir / "submission_gallery_index.csv"
    submission_output_path = output_dir / "submission_gallery_by_submission.csv"
    student_output_path = output_dir / "submission_gallery_by_student.csv"
    analysis_output_path = output_dir / "submission_gallery_analysis_units.csv"
    progression_output_path = output_dir / "submission_gallery_student_progression.csv"

    all_rows = []
    for session_name, source_url in GALLERIES:
        all_rows.extend(parse_gallery(session_name, source_url))

    raw_fieldnames = [
        "session",
        "source_url",
        "entry_index",
        "title",
        "author",
        "score",
        "platform",
        "student_id",
        "video_url",
        "thumbnail_url",
    ]
    write_csv(raw_output_path, raw_fieldnames, all_rows)

    submission_rows = build_submission_rows(all_rows)
    submission_fieldnames = [
        "session",
        "student_id",
        "author",
        "title",
        "score",
        "platform",
        "video_url",
        "thumbnail_url",
        "source_url",
        "first_entry_index",
        "duplicate_count",
    ]
    write_csv(submission_output_path, submission_fieldnames, submission_rows)

    student_rows = build_student_rows(submission_rows)
    student_fieldnames = [
        "student_id",
        "primary_author",
        "author_variants",
        "sessions_present",
        "unique_submission_count",
        "s1_submission_count",
        "s2_submission_count",
        "s1_titles",
        "s2_titles",
        "s1_video_urls",
        "s2_video_urls",
        "score_values",
        "platform_values",
    ]
    write_csv(student_output_path, student_fieldnames, student_rows)

    analysis_rows = build_student_session_primary_rows(submission_rows)
    analysis_fieldnames = [
        "student_id",
        "session",
        "author",
        "score",
        "primary_title",
        "primary_platform",
        "primary_video_url",
        "primary_thumbnail_url",
        "candidate_count",
        "all_titles",
        "all_video_urls",
        "all_platforms",
        "selection_notes",
    ]
    write_csv(analysis_output_path, analysis_fieldnames, analysis_rows)

    progression_rows = build_progression_rows(analysis_rows)
    progression_fieldnames = [
        "student_id",
        "author",
        "has_s1",
        "has_s2",
        "s1_score",
        "s2_score",
        "s1_primary_title",
        "s2_primary_title",
        "s1_primary_video_url",
        "s2_primary_video_url",
        "s1_candidate_count",
        "s2_candidate_count",
    ]
    write_csv(progression_output_path, progression_fieldnames, progression_rows)

    print(f"Wrote {len(all_rows)} raw rows to {raw_output_path}")
    print(f"Wrote {len(submission_rows)} grouped submission rows to {submission_output_path}")
    print(f"Wrote {len(student_rows)} grouped student rows to {student_output_path}")
    print(f"Wrote {len(analysis_rows)} analysis-unit rows to {analysis_output_path}")
    print(f"Wrote {len(progression_rows)} student progression rows to {progression_output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"Failed to build submission gallery CSV: {exc}", file=sys.stderr)
        raise
