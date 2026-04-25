# Dataset notes

## Raw gallery index

This folder contains the raw historical gallery index used by `Submission Review Assistant`.

Current file:

- `submission_gallery_index.csv`
- `submission_gallery_by_submission.csv`
- `submission_gallery_by_student.csv`
- `submission_gallery_analysis_units.csv`
- `submission_gallery_student_progression.csv`
- `submission_gallery_analysis_units_train.csv`
- `submission_gallery_analysis_units_test.csv`
- `submission_gallery_split_manifest.csv`

## Where it comes from

The CSV is generated from these public gallery pages:

- `S1`: `https://s3.us-east-1.amazonaws.com/theschoolof.ai/eagv3assignments/S1_Assignment_Gallery.html`
- `S2`: `https://s3.us-east-1.amazonaws.com/theschoolof.ai/eagv3assignments/S2_Assignment_Gallery.html`

Use the generator script:

- `../scripts/build_submission_gallery_csv.py`

## Why we keep a raw file

This file is not meant to be perfect. It is meant to preserve the gallery as published.

That means:

- duplicate cards stay in the file
- repeated student IDs stay in the file
- mixed platforms stay in the file
- odd titles and placeholder entries stay in the file

If we need cleaned analysis tables later, we should generate derived files instead of editing this one by hand.

## Derived files

### `submission_gallery_by_submission.csv`

One row per submission artifact. This is the best starting point for evaluation runs where we want to inspect a single gallery card or video link at a time.

Useful for:

- picking individual submissions to review
- comparing scoring outputs artifact by artifact
- tracking platforms and video URLs cleanly

### `submission_gallery_by_student.csv`

One row per `student_id`, with Session 1 and Session 2 submissions grouped together.

Useful for:

- cross-session comparisons
- spotting repeat builders
- building later features that reason over student progression from S1 to S2
- grouping all artifacts belonging to the same student before running analysis

### `submission_gallery_analysis_units.csv`

One row per `student_id + session`, with a selected primary submission plus all candidate submissions preserved in the row.

This is the best file for:

- evaluation runs that need one stable analysis unit per student per session
- prompting Gemini Flash 3.1 with a single chosen primary URL
- preserving alternates without losing the context of multiple submissions

Primary-selection heuristic:

- prefer YouTube when available
- otherwise prefer the highest-priority public platform
- prefer descriptive titles over generic titles like `assignment demo`, `screen recording`, timestamps, or `first project`
- keep all alternative titles and URLs in the row for traceability

### `submission_gallery_student_progression.csv`

One row per student with the primary Session 1 and primary Session 2 submissions side by side.

This is the best file for:

- cross-session progression analysis
- comparing S1 and S2 scores quickly
- building later features around student growth or consistency

### `submission_gallery_analysis_units_train.csv`

Training split built from `submission_gallery_analysis_units.csv`.

Rules:

- split at the `student_id` level, not at the row level
- the same student never appears in both train and test
- split is stratified by each student's mean score band

### `submission_gallery_analysis_units_test.csv`

Test split built with the same leak-prevention rule.

Use this for:

- final evaluation runs
- comparing baseline vs agent
- prompt and scoring experiments without contaminating the train set

### `submission_gallery_split_manifest.csv`

Student-level manifest showing which split each student belongs to and why.

Useful for:

- auditing leakage
- checking split balance
- debugging train/test selection

## Raw file columns

- `session`
- `source_url`
- `entry_index`
- `title`
- `author`
- `score`
- `platform`
- `student_id`
- `video_url`
- `thumbnail_url`

## By-submission columns

- `session`
- `student_id`
- `author`
- `title`
- `score`
- `platform`
- `video_url`
- `thumbnail_url`
- `source_url`
- `first_entry_index`
- `duplicate_count`

## By-student columns

- `student_id`
- `primary_author`
- `author_variants`
- `sessions_present`
- `unique_submission_count`
- `s1_submission_count`
- `s2_submission_count`
- `s1_titles`
- `s2_titles`
- `s1_video_urls`
- `s2_video_urls`
- `score_values`
- `platform_values`

## Analysis-unit columns

- `student_id`
- `session`
- `author`
- `score`
- `primary_title`
- `primary_platform`
- `primary_video_url`
- `primary_thumbnail_url`
- `candidate_count`
- `all_titles`
- `all_video_urls`
- `all_platforms`
- `selection_notes`

## Student-progression columns

- `student_id`
- `author`
- `has_s1`
- `has_s2`
- `s1_score`
- `s2_score`
- `s1_primary_title`
- `s2_primary_title`
- `s1_primary_video_url`
- `s2_primary_video_url`
- `s1_candidate_count`
- `s2_candidate_count`

## Train/test split columns

The train and test analysis files keep the analysis-unit columns and add:

- `split`
- `row_score_band`

## Split manifest columns

- `student_id`
- `split`
- `student_mean_score`
- `student_mean_band`
- `unit_count`
- `sessions_present`

## Expected use

This dataset supports:

- retrieval of similar past submissions
- score-band calibration
- duplicate and student-level grouping
- building baseline evaluation sets
- selecting examples for demo and testing
- cross-session grouping by `student_id`
- one-row-per-student-session evaluation
- side-by-side S1 to S2 progression analysis
- leak-safe train/test experiments
- score-band-balanced evaluation runs

## Current split summary

Built with:

- script: `../scripts/build_train_test_splits.py`
- test ratio: `0.2`
- seed: `42`

Current counts:

- train rows: `323`
- test rows: `83`
- train students: `186`
- test students: `48`
