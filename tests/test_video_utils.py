from __future__ import annotations

from backend.app.video_utils import extract_youtube_video_id, fetch_youtube_transcript


def test_extract_from_youtu_be() -> None:
    assert extract_youtube_video_id("https://youtu.be/pV8O0fbMPuc") == "pV8O0fbMPuc"


def test_extract_from_watch_url() -> None:
    assert (
        extract_youtube_video_id("https://www.youtube.com/watch?v=pV8O0fbMPuc&t=10s")
        == "pV8O0fbMPuc"
    )


def test_extract_from_shorts() -> None:
    assert extract_youtube_video_id("https://youtube.com/shorts/abcdefghijk") == "abcdefghijk"


def test_extract_from_embed() -> None:
    assert extract_youtube_video_id("https://www.youtube.com/embed/aaaaaaaaaaa") == "aaaaaaaaaaa"


def test_extract_rejects_non_youtube() -> None:
    assert extract_youtube_video_id("https://example.com/watch?v=abc") is None


def test_extract_rejects_short_id() -> None:
    assert extract_youtube_video_id("https://youtu.be/short") is None


def test_fetch_handles_non_youtube_gracefully() -> None:
    result = fetch_youtube_transcript("https://example.com/not-a-video")
    assert result.available is False
    assert result.snippets == []
    assert result.video_id is None
    assert result.error is not None
