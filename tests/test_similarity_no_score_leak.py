from __future__ import annotations

import inspect
import io
import tokenize

from backend.app import data as data_module


def _code_only(source: str) -> str:
    """Return source with comments and string literals removed so we can
    assert on real name references, not doc-string mentions."""

    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    kept: list[str] = []
    for tok in tokens:
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        kept.append(tok.string)
    return " ".join(kept)


def test_similarity_key_does_not_read_target_score() -> None:
    """The retrieval ranker must not read target.score — at inference time
    the runner treats ground truth as hidden."""

    source = inspect.getsource(data_module.find_similar_examples)
    code = _code_only(source)
    assert "target.score" not in code, (
        "find_similar_examples should not rank by target.score (GT leak)."
    )
