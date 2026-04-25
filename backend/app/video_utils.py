from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


logger = logging.getLogger(__name__)


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


@dataclass
class TranscriptSnippet:
    text: str
    start: float
    duration: float

    @property
    def timestamp(self) -> str:
        minutes, seconds = divmod(int(self.start), 60)
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class TranscriptResult:
    available: bool
    video_id: str | None
    language: str | None
    snippets: list[TranscriptSnippet]
    error: str | None = None

    def as_prompt_block(self, *, max_chars: int = 6000) -> str:
        if not self.available or not self.snippets:
            return ""
        lines: list[str] = []
        used = 0
        for snippet in self.snippets:
            line = f"[{snippet.timestamp}] {snippet.text}"
            if used + len(line) + 1 > max_chars:
                lines.append("... (transcript truncated)")
                break
            lines.append(line)
            used += len(line) + 1
        return "\n".join(lines)


def extract_youtube_video_id(url: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None

    host = parsed.netloc.lower()
    if host not in YOUTUBE_HOSTS:
        return None

    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    else:
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts and path_parts[0] in {"shorts", "embed", "v", "live"} and len(path_parts) >= 2:
            candidate = path_parts[1]
        else:
            query = parse_qs(parsed.query)
            candidate = (query.get("v") or [""])[0]

    if candidate and _VIDEO_ID_RE.match(candidate):
        return candidate
    return None


def fetch_youtube_transcript(url: str, *, languages: list[str] | None = None) -> TranscriptResult:
    """Fetch a YouTube transcript using youtube-transcript-api when available.

    Returns a TranscriptResult describing success or why it failed. Never
    raises — caller should treat absence as "no transcript signal" rather
    than a hard error, so a review can still run on metadata + Gemini's
    url_context tool alone.
    """

    video_id = extract_youtube_video_id(url)
    if not video_id:
        return TranscriptResult(
            available=False,
            video_id=None,
            language=None,
            snippets=[],
            error="URL is not a recognizable YouTube video URL.",
        )

    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
        from youtube_transcript_api._errors import (  # type: ignore
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
        )
    except ImportError:
        logger.info("youtube-transcript-api not installed; skipping transcript fetch for %s", video_id)
        return TranscriptResult(
            available=False,
            video_id=video_id,
            language=None,
            snippets=[],
            error="youtube-transcript-api is not installed.",
        )

    preferred_languages = languages or ["en", "en-US", "en-GB"]

    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
    except (TranscriptsDisabled, VideoUnavailable) as exc:
        logger.info("Transcript unavailable for %s: %s", video_id, exc)
        return TranscriptResult(
            available=False,
            video_id=video_id,
            language=None,
            snippets=[],
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 — protect the review loop
        logger.warning("Unexpected transcript lookup error for %s: %s", video_id, exc)
        return TranscriptResult(
            available=False,
            video_id=video_id,
            language=None,
            snippets=[],
            error=f"{type(exc).__name__}: {exc}",
        )

    transcript = None
    language = None
    try:
        transcript = transcripts.find_manually_created_transcript(preferred_languages)
        language = transcript.language_code
    except NoTranscriptFound:
        try:
            transcript = transcripts.find_generated_transcript(preferred_languages)
            language = transcript.language_code
        except NoTranscriptFound:
            for candidate in transcripts:
                try:
                    transcript = candidate.translate("en")
                    language = "en (translated)"
                    break
                except Exception:  # noqa: BLE001
                    continue

    if transcript is None:
        return TranscriptResult(
            available=False,
            video_id=video_id,
            language=None,
            snippets=[],
            error="No transcripts found for this video.",
        )

    try:
        raw = transcript.fetch()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Transcript fetch failed for %s: %s", video_id, exc)
        return TranscriptResult(
            available=False,
            video_id=video_id,
            language=language,
            snippets=[],
            error=f"{type(exc).__name__}: {exc}",
        )

    snippets = [
        TranscriptSnippet(
            text=str(entry.get("text", "")).strip(),
            start=float(entry.get("start", 0.0)),
            duration=float(entry.get("duration", 0.0)),
        )
        for entry in raw
        if entry.get("text")
    ]

    return TranscriptResult(
        available=bool(snippets),
        video_id=video_id,
        language=language,
        snippets=snippets,
    )
