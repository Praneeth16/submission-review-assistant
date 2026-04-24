from __future__ import annotations

import os
from pathlib import Path


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if value and ((value[0] == value[-1]) and value[0] in {'"', "'"}):
        value = value[1:-1]
    return key, value


def load_local_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    original_env_keys = set(os.environ.keys())
    env_files = [
        repo_root / ".env",
        repo_root / ".env.local",
        backend_dir / ".env",
        backend_dir / ".env.local",
    ]

    for env_file in env_files:
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(raw_line)
            if not parsed:
                continue
            key, value = parsed
            if key in original_env_keys:
                continue
            os.environ[key] = value


load_local_env()
