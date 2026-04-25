from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = REPO_ROOT / "logs"


def _log_dir() -> Path:
    override = os.getenv("LLM_LOG_DIR")
    return Path(override) if override else DEFAULT_LOG_DIR


def _enabled() -> bool:
    return os.getenv("LLM_LOG_DISABLED") != "1"


_PROMPT_TRUNC = int(os.getenv("LLM_LOG_PROMPT_MAX", "8000"))
_RESPONSE_TRUNC = int(os.getenv("LLM_LOG_RESPONSE_MAX", "8000"))


_review_id_var: ContextVar[Optional[str]] = ContextVar("review_id", default=None)
_step_name_var: ContextVar[Optional[str]] = ContextVar("step_name", default=None)
_review_meta_var: ContextVar[Optional[dict]] = ContextVar("review_meta", default=None)

_jsonl_lock = threading.Lock()
_review_locks: dict[str, threading.Lock] = {}
_review_locks_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if text is None:
        return "", False
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def _ensure_dirs() -> None:
    base = _log_dir()
    (base / "reviews").mkdir(parents=True, exist_ok=True)


def _review_lock(review_id: str) -> threading.Lock:
    with _review_locks_lock:
        lock = _review_locks.get(review_id)
        if lock is None:
            lock = threading.Lock()
            _review_locks[review_id] = lock
        return lock


def start_review(*, mode: str, source: str, meta: dict[str, Any]) -> str:
    """Open a logging session for a single review run.

    Returns the review_id and seeds the per-request file with metadata.
    """

    review_id = uuid.uuid4().hex
    _review_id_var.set(review_id)
    _step_name_var.set(None)
    payload = {
        "review_id": review_id,
        "started_at": _now_iso(),
        "mode": mode,
        "source": source,
        "submission": meta,
        "calls": [],
    }
    _review_meta_var.set(payload)

    if _enabled():
        try:
            _ensure_dirs()
            path = _log_dir() / "reviews" / f"{review_id}.json"
            with _review_lock(review_id):
                path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("LLM logger could not initialize per-review file: %s", exc)

    return review_id


def set_step(step_name: str) -> None:
    _step_name_var.set(step_name)


def current_review_id() -> Optional[str]:
    return _review_id_var.get()


def record_call(
    *,
    prompt: str,
    response_text: str,
    response_json: Optional[dict],
    model: str,
    tools: Optional[list[dict]],
    latency_ms: int,
    error: Optional[str],
) -> None:
    if not _enabled():
        return

    review_id = _review_id_var.get()
    step_name = _step_name_var.get()
    meta = _review_meta_var.get() or {}

    prompt_text, prompt_truncated = _truncate(prompt, _PROMPT_TRUNC)
    response_truncated_text, response_truncated = _truncate(response_text or "", _RESPONSE_TRUNC)

    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "ts": _now_iso(),
        "review_id": review_id,
        "step": step_name,
        "model": model,
        "tools": tools or [],
        "latency_ms": latency_ms,
        "prompt": prompt_text,
        "prompt_truncated": prompt_truncated,
        "response_text": response_truncated_text,
        "response_truncated": response_truncated,
        "response_json": response_json,
        "error": error,
        "submission": {
            "student_id": (meta.get("submission") or {}).get("student_id"),
            "session": (meta.get("submission") or {}).get("session"),
        },
        "mode": meta.get("mode"),
        "source": meta.get("source"),
    }

    try:
        _ensure_dirs()
        jsonl_path = _log_dir() / "llm_calls.jsonl"
        line = json.dumps(entry, ensure_ascii=False)
        with _jsonl_lock:
            with jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except OSError as exc:
        logger.warning("LLM logger could not append to JSONL: %s", exc)
        return

    if review_id:
        try:
            review_path = _log_dir() / "reviews" / f"{review_id}.json"
            with _review_lock(review_id):
                if review_path.exists():
                    payload = json.loads(review_path.read_text(encoding="utf-8"))
                else:
                    payload = {"review_id": review_id, "calls": []}
                payload.setdefault("calls", []).append(entry)
                review_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("LLM logger could not append to per-review file: %s", exc)


def finish_review(*, result: Optional[dict], error: Optional[str] = None) -> None:
    if not _enabled():
        return

    review_id = _review_id_var.get()
    if not review_id:
        return

    try:
        review_path = _log_dir() / "reviews" / f"{review_id}.json"
        with _review_lock(review_id):
            if review_path.exists():
                payload = json.loads(review_path.read_text(encoding="utf-8"))
            else:
                payload = {"review_id": review_id, "calls": []}
            payload["finished_at"] = _now_iso()
            payload["result"] = result
            payload["error"] = error
            review_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("LLM logger could not finalize per-review file: %s", exc)
    finally:
        with _review_locks_lock:
            _review_locks.pop(review_id, None)
        _review_id_var.set(None)
        _step_name_var.set(None)
        _review_meta_var.set(None)


class StepTimer:
    """Helper to set step name and time the call automatically.

    Usage:
        with StepTimer("plan_review"):
            client.generate_json(prompt)
    """

    def __init__(self, step_name: str):
        self.step_name = step_name
        self._token = None

    def __enter__(self) -> "StepTimer":
        self._token = _step_name_var.set(self.step_name)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._token is not None:
            _step_name_var.reset(self._token)


def now_ms() -> int:
    return int(time.time() * 1000)
