from __future__ import annotations

from urllib.parse import urlparse


REPO_HOSTS: dict[str, int] = {
    "github.com": 2,
    "www.github.com": 2,
    "gitlab.com": 2,
    "www.gitlab.com": 2,
    "bitbucket.org": 2,
    "www.bitbucket.org": 2,
    "huggingface.co": 3,
    "www.huggingface.co": 3,
}


def normalize_url(url: str) -> str:
    return url.strip()


def unique_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in urls:
        url = normalize_url(raw)
        if not url or url in seen:
            continue
        seen.add(url)
        ordered.append(url)
    return ordered


def extract_direct_repo_candidates(urls: list[str]) -> list[str]:
    candidates: list[str] = []
    for url in unique_urls(urls):
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        min_parts = REPO_HOSTS.get(host)
        if min_parts is None:
            if "colab.research.google.com" in host:
                candidates.append(url)
            continue
        path_parts = [part for part in parsed.path.split("/") if part]
        if host.endswith("huggingface.co") and path_parts:
            if path_parts[0] not in {"spaces", "datasets"}:
                # huggingface model repo uses 2 parts (owner/repo) — keep permissive
                min_parts = 2
        if len(path_parts) < min_parts:
            continue
        scheme = parsed.scheme or "https"
        canonical_host = host.replace("www.", "")
        clean = f"{scheme}://{canonical_host}/" + "/".join(path_parts[:min_parts])
        if clean not in candidates:
            candidates.append(clean)
    return candidates
