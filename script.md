# Submission Review Assistant — 5-min YouTube tutorial

**Title:** *S3 build: an evidence-first review agent (no LangGraph, no CrewAI)*
**Length:** 5:00 hard cap
**Format:** screen capture + voice-over, no talking head
**Pre-flight:** backend running with `GEMINI_API_KEY`, frontend at `localhost:5173`, dark theme, one ad-hoc demo URL ready.

---

### 0:00 — Hook *(stand on home screen, dossier visible)*

> Five-minute tour of my Session 3 build — Submission Review Assistant. It scores project submissions by collecting evidence first, scoring last, and refusing when the evidence is too thin to defend. Demo first. Then I'll show you exactly how it works.

---

## DEMO BLOCK (0:15 – 2:00)

### 0:15 — App layout *(pan over inbox, scoring, notebook panels)*

> Three panels. Inbox on the left. Scoring sheet in the middle. Evidence notebook on the right. The dataset is leak-safe — train and test splits, no shared students between them.

### 0:30 — Ad-hoc form *(click "Ad-hoc review" tab; type title; paste a real YouTube URL; assignment field type "Capstone Week 4"; mode = agent)*

> The instructor flow. Paste any new submission — title, video URL, any assignment label. The assignment field is free text, so it's not just S1 and S2. Mode is set to agent. Run.

### 0:55 — Watching it work *(spinner; switch to backend log briefly to show Gemini calls firing)*

> Behind the spinner, the backend builds a transient submission record and runs the same handwritten loop the historical dataset uses — five steps, fixed order, plain Python.

### 1:15 — Dossier renders *(point at score, confidence chip, source chip)*

> Output. Predicted score, but never alone — there's a confidence level and a source tag. `gemini` means real evidence was collected. `fallback` means the system is refusing to score, and the dossier is flagged for human review.

### 1:30 — Criterion evidence *(scroll to criterion cards)*

> Below the score, criterion-by-criterion findings — problem clarity, agentic behavior, demo quality, completeness. Each card has its own confidence, so the score isn't a single number — it's a defensible breakdown.

### 1:45 — Trace + claim ledger *(expand trace; show confirmed / weak / unsupported / open questions)*

> Right panel is the audit trail. Confirmed claims, weak claims, unsupported claims, open questions. Then the trace — every tool call, the result it produced, the belief update, the next step. If the score is wrong, you can find the exact step that broke.

---

## INTERNALS BLOCK (2:00 – 4:30)

### 2:00 — Agent loop *(open `backend/app/review_runner.py`, point at `_review`)*

> No LangGraph. No CrewAI. That's a Session 3 constraint. The agent loop is plain Python. Five method calls in fixed order — plan, inspect demo video, inspect repo, retrieve similar historical examples, synthesize the dossier.

### 2:25 — Video evidence *(open `backend/app/video_utils.py`)*

> The video step does two things. Gemini's `url_context` tool reads the page. We also fetch the YouTube transcript and inject it into the prompt with timestamps. The prompt forbids the model from fabricating quotes. If the transcript fails, the prompt admits it, and confidence drops.

### 2:50 — Repo evidence *(jump to `_inspect_repo_artifacts`, show the GitHub / GitLab / HuggingFace extractor)*

> The repo step prefers a direct URL. If the metadata has no GitHub, GitLab, Bitbucket, HuggingFace, or Colab link, the agent does grounded Google Search. The model has to ground claims in what it actually found.

### 3:10 — Refusing to score *(open `backend/app/mock_review.py`; show `fallback_predicted_score`; then flash `tests/test_fallback_no_leak.py`)*

> This is the part Session 3 cares most about. The first version leaked the ground-truth score into the fallback prediction. Agent runs reported 100 percent exact accuracy. All leak. Now the fallback uses the band midpoint, forces confidence low, and tags `source: fallback`. There's a regression test that fails the moment any code touches `submission.score` in retrieval.

### 3:35 — Shared contract *(open `schemas/review_result.schema.json`)*

> Baseline mode and agent mode return the same JSON schema. Same fields. Same enum. The API validates every response against it before returning it. That's the only way to compare the two modes fairly — Session 3 explicitly requires it.

### 3:55 — Eval lab *(scroll to evaluation lab in UI; mention `run_eval.py --concurrency`)*

> Both modes write per-row JSON, a metrics file, and a CSV. The compare script reports exact accuracy, within-250 accuracy, score-band accuracy, MAE, and MAE bucketed by confidence. If low-confidence rows don't have higher error than high-confidence rows, the confidence signal is fake.

### 4:15 — Tests *(terminal: `pytest -q` showing 32 passed)*

> Thirty-two tests. Leak regression, schema contract, JSON parser, repo extractor, YouTube ID parser. All green.

---

## WRAP (4:30 – 5:00)

### 4:30 — North-star alignment *(split-screen: `CLAUDE.md` north-star list on the left, live dossier answering each on the right)*

> Five north-star questions from the Session 3 brief. What does the project claim. What evidence supports those claims. What's missing or contradictory. What score is justified. Should a human take a closer look. The dossier answers all five — every time.

### 4:50 — Outro *(GitHub URL on screen)*

> Code is at github.com/Praneeth16/submission-review-assistant. That's it.

---

## S3 callouts visible on screen (at least once each)

- No LangGraph / No CrewAI — shown at 2:00
- Gemini Flash 3.1 — model chip on score card + health endpoint
- Trace per step — shown at 1:45
- Confidence + `needs_human_review` — chip on score card
- Baseline vs agent shared schema — shown at 3:35
- Train / test split — dataset chip in header
- Refuse / abstain — `source: fallback` chip + needs-review chip

## Production notes

- 145 wpm voice-over target. Total ≈ 720 words.
- Cut every 6–8 sec; hold longer only on trace JSON.
- Pre-record one full ad-hoc run and splice fast-forward through synthesis if Gemini call exceeds 40s.
- Captions: hand-correct `url_context`, `youtube-transcript-api`, `row_score_band`.
- Thumbnail: *"AI grader that refuses to grade"* + screenshot showing `source: gemini` and `needs human review` chips.
- Description first line: *"Session 3 build — handwritten agent loop, Gemini Flash 3.1, evidence-first review, no orchestration framework."*
