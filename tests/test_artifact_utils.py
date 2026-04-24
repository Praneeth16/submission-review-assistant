from __future__ import annotations

from backend.app.artifact_utils import extract_direct_repo_candidates


def test_github_repo_extracted() -> None:
    urls = ["https://github.com/acme/cool-project/tree/main/src"]
    assert extract_direct_repo_candidates(urls) == ["https://github.com/acme/cool-project"]


def test_gitlab_repo_extracted() -> None:
    urls = ["https://gitlab.com/acme/cool"]
    assert extract_direct_repo_candidates(urls) == ["https://gitlab.com/acme/cool"]


def test_bitbucket_repo_extracted() -> None:
    urls = ["https://bitbucket.org/acme/cool/src/main/"]
    assert extract_direct_repo_candidates(urls) == ["https://bitbucket.org/acme/cool"]


def test_huggingface_space_extracted() -> None:
    urls = ["https://huggingface.co/spaces/acme/demo"]
    result = extract_direct_repo_candidates(urls)
    assert result == ["https://huggingface.co/spaces/acme/demo"]


def test_huggingface_model_extracted() -> None:
    urls = ["https://huggingface.co/acme/demo-model"]
    result = extract_direct_repo_candidates(urls)
    assert result == ["https://huggingface.co/acme/demo-model"]


def test_colab_passthrough() -> None:
    urls = ["https://colab.research.google.com/drive/abc123"]
    assert extract_direct_repo_candidates(urls) == urls


def test_unrelated_youtube_ignored() -> None:
    urls = ["https://youtu.be/abc", "https://www.youtube.com/watch?v=abc"]
    assert extract_direct_repo_candidates(urls) == []


def test_dedup_and_shortening() -> None:
    urls = [
        "https://github.com/acme/cool",
        "https://github.com/acme/cool/tree/main",
        "https://www.github.com/acme/cool",
    ]
    result = extract_direct_repo_candidates(urls)
    assert result == ["https://github.com/acme/cool"]
