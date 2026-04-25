# Submission Review Assistant

Submission Review Assistant is a full-stack review workspace for scoring project submissions with an evidence trail instead of a blind number.

The current build uses:

- React frontend
- FastAPI backend
- handwritten agent orchestration
- Gemini Flash 3.1 as the intended model path for video and artifact review

## Current status

This repo already includes:

- project brief and evaluation plan
- historical gallery datasets
- leak-safe train/test splits
- FastAPI endpoints backed by the dataset
- a React review cockpit UI
- a live Gemini-backed review runner with a safe fallback when Gemini is not configured
- an evaluation lab view for persisted baseline/agent runs and saved comparisons

## Project structure

```text
backend/
  app/
    gemini_client.py
    main.py
    data.py
    mock_review.py
    review_runner.py
    rubric.py
    schemas.py
  requirements.txt

frontend/
  src/
    App.tsx
    index.css
    lib/api.ts
    types/api.ts

data/
  submission_gallery_index.csv
  submission_gallery_by_submission.csv
  submission_gallery_by_student.csv
  submission_gallery_analysis_units.csv
  submission_gallery_student_progression.csv
  submission_gallery_analysis_units_train.csv
  submission_gallery_analysis_units_test.csv
  submission_gallery_split_manifest.csv

scripts/
  build_submission_gallery_csv.py
  build_train_test_splits.py
  run_eval.py
  compare_eval_runs.py
  optimize_prompts_gepa.py

schemas/
  review_request.schema.json
  review_result.schema.json

prompts/
  seed_prompt_templates.json
```

## Backend run

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Backend default:

- `http://localhost:8000`

Useful endpoints:

- `GET /api/health`
- `GET /api/datasets/summary`
- `GET /api/submissions?split=test`
- `GET /api/submissions/{student_id}/{session}`
- `GET /api/submissions/{student_id}/{session}/review-preview?mode=agent`

## Gemini configuration

The backend auto-loads local env files in this order when they exist:

1. `.env`
2. `.env.local`
3. `backend/.env`
4. `backend/.env.local`

Shell environment variables still take priority over file values.

The backend reads these environment variables:

```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3-flash-preview
```

Optional:

```bash
GEMINI_API_BASE=https://generativelanguage.googleapis.com/v1beta/models
```

Recommended local setup:

```bash
cp .env.example .env.local
```

or:

```bash
cp backend/.env.example backend/.env.local
```

Then edit the file with your real values.

If `GEMINI_API_KEY` is missing, the backend returns a tagged fallback dossier
(`source: "fallback"`, `confidence: "low"`, `needs_human_review: true`) that
uses the historical score band's midpoint as a placeholder rather than reading
the ground-truth score. This is clearly labelled in every eval run so fallback
rows cannot be confused with real Gemini runs in metrics or comparisons.

Current live review steps:

- plan review
- inspect primary video URL
- inspect repo or search for a likely public code artifact
- inspect alternate artifacts when useful
- retrieve similar scored examples
- synthesize a final dossier

## Frontend run

From the repo root:

```bash
cd frontend
npm install
npm run dev
```

Frontend default:

- `http://localhost:5173`

Current frontend areas:

- dataset slicer
- submission rail
- dossier panel
- review preview
- agent trace
- claim ledger
- evaluation lab
- run comparison panel
- metric bars and confidence breakdowns for saved eval runs

Optional env:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Frontend local env file:

```text
frontend/.env.local
```

Start from:

```bash
cp frontend/.env.local.example frontend/.env.local
```

Then edit:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Dataset refresh

Rebuild the historical gallery dataset:

```bash
python3 scripts/build_submission_gallery_csv.py
python3 scripts/build_train_test_splits.py
```

## Evaluation runs

Run baseline on the test set:

```bash
python3 scripts/run_eval.py --mode baseline --split test
```

Run the agent on the test set:

```bash
python3 scripts/run_eval.py --mode agent --split test
```

By default `run_eval.py` refuses to run without `GEMINI_API_KEY` set, so
fallback-only predictions cannot silently pollute reported metrics. Pass
`--allow-fallback` if you explicitly want a fallback baseline (rows are
clearly tagged `source=fallback` in the output).

Parallelize Gemini calls with `--concurrency N` — respect your key's rate
limits.

Outputs are written under:

```text
eval/
  baseline/
  agent/
```

Each run stores:

- one JSON result per submission
- `summary.csv`
- `metrics.json`
- `run_config.json`

Compare two eval runs:

```bash
python3 scripts/compare_eval_runs.py \
  --run-a eval/baseline/smoke-baseline \
  --run-b eval/agent/smoke-agent \
  --label-a baseline \
  --label-b agent
```

This writes a comparison JSON under:

```text
eval/compare/
```

## GEPA prompt optimization

Install GEPA:

```bash
pip install -r requirements-opt.txt
```

Set the required environment:

```bash
export GEMINI_API_KEY=your_key_here
export GEPA_REFLECTION_LM=your_reflection_model_string
```

Then run:

```bash
python3 scripts/optimize_prompts_gepa.py --max-metric-calls 40
```

This script:

- uses the train split only
- carves out an internal validation slice from train
- treats the prompt template set as the optimization artifact
- writes optimized prompt templates under `eval/gepa/<run_name>/`

Seed prompts live in:

```text
prompts/seed_prompt_templates.json
```

## Tests

Install dev dependencies and run pytest:

```bash
pip install -r requirements-dev.txt
pytest
```

Current suite covers:

- fallback never reads `submission.score` (GT leak regression test)
- `ReviewPreview` output matches `schemas/review_result.schema.json`
- Gemini JSON parser handles fenced blocks and rejects malformed JSON
- repo URL extractor supports GitHub, GitLab, Bitbucket, HuggingFace, and Colab
- retrieval similarity does not rank on `target.score`

## Near-term next steps

1. Surface persisted eval runs and comparison outputs in the frontend.
2. Run GEPA over the train split and compare optimized prompts against the seed prompts on the untouched test set.
3. Add stronger repo-specific inspection when a direct repository URL is available.
4. Replace more placeholder logic in the frontend with true run history and evaluation charts.

## Project rules

- No LangGraph
- No CrewAI
- No agent orchestration framework
- Keep the loop explicit and handwritten
- Keep score outputs downstream of evidence
