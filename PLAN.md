# Submission Review Assistant

## One-line pitch

A browser agent that reviews project submissions the way a human judge does: it opens the gallery entry, inspects the demo video, checks the repo, verifies the big claims, and then produces a provisional score with confidence and an evidence trail.

## Current status

This is no longer just a concept brief. The project now has a working full-stack shell, a live Gemini-backed review path, persisted evaluation runs, and a local env-based setup.

What is already built:

- a React frontend for instructors
- a FastAPI backend
- a handwritten multi-step review runner
- raw and cleaned historical datasets
- leak-safe train/test splits
- persisted baseline and agent evaluation runs
- comparison artifacts for eval runs
- a GEPA optimization script for prompt-template tuning
- local `.env` loading for backend and scripts

## What has been implemented

### Full-stack app

- `frontend/` React app
- `backend/` FastAPI app
- frontend talks to the backend over a simple JSON API

### Instructor-facing product UI

The UI has been reshaped away from a generic dashboard and toward a scoring workflow.

Current product surfaces:

- review inbox
- scoring sheet
- evidence notebook
- evaluation lab
- run comparison view

The main scoring surface now puts the actual predicted score first, followed by the written explanation and supporting evidence.

### Backend review runner

The live review path now does:

1. plan the review
2. inspect the primary demo/video URL with Gemini
3. inspect repo/code artifacts, or search for likely public repo evidence
4. inspect alternate artifacts when useful
5. retrieve similar scored historical examples
6. synthesize the final dossier

If Gemini is not configured or a call fails, the backend falls back to a safe dataset-backed mock preview instead of crashing.

### Dataset and evaluation pipeline

Generated datasets now include:

- `data/submission_gallery_index.csv`
- `data/submission_gallery_by_submission.csv`
- `data/submission_gallery_by_student.csv`
- `data/submission_gallery_analysis_units.csv`
- `data/submission_gallery_student_progression.csv`
- `data/submission_gallery_analysis_units_train.csv`
- `data/submission_gallery_analysis_units_test.csv`
- `data/submission_gallery_split_manifest.csv`

These support:

- raw preservation
- grouped submission analysis
- grouped student analysis across Session 1 and Session 2
- one stable unit per `student_id + session`
- leak-safe train/test evaluation

### Persisted evaluation runs

The repo can now write evaluation results to disk:

- baseline runs under `eval/baseline/`
- agent runs under `eval/agent/`
- run comparisons under `eval/compare/`
- GEPA optimization outputs under `eval/gepa/`

### Prompt optimization setup

Prompt templates have been externalized into:

- `prompts/seed_prompt_templates.json`

The GEPA hook is implemented through:

- `scripts/optimize_prompts_gepa.py`

This treats the prompt-template set as the optimization artifact and uses the train split only, with an internal validation carve-out from train.

### Local configuration

Local env file support is implemented for backend and scripts.

Supported files:

1. `.env`
2. `.env.local`
3. `backend/.env`
4. `backend/.env.local`

The frontend uses:

- `frontend/.env.local`

## Why this is worth building

Most "AI grader" ideas collapse into a rubric prompt plus a number. This one has a better center of gravity.

The product is not "guess the instructor's score." The product is "collect the evidence a reviewer would otherwise have to gather by hand." Scoring is the last step, not the whole story.

That makes it:

- more agentic
- more defensible
- easier to demo
- more useful outside the class

The broader wedge is hackathon judging, demo-day review, portfolio triage, and take-home project review.

## Hard constraints

These are project rules, not suggestions.

1. No LangGraph.
2. No CrewAI.
3. No agent/tool-calling framework.
4. Build the orchestration loop ourselves with plain application code.
5. Use Gemini Flash 3.1 as the core model.
6. Lean on Gemini Flash 3.1 for:
   - YouTube URL understanding
   - web page / URL reading
   - web-grounded lookups when a linked artifact needs more context

The point of the project is to show that we understand agent loops, not that we can wire together a framework.

## What makes this genuinely agentic

This only works if the system behaves like a small review investigator.

Core loop:

1. Read the submission page.
2. Decide what evidence is missing for each rubric item.
3. Open the demo video and pull concrete claims.
4. Open the repo and look for matching implementation evidence.
5. Follow external links if the project points to a live demo or docs.
6. Mark each criterion as supported, weakly supported, unsupported, or unclear.
7. Produce a provisional score only when enough evidence exists.
8. Abstain or flag for human review when confidence is low.

If this turns into "stuff everything into one prompt and score it," we should kill the idea.

## Technical stance

The architecture should stay simple and inspectable.

### Agent orchestration

Build a handwritten orchestrator with a loop like this:

1. State object
2. Next-step planner
3. Tool dispatcher
4. Observation parser
5. Score / confidence updater
6. Stop or continue

In practice this means:

- plain TypeScript or JavaScript
- explicit tool functions
- explicit message history
- explicit state transitions
- no hidden framework magic

### Model strategy

Use Gemini Flash 3.1 as the one primary reasoning model for the MVP.

Use it for:

- submission-page interpretation
- YouTube URL analysis
- transcript or timestamp extraction when available
- repo evidence synthesis
- claim verification
- dossier generation

Use structured JSON outputs wherever possible so the trace is easy to render in the UI.

## Product framing

Use this wording everywhere:

- "submission review assistant"
- "evidence-backed judging assistant"
- "project review dossier"
- "provisional score with confidence"

Avoid this wording:

- "automatic grader"
- "replacement for instructors"
- "learns the instructor's mind"
- "predicts the true score"

## Target users

Primary:

- course instructors
- teaching assistants
- hackathon judges
- internal showcase reviewers

Secondary:

- students who want a pre-submission review before the final judge sees it

## Core user story

"I have too many submissions and not enough time. Open one project, gather the evidence across the gallery page, demo video, and repo, show me whether the main claims are real, then give me a provisional score and tell me what still needs a human look."

## MVP scope

Keep the first version tight.

Supported inputs:

- one gallery entry page
- one linked demo video
- one linked GitHub repo or code folder
- optional external demo/docs link

Supported output:

- criterion-by-criterion evidence table
- major claims pulled from the demo
- claim vs evidence verification notes
- provisional score
- confidence score
- "needs human review" flag

Do not build in V1:

- arbitrary code execution from untrusted repos
- full LMS integration
- model fine-tuning
- automated final grading
- support for every possible assignment type
- multi-model routing
- external agent frameworks

## Assignment-aware scoring notes

The scoring prompt should reflect the actual framing of the earlier assignments:

### Session 1

- uniqueness matters
- usefulness matters
- practical effort matters
- README and demo video matter a lot
- "No video == no score"
- scores are subjective

### Session 2

- Gemini integration matters
- the app should clearly use the LLM
- public sharing can add bonus points

### Important scoring nuance

The scorer should not assume a hard ceiling like a strict rubric grader. The instructor may score above the nominal expectation when a project is unusually exciting or impressive. The prompt should explicitly allow that.

## Dataset plan

We already have a raw gallery dataset for calibration and evaluation.

### Source galleries

- `S1`: `https://s3.us-east-1.amazonaws.com/theschoolof.ai/eagv3assignments/S1_Assignment_Gallery.html`
- `S2`: `https://s3.us-east-1.amazonaws.com/theschoolof.ai/eagv3assignments/S2_Assignment_Gallery.html`

### Generated artifact

- `data/submission_gallery_index.csv`
- `data/submission_gallery_by_submission.csv`
- `data/submission_gallery_by_student.csv`
- `data/submission_gallery_analysis_units.csv`
- `data/submission_gallery_student_progression.csv`
- `data/submission_gallery_analysis_units_train.csv`
- `data/submission_gallery_analysis_units_test.csv`
- `data/submission_gallery_split_manifest.csv`

### Generator

- `scripts/build_submission_gallery_csv.py`

### Current schema

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

### Why this matters

These files give us:

- historical score anchors
- student IDs for grouping repeated entries
- raw video URLs for Gemini Flash 3.1 video review
- a practical dataset for baseline vs agent comparison
- a clean student-level view across Session 1 and Session 2
- a clean submission-level view for per-artifact evaluation

They also let us bring in assignment-specific context by session so the scorer does not judge Session 1 and Session 2 by the same expectations.

### Important note

`submission_gallery_index.csv` is the raw index, not a cleaned benchmark. The galleries contain duplicates and mixed platforms like YouTube, Loom, GitHub video, and direct demo links.

Use:

- `submission_gallery_index.csv` for raw preservation
- `submission_gallery_by_submission.csv` for one row per submission artifact
- `submission_gallery_by_student.csv` for one row per student across S1 and S2
- `submission_gallery_analysis_units.csv` for one row per student per session with a chosen primary submission
- `submission_gallery_student_progression.csv` for side-by-side S1 vs S2 analysis
- `submission_gallery_analysis_units_train.csv` for training runs
- `submission_gallery_analysis_units_test.csv` for evaluation runs
- `submission_gallery_split_manifest.csv` for auditing leakage and balance

Keep the raw file intact. If we need more cleaned versions later, generate derived files instead of hand-editing it.

## Evaluation rubric for V1

Use a small rubric that fits the assignment and can be scored from public artifacts.

Suggested rubric:

1. Problem clarity
2. Agentic behavior
3. Genuine tool use
4. Implementation depth
5. Demo quality
6. Originality
7. Completeness and polish

For each criterion, the agent should output:

- evidence found
- confidence
- provisional score band
- what is still missing

This rubric is intentionally broad, but the prompt should also condition on the actual assignment text for each session so the final score is not detached from what the instructor asked for.

## Tool plan

These are the core custom tools the system should expose in the UI.

### 1. `read_submission_page`

Purpose:
Extract title, description, score if present, demo links, repo links, and any visible claims from the gallery entry.

Returns:

- structured submission metadata
- candidate artifacts to inspect next

### 2. `inspect_demo_video`

Purpose:
Open the demo video URL, send the URL to Gemini Flash 3.1, pull transcript chunks or timestamped observations when possible, and summarize what the presenter says the system can do.

Returns:

- transcript evidence
- claimed features
- timestamps worth citing

### 3. `inspect_repo`

Purpose:
Inspect repo structure, README, manifest/config files, and code files that likely support the claimed features.

Returns:

- project structure
- detected stack
- implementation evidence
- gaps between demo claims and code

### 4. `verify_claims_against_code`

Purpose:
Take the claims found in the video or description and try to confirm whether the repo supports them.

Returns:

- verified claims
- weak claims
- unsupported claims
- unclear claims

### 5. `inspect_external_artifacts`

Purpose:
Open live demo links, docs, or slides when present and use them as extra evidence. When a page needs contextual lookup, allow Gemini Flash 3.1 to reason over the URL or grounded page content.

Returns:

- working / broken link status
- supporting evidence
- contradictions

### 6. `retrieve_similar_scored_examples`

Purpose:
Pull a few historically scored submissions that look similar so the reviewer can anchor the provisional score.

Returns:

- nearest examples
- score range
- useful comparison notes

### 7. `generate_review_dossier`

Purpose:
Assemble the final review output in a format a human judge can trust.

Returns:

- score
- confidence
- criterion table
- strengths
- risks
- open questions

### What is currently live

The backend currently has working equivalents of:

- `plan_review`
- `inspect_demo_video`
- `inspect_repo`
- `inspect_external_artifacts`
- `retrieve_similar_scored_examples`
- `generate_review_dossier`

The repo verification step is real, but still lightweight. It looks for direct GitHub evidence first and then uses grounded search as fallback.

## Agent workflow

### Step 1: intake

- read the gallery entry
- identify available artifacts
- generate an evidence plan for the rubric

### Step 2: claim extraction

- inspect the demo video
- pull the big product claims
- map claims to rubric criteria

### Step 3: repo verification

- inspect repo structure and key files
- verify whether each claim has code support
- note missing or inconsistent evidence

### Step 4: external artifact check

- inspect any live demo or docs link
- use this only to support or challenge existing evidence

### Step 5: calibration

- retrieve a small set of scored examples
- use them as anchors, not as truth

### Step 6: scoring and abstention

- produce a provisional score only when evidence is enough
- lower confidence if artifacts conflict
- flag "needs human review" when the agent is guessing

This workflow is already implemented in a first version in the backend review runner.

## Data pipeline

### Phase 0: build the raw index

- scrape both gallery HTML pages
- store score, student ID, video URL, and metadata in CSV
- keep the raw index in version control

### Phase 0.5: derive a working analysis set

- group by `student_id`
- keep duplicate entries visible
- optionally derive one file per session and one combined file
- add cleaned fields later without touching the raw file

### Phase 0.75: create stable analysis units

- build one row per `student_id + session`
- select a primary submission with explicit heuristics
- preserve alternate submissions in the same row
- build a student-progression file for S1 vs S2 analysis

### Phase 0.9: build leak-safe train/test splits

- split by `student_id`, not by row
- keep the same student out of both train and test
- stratify by student mean score band
- generate a manifest so the split can be audited later

## UI plan

The UI should feel like a product an instructor would actually use, not a data dashboard.

### Current layout

#### Left: review inbox

- dataset split
- session filter
- scoring path toggle
- search
- submission list

#### Center: scoring sheet

- actual predicted score
- confidence
- instructor-style explanation
- criterion evidence

#### Right: evidence notebook

- context and progression
- alternate artifacts
- claim support
- open questions
- trace of why the system moved

#### Bottom: evaluation lab

- saved baseline runs
- saved agent runs
- metrics and confidence breakdowns
- run comparisons and deltas

## Data and scoring strategy

Historical scores are useful, but only in a narrow way.

Use them for:

- calibration anchors
- score band sanity checks
- side-by-side comparisons

Do not use them for:

- "learning the instructor's mind"
- claiming fairness
- claiming objective correctness

The safest scoring story is:

"The agent uses past examples as rough anchors, then scores only from the evidence it gathers on this submission."

We should also say:

"The historical CSV is there to help us evaluate and calibrate the workflow, not to train a grading model that imitates the instructor."

## Baseline vs agentic system

This project needs a clear baseline or the agent loop will look ornamental.

### Baseline

- one-shot multimodal review
- submission text + video summary + repo summary
- direct score output

### Agentic system

- criterion-level evidence plan
- targeted tool calls
- claim extraction
- claim verification
- confidence-aware scoring
- abstention when evidence is weak

The story we want to show:

"The agentic version is slower, but it gives a better dossier, fewer hallucinated claims, and cleaner uncertainty handling."

That baseline-vs-agent workflow is now implemented in scripts and persisted under `eval/`.

## Success criteria

The project wins if it shows these clearly:

1. It gathers evidence across multiple artifacts.
2. Tool results change the next step.
3. The final score is tied to evidence, not vibes.
4. It can say "I don't know" when evidence is weak.
5. A human reviewer would save time using it.

## Main risks

### Risk 1: it becomes a fancy rubric wrapper

Mitigation:
Make claim verification the center of the product.

### Risk 2: it overfits to historical scores

Mitigation:
Use past scores as anchors only. Keep the final judgment evidence-first.

### Risk 3: video and repo disagree

Mitigation:
Treat disagreement as a feature. Surface it in the dossier and reduce confidence.

### Risk 4: the demo feels too academic

Mitigation:
Frame it as a hackathon/demo judging copilot, not just a class grader.

### Risk 5: the model sounds overconfident

Mitigation:
Always show confidence and "needs human review."

## First risky assumption to test

Before building the full product, run this kill test:

"Does gallery + video + repo + claim verification produce meaningfully better judgments than a one-shot scoring prompt?"

If the answer is no, pivot away from scoring and keep only the review dossier.

## Build plan

### Completed

#### Phase 0: data foundation

- scrape both gallery pages
- build raw and derived CSV files
- build grouped student and submission views
- build stable analysis units
- build leak-safe train/test splits

#### Phase 1: baseline and agent loop

- implement baseline and agent review modes
- externalize prompts into a seed artifact
- implement persisted eval runs
- implement run comparison output

#### Phase 2: product UI

- build a full-stack shell
- build an instructor-facing scoring workspace
- build an evaluation lab view
- add dark and light theme support

#### Phase 3: Gemini integration

- wire backend Gemini client
- confirm real Gemini calls work from local `.env`
- run live review previews through the multi-step runner

### Current next steps

1. Fold the actual Session 1 and Session 2 assignment texts directly into the review prompts so scoring aligns better with the instructor’s stated expectations.
2. Make the score output more instructor-like by refining when the system should be cautious versus excited, including the "can go above the nominal limit" nuance.
3. Strengthen repo inspection for direct GitHub repositories beyond URL- and search-level evidence.
4. Run larger persisted evals on the full test set with Gemini enabled.
5. Set `GEPA_REFLECTION_LM` and run the first real GEPA prompt-optimization loop.
6. Compare seed prompts vs optimized prompts on the untouched test set.
7. Surface saved eval and GEPA artifacts more richly in the frontend.

## Demo script

### Demo 1: straightforward strong submission

- open a high-quality submission
- show the agent read the page
- show the agent inspect the video
- show the agent verify claims in the repo
- finish with a confident dossier

### Demo 2: polished demo, weak code support

- show the agent pull strong claims from the video
- show the repo inspection fail to back up part of the story
- finish with reduced confidence and a lower score

### Demo 3: incomplete evidence

- broken repo link or thin code
- show the agent mark criteria as unclear
- finish with "needs human review"

### Demo 4: evaluation proof

- show saved baseline and agent runs
- show comparison deltas
- show that the review system is being measured, not just presented

### Demo 5: optimization proof

- show the seed prompt artifact
- show GEPA output after optimization
- compare before vs after on held-out test examples

## Submission strategy

The final YouTube video should sell three things:

1. This is a real browser agent, not a one-shot grader.
2. The system is useful even when the score is uncertain.
3. The agent is honest about missing evidence.

That combination is what makes it feel mature.

It should also make one implementation point obvious:

"We built the agent loop ourselves. No LangGraph, no CrewAI, no orchestration library."

It should also make one product point obvious:

"This is not just an AI grader. It is a scoring workspace with evidence, explanation, and evaluation."
