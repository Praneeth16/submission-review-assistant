from __future__ import annotations

import pytest

from backend.app.gemini_client import GeminiClient, GeminiClientError


def test_plain_json_parsed() -> None:
    client = GeminiClient()
    assert client._parse_json('{"a": 1}') == {"a": 1}


def test_fenced_json_parsed() -> None:
    client = GeminiClient()
    text = 'Here is the result:\n```json\n{"a": 2, "b": [1, 2]}\n```\nDone.'
    assert client._parse_json(text) == {"a": 2, "b": [1, 2]}


def test_fenced_untagged_parsed() -> None:
    client = GeminiClient()
    text = '```\n{"a": 3}\n```'
    assert client._parse_json(text) == {"a": 3}


def test_invalid_raises() -> None:
    client = GeminiClient()
    with pytest.raises(GeminiClientError):
        client._parse_json("not json at all")


def test_broken_json_block_raises() -> None:
    client = GeminiClient()
    with pytest.raises(GeminiClientError):
        client._parse_json('{"a": ')
