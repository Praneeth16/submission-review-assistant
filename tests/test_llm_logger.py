from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.app import llm_logger


@pytest.fixture(autouse=True)
def isolated_log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("LLM_LOG_DISABLED", raising=False)
    yield tmp_path


def test_start_review_creates_per_review_file(isolated_log_dir: Path) -> None:
    review_id = llm_logger.start_review(
        mode="agent",
        source="dataset",
        meta={"student_id": "200", "session": "S1", "primary_title": "Demo"},
    )
    path = isolated_log_dir / "reviews" / f"{review_id}.json"
    assert path.exists()

    payload = json.loads(path.read_text())
    assert payload["mode"] == "agent"
    assert payload["source"] == "dataset"
    assert payload["submission"]["student_id"] == "200"
    assert payload["calls"] == []

    llm_logger.finish_review(result={"ok": True})


def test_record_call_appends_to_jsonl_and_review_file(isolated_log_dir: Path) -> None:
    review_id = llm_logger.start_review(
        mode="agent",
        source="adhoc",
        meta={"student_id": "adhoc", "session": "Capstone", "primary_title": "T"},
    )
    llm_logger.set_step("plan_review")
    llm_logger.record_call(
        prompt="hello",
        response_text='{"a": 1}',
        response_json=None,
        model="gemini-test",
        tools=[{"url_context": {}}],
        latency_ms=42,
        error=None,
    )

    jsonl = (isolated_log_dir / "llm_calls.jsonl").read_text().strip().splitlines()
    assert len(jsonl) == 1
    entry = json.loads(jsonl[0])
    assert entry["step"] == "plan_review"
    assert entry["model"] == "gemini-test"
    assert entry["latency_ms"] == 42
    assert entry["review_id"] == review_id
    assert entry["mode"] == "agent"
    assert entry["source"] == "adhoc"

    review_payload = json.loads(
        (isolated_log_dir / "reviews" / f"{review_id}.json").read_text()
    )
    assert len(review_payload["calls"]) == 1
    assert review_payload["calls"][0]["prompt"] == "hello"

    llm_logger.finish_review(result={"ok": True})
    final = json.loads(
        (isolated_log_dir / "reviews" / f"{review_id}.json").read_text()
    )
    assert final["finished_at"]
    assert final["result"] == {"ok": True}


def test_record_call_truncates_long_prompts(isolated_log_dir: Path, monkeypatch) -> None:
    monkeypatch.setattr(llm_logger, "_PROMPT_TRUNC", 16)
    monkeypatch.setattr(llm_logger, "_RESPONSE_TRUNC", 8)

    llm_logger.start_review(mode="baseline", source="dataset", meta={})
    llm_logger.set_step("synthesize_dossier")
    llm_logger.record_call(
        prompt="x" * 100,
        response_text="y" * 100,
        response_json=None,
        model="gemini-test",
        tools=None,
        latency_ms=10,
        error=None,
    )

    entry = json.loads((isolated_log_dir / "llm_calls.jsonl").read_text().strip())
    assert entry["prompt_truncated"] is True
    assert len(entry["prompt"]) == 16
    assert entry["response_truncated"] is True
    assert len(entry["response_text"]) == 8

    llm_logger.finish_review(result=None)


def test_disabled_logger_writes_nothing(isolated_log_dir: Path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_LOG_DISABLED", "1")
    llm_logger.start_review(mode="agent", source="dataset", meta={})
    llm_logger.record_call(
        prompt="p",
        response_text="r",
        response_json=None,
        model="m",
        tools=None,
        latency_ms=1,
        error=None,
    )
    llm_logger.finish_review(result=None)
    assert not (isolated_log_dir / "llm_calls.jsonl").exists()
    assert not (isolated_log_dir / "reviews").exists()
