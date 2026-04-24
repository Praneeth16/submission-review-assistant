from __future__ import annotations

from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    return url.strip()


def unique_urls(urls: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for raw in urls:
        url = normalize_url(raw)
        if not url or url in seen:
            continue
        seen.add(url)
        ordered.append(url)
    return ordered


def extract_direct_repo_candidates(urls: list[str]) -> list[str]:
    candidates = []
    for url in unique_urls(urls):
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path_parts = [part for part in parsed.path.split("/") if part]
        if "github.com" in host and len(path_parts) >= 2:
            owner, repo = path_parts[0], path_parts[1]
            clean = f"{parsed.scheme or 'https'}://github.com/{owner}/{repo}"
            if clean not in candidates:
                candidates.append(clean)
    return candidates
