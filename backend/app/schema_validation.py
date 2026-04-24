from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_SCHEMA_PATH = REPO_ROOT / "schemas" / "review_result.schema.json"
REQUEST_SCHEMA_PATH = REPO_ROOT / "schemas" / "review_request.schema.json"


class ReviewResultSchemaError(ValueError):
    pass


@lru_cache(maxsize=1)
def _result_validator() -> Draft202012Validator:
    schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


@lru_cache(maxsize=1)
def _request_validator() -> Draft202012Validator:
    schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate_review_result(payload: dict) -> None:
    errors = sorted(_result_validator().iter_errors(payload), key=lambda err: err.path)
    if not errors:
        return
    joined = "; ".join(f"{list(err.path)}: {err.message}" for err in errors)
    raise ReviewResultSchemaError(f"review_result schema violations: {joined}")


def validate_review_request(payload: dict) -> None:
    errors = sorted(_request_validator().iter_errors(payload), key=lambda err: err.path)
    if not errors:
        return
    joined = "; ".join(f"{list(err.path)}: {err.message}" for err in errors)
    raise ReviewResultSchemaError(f"review_request schema violations: {joined}")
