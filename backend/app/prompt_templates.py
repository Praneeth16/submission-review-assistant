from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_PROMPT_TEMPLATES: dict[str, str] = {
    "plan_review": """
You are planning a review run for a project submission.

Mode: {mode}
Student: {student_id}
Session: {session}
Author: {author}
Primary title: {primary_title}
Primary platform: {primary_platform}
Primary URL: {primary_video_url}
Candidate count: {candidate_count}
Selection notes: {selection_notes}

Rubric:
{rubric_lines}

Return JSON with this shape:
{{
  "review_plan": {{
    "focus_areas": ["..."],
    "evidence_gaps": ["..."],
    "first_question": "..."
  }},
  "trace": {{
    "result_summary": "...",
    "belief_update": "...",
    "next_step": "..."
  }}
}}
""".strip(),
    "inspect_demo_video": """
Review the project demo at this URL:
{primary_video_url}

Submission title: {primary_title}
Author: {author}
Session: {session}
Mode: {mode}

Use the URL context tool to inspect the URL. If the URL contains a video, infer the main project claims, what appears to be implemented, and what still looks uncertain.

Return JSON with this shape:
{{
  "video_summary": {{
    "project_summary": "...",
    "likely_claims": ["..."],
    "implementation_signals": ["..."],
    "uncertainties": ["..."],
    "score_hint": {{
      "predicted_score": 1000,
      "confidence": "medium",
      "reason": "..."
    }}
  }},
  "trace": {{
    "result_summary": "...",
    "belief_update": "...",
    "next_step": "..."
  }}
}}
""".strip(),
    "inspect_alternate_artifacts": """
We already inspected the primary artifact for this submission.

Primary title: {primary_title}
Alternate titles: {all_titles}
Alternate URLs: {all_video_urls}
Platforms: {all_platforms}

Use URL context when helpful and judge whether the alternate artifacts reinforce the same project story, look like duplicates, or suggest multiple different submissions.

Return JSON:
{{
  "artifact_summary": {{
    "alternate_signal": "supports_primary|duplicates_primary|mixed_signals",
    "confidence_adjustment": "raise|none|lower",
    "notes": ["..."]
  }},
  "trace": {{
    "result_summary": "...",
    "belief_update": "...",
    "next_step": "..."
  }}
}}
""".strip(),
    "inspect_repo_artifacts": """
You are trying to gather code evidence for a project submission.

Submission title: {primary_title}
Author: {author}
Session: {session}
Known artifact URLs: {all_video_urls}
Direct repo candidates from known URLs: {direct_repo_candidates}

If a direct repo candidate exists, inspect it with URL context. If no direct repo candidate exists, use grounded Google Search to look for a likely public GitHub repo or code artifact that appears to belong to this project.

Return JSON:
{{
  "repo_summary": {{
    "repo_signal": "direct_repo|searched_repo|no_repo_found",
    "repo_url": "...",
    "stack_signals": ["..."],
    "implementation_signals": ["..."],
    "limitations": ["..."]
  }},
  "trace": {{
    "result_summary": "...",
    "belief_update": "...",
    "next_step": "..."
  }}
}}
""".strip(),
    "synthesize_review": """
You are producing the final evidence-backed review dossier for a technical project submission.

Mode: {mode}
Submission metadata:
- student_id: {student_id}
- session: {session}
- author: {author}
- title: {primary_title}
- split: {split}
- score band anchor from dataset: {row_score_band}

Rubric:
{rubric_lines}

Review plan:
{review_plan}

Video summary:
{video_summary}

Repo summary:
{repo_summary}

Alternate artifact summary:
{alternate_summary}

Similar scored examples:
{similar_examples}

Return JSON with this exact shape:
{{
  "predicted_score": 1000,
  "predicted_score_band": "strong_1000_1499",
  "confidence": "medium",
  "needs_human_review": false,
  "summary": "...",
  "criterion_evidence": [
    {{
      "criterion": "Problem clarity",
      "finding": "...",
      "evidence_source": "video_summary",
      "confidence": "medium",
      "provisional_score_band": "high"
    }}
  ],
  "claim_verification": {{
    "confirmed_claims": ["..."],
    "weak_claims": ["..."],
    "unsupported_claims": ["..."],
    "open_questions": ["..."]
  }},
  "trace": {{
    "result_summary": "...",
    "belief_update": "...",
    "next_step": "..."
  }}
}}
""".strip(),
}


def load_prompt_templates() -> dict[str, str]:
    path = os.getenv("PROMPT_TEMPLATES_PATH")
    if not path:
        return dict(DEFAULT_PROMPT_TEMPLATES)

    template_path = Path(path)
    data = json.loads(template_path.read_text(encoding="utf-8"))
    merged = dict(DEFAULT_PROMPT_TEMPLATES)
    merged.update({key: value for key, value in data.items() if isinstance(value, str)})
    return merged
