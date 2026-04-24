# CLAUDE.md

## Working brief

You are helping build `Submission Review Copilot`, a browser-native agent that reviews project submissions by collecting evidence across the gallery page, demo video, repo, and linked artifacts.

The aim is not to fake certainty. The aim is to help a human judge move faster with better evidence.

## Build constraints

- Do not use LangGraph.
- Do not use CrewAI.
- Do not use an agent framework for tool orchestration.
- Keep the loop manual and explicit.
- Use Gemini Flash 3.1 as the primary model.

The implementation should make the agent logic visible in ordinary application code.

## North star

For every submission, answer:

1. What does the project claim to do?
2. What evidence supports those claims?
3. What evidence is missing or contradictory?
4. What provisional score is justified from the evidence?
5. Should a human reviewer take a closer look?

## Operating principles

### Evidence first

Start from artifacts, not assumptions.

Good sequence:

- read the page
- inspect the video
- inspect the repo
- verify claims
- score

Bad sequence:

- infer score
- search for supporting evidence

### Confidence is part of the output

Every result should make room for uncertainty.

Use confidence labels such as:

- high
- medium
- low

Low-confidence cases should lean toward "needs human review."

### Use historical scores carefully

Historical scores are for calibration, not imitation.

Use them to:

- anchor score ranges
- compare against similar projects
- explain why this submission looks above or below nearby examples

Do not use them to:

- claim the system has learned instructor preferences
- hide weak evidence behind a prior score pattern

### Use the dataset as raw evidence support

The project has a raw gallery index at:

- `data/submission_gallery_index.csv`

It is generated from the two assignment gallery HTML pages and should be treated as source material for retrieval, calibration, and analysis.

Do not hand-edit the raw CSV.

### Use a shared evaluation contract

When building runners or prompts, align to:

- `EVALUATION.md`
- `schemas/review_request.schema.json`
- `schemas/review_result.schema.json`

The baseline and the agent should differ in workflow, not in output shape.

## Expected tool behaviors

### `read_submission_page`

Pull:

- title
- description
- demo link
- repo link
- assignment notes
- visible claims

### `inspect_demo_video`

Pull:

- transcript snippets
- timestamps
- feature claims
- evidence of working behavior

Implementation note:

- Prefer Gemini Flash 3.1 on the YouTube URL directly when possible.
- If a transcript is available, keep the relevant quote and timestamp in the trace.
- If the video provider is not YouTube, fall back to the best available public artifact flow and lower confidence if needed.

### `inspect_repo`

Pull:

- stack and structure
- README quality
- likely implementation files
- feature evidence
- obvious gaps

### `verify_claims_against_code`

For each major claim:

- supported
- weakly supported
- unsupported
- unclear

### `inspect_external_artifacts`

Use sparingly. Only inspect live demos or docs when they help resolve a rubric criterion or claim dispute.

If Gemini Flash 3.1 needs more context, let it reason over the URL or page content, but keep the output tied to evidence rather than broad prose.

### `retrieve_similar_scored_examples`

Use only after primary evidence collection.

## Review output format

Prefer this structure:

### Summary

One paragraph on what the project appears to be and how complete it looks.

### Evidence by criterion

For each rubric item:

- short finding
- evidence source
- confidence
- provisional score band

### Claim verification

- confirmed claims
- weak claims
- unsupported claims
- open questions

### Final recommendation

- provisional score
- confidence
- advance / borderline / reject
- needs human review: yes/no

### Trace expectations

For each major reasoning step, capture:

- current question
- selected tool
- tool result
- what changed in the belief state
- next step

This is important for the assignment and for reviewer trust.

## What to optimize for

- reviewer trust
- traceability
- fewer hallucinated claims
- honest uncertainty
- useful evidence gathering

## What not to optimize for

- matching historical scores at all costs
- inflated certainty
- clever wording without proof
- overbuilt autonomy
- framework-heavy architecture

## Demo priorities

If you have to choose, prefer:

1. a clear trace over a fancy score
2. a concrete contradiction over a vague summary
3. a useful abstention over a made-up judgment
4. a handwritten agent loop over a framework demo

## Writing style for outputs

- plainspoken
- concise
- specific
- no hype
- no inflated academic language

The final product should sound like a thoughtful reviewer, not a marketing page and not a robotic rubric engine.
