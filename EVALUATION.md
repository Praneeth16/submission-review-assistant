# Evaluation runner spec

## Goal

We need one clean evaluation loop for two systems:

1. `baseline`
2. `agent`

Both systems should read the same leak-safe test set and return the same output schema so we can compare them directly.

The point is not just "which one predicts the score better." The point is:

- which one is closer on score
- which one handles uncertainty better
- which one gives a more usable evidence trail
- which one hallucinates less

## Source datasets

Use these files:

- train: `data/submission_gallery_analysis_units_train.csv`
- test: `data/submission_gallery_analysis_units_test.csv`
- split audit: `data/submission_gallery_split_manifest.csv`

Do not build evaluation prompts from the raw crawl unless there is a specific debugging reason.

The stable unit for evaluation is one row from:

- `submission_gallery_analysis_units_train.csv`
- `submission_gallery_analysis_units_test.csv`

That means one row per `student_id + session`.

## Exact model input row

The runner should read one row at a time from the analysis-unit file and convert it into a structured request object.

### Required fields from the CSV

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
- `row_score_band`

### Model request object

This is the object we should send into the model pipeline after parsing the CSV row:

```json
{
  "student_id": "199",
  "session": "S1",
  "author": "barun acharya",
  "primary_submission": {
    "title": "Personal Spends Tracker on Your Voice Tips",
    "platform": "YouTube",
    "video_url": "https://youtu.be/s6y88pjANvk",
    "thumbnail_url": "https://i.ytimg.com/vi/..."
  },
  "alternate_submissions": {
    "candidate_count": 2,
    "all_titles": [
      "barun acharya assignment demo",
      "Personal Spends Tracker on Your Voice Tips"
    ],
    "all_video_urls": [
      "https://raw.githubusercontent.com/.../demo.mp4",
      "https://youtu.be/s6y88pjANvk"
    ],
    "all_platforms": [
      "Direct demo",
      "YouTube"
    ],
    "selection_notes": [
      "preferred_youtube",
      "descriptive_title",
      "chosen_from_multiple_candidates"
    ]
  },
  "rubric_version": "v1",
  "ground_truth": {
    "score": 700,
    "score_band": "early_below_750"
  }
}
```

Important:

- `ground_truth` is for the runner, not for the model prompt.
- The model should never see the true score.

## Evaluation modes

### Mode 1: baseline

The baseline is intentionally simple.

What it gets:

- parsed row metadata
- primary title
- primary video URL
- alternate submission metadata
- rubric

What it does not get:

- multi-step evidence collection
- repo verification
- retrieval of similar scored examples
- explicit tool planning

Baseline prompt shape:

1. "Here is the submission metadata."
2. "Here is the rubric."
3. "Review this submission and return the output schema."

This is the one-shot scorer.

### Mode 2: agent

The agent mode uses the same starting row but is allowed to:

1. plan evidence gaps
2. inspect the video URL with Gemini Flash 3.1
3. inspect linked repo or external artifacts if available
4. retrieve similar historical examples from the train set
5. update confidence after each step
6. abstain when evidence is weak

The evaluation runner should record:

- each step
- tool name
- tool input
- tool result summary
- updated belief state

## Shared output contract

Both systems must return the same top-level JSON shape.

Use:

- `schemas/review_result.schema.json`

The important outputs are:

- `predicted_score`
- `predicted_score_band`
- `confidence`
- `needs_human_review`
- `summary`
- `criterion_evidence`
- `claim_verification`
- `trace`

## Required rubric for evaluation

Use one rubric for both systems so the comparison is fair.

Suggested rubric:

1. Problem clarity
2. Agentic behavior
3. Genuine tool use
4. Implementation depth
5. Demo quality
6. Originality
7. Completeness and polish

Each criterion must include:

- short finding
- evidence source
- confidence
- provisional score band

## Metrics

Use these metrics first. They are simple and hard to argue with.

### 1. Exact score accuracy

How often `predicted_score == ground_truth_score`.

### 2. Within-250 accuracy

How often:

`abs(predicted_score - ground_truth_score) <= 250`

This is a practical metric because the score buckets are coarse.

### 3. Mean absolute error

Average:

`abs(predicted_score - ground_truth_score)`

### 4. Score-band accuracy

Compare:

- predicted score band
- true score band

Bands:

- `early_below_750`
- `mid_750_999`
- `strong_1000_1499`
- `elite_1500_plus`

### 5. Confidence coverage

Measure:

- how many rows are marked high / medium / low confidence
- how many rows are marked `needs_human_review`

This matters because the agent should be allowed to be cautious.

### 6. Confidence-conditioned error

Compare MAE for:

- high-confidence rows
- medium-confidence rows
- low-confidence rows

If confidence is meaningful, low-confidence rows should have worse error than high-confidence rows.

### 7. Hallucination audit on a manual sample

Take a small manually reviewed sample from the test set.

For each reviewed row, judge:

- did the system claim evidence that was not actually observed?
- did it overstate implementation support?
- did it smooth over contradictions?

This should be a small human audit, not an automated metric.

## Primary comparison question

The most important question is:

"Does the agent improve score usefulness and evidence quality enough to justify the extra complexity?"

That breaks down into:

1. lower or comparable MAE
2. better score-band accuracy
3. cleaner abstention behavior
4. fewer unsupported evidence claims
5. more useful reviewer-facing outputs

## Runner outputs

For each mode, the runner should write:

- one JSON result per evaluated row
- one aggregate metrics file
- one CSV summary table

Suggested folder layout:

```text
eval/
  baseline/
    runs/
    metrics.json
    summary.csv
  agent/
    runs/
    metrics.json
    summary.csv
```

The repo now includes:

- `scripts/run_eval.py` for persisted baseline and agent runs
- `scripts/compare_eval_runs.py` for run-vs-run comparison
- `scripts/optimize_prompts_gepa.py` for GEPA prompt optimization on the train split
- `prompts/seed_prompt_templates.json` as the seed artifact for optimization

Each per-row run should include:

- input row ID
- mode
- model name
- raw result JSON
- runtime
- error if any

## Evaluation protocol

### Step 1

Run the baseline on the full test set.

### Step 2

Run the agent on the same test set.

### Step 3

Compute the shared metrics.

### Step 4

Manually inspect:

- 5 best baseline wins
- 5 best agent wins
- 5 rows where both fail badly

### Step 5

Write a short evaluation memo:

- what improved
- what did not
- where the agent still cheats or hallucinates
- whether the extra tool loop is worth it

## Failure handling

The runner should never silently drop rows.

If a row fails:

- write an error record
- keep the row in the summary
- count it in failure statistics

If the model cannot justify a score:

- return `needs_human_review: true`
- set low confidence
- still produce the rest of the schema where possible

## Train-set usage rules

Train set is allowed for:

- retrieval of similar scored examples
- tuning prompt wording
- calibrating score bands
- few-shot examples

Train set is not allowed for:

- leaking the same student into test
- copying exact historical labels into the prompt as if they were facts
- choosing examples from the test set by mistake

## What counts as success

This evaluation is successful if it tells us one of these two things clearly:

1. The agent is better enough to justify its complexity.
2. The one-shot baseline is already strong enough that the agent needs a sharper value proposition.

Either answer is useful. The goal is not to "prove the agent wins" at all costs.
