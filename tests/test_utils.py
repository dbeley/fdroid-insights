"""Regression tests for the per-repository lookups.

Fetching metadata for a repository that cannot be read (deleted, renamed,
blocked after a DMCA takedown, network error...) used to raise an unhandled
exception and abort the whole export, leaving the published data stale. Every
failing repository must now be skipped instead.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests
from github.GithubException import (
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
from gitlab.exceptions import GitlabGetError

from utils import (
    get_codeberg_repository_data,
    get_github_repository_data,
    get_gitlab_repository_data,
)


def github_exception(status: int, message: str) -> GithubException:
    return GithubException(status, {"message": message}, None)


# --- Github -----------------------------------------------------------------


def test_github_repository_stats():
    g = MagicMock()
    g.get_repo.return_value = MagicMock(stargazers_count=1234, forks_count=42)

    assert get_github_repository_data(g, "dbeley/fdroid-insights") == {
        "repository_stars_count": 1234,
        "repository_forks_count": 42,
    }


def test_github_blocked_repository_is_skipped(caplog):
    """451: repository blocked, e.g. after a DMCA takedown."""
    g = MagicMock()
    g.get_repo.side_effect = github_exception(451, "Repository access blocked")

    with caplog.at_level(logging.WARNING):
        assert get_github_repository_data(g, "Arturo254/OpenTune") == {}
    assert "Arturo254/OpenTune" in caplog.text


def test_github_forbidden_repository_is_skipped():
    """403: repository disabled or blocked from third-party access."""
    g = MagicMock()
    g.get_repo.side_effect = github_exception(403, "Repository access blocked")

    assert get_github_repository_data(g, "someone/private-repo") == {}


def test_github_missing_repository_is_skipped():
    g = MagicMock()
    g.get_repo.side_effect = UnknownObjectException(404, {"message": "Not Found"}, None)

    assert get_github_repository_data(g, "dbeley/does-not-exist") == {}


def test_github_rate_limit_sleeps_then_retries():
    g = MagicMock()
    reset = datetime.now(timezone.utc)
    g.get_rate_limit.return_value = MagicMock(core=MagicMock(reset=reset))
    g.get_repo.side_effect = [
        RateLimitExceededException(403, {"message": "API rate limit exceeded"}, None),
        MagicMock(stargazers_count=1, forks_count=2),
    ]

    with patch("utils.time.sleep") as sleep:
        stats = get_github_repository_data(g, "dbeley/fdroid-insights")

    assert sleep.called
    assert stats == {"repository_stars_count": 1, "repository_forks_count": 2}


def test_github_failure_after_rate_limit_sleep_is_skipped():
    g = MagicMock()
    reset = datetime.now(timezone.utc)
    g.get_rate_limit.return_value = MagicMock(core=MagicMock(reset=reset))
    g.get_repo.side_effect = RateLimitExceededException(
        403, {"message": "API rate limit exceeded"}, None
    )

    with patch("utils.time.sleep"):
        assert get_github_repository_data(g, "dbeley/fdroid-insights") == {}


# --- Gitlab -----------------------------------------------------------------


def test_gitlab_repository_stats():
    gl = MagicMock()
    gl.projects.get.return_value = MagicMock(star_count=10, forks_count=3)

    assert get_gitlab_repository_data(gl, "group/project") == {
        "repository_stars_count": 10,
        "repository_forks_count": 3,
    }


def test_gitlab_missing_repository_is_skipped():
    gl = MagicMock()
    gl.projects.get.side_effect = GitlabGetError("404 Not Found", response_code=404)

    assert get_gitlab_repository_data(gl, "group/deleted-project") == {}


@pytest.mark.parametrize("status", [403, 451, 500])
def test_gitlab_error_is_skipped(status):
    gl = MagicMock()
    gl.projects.get.side_effect = GitlabGetError("error", response_code=status)

    assert get_gitlab_repository_data(gl, "group/project") == {}


# --- Codeberg ---------------------------------------------------------------


def test_codeberg_repository_stats():
    response = MagicMock(status_code=200)
    response.json.return_value = {"stars_count": 5, "forks_count": 1}

    with patch("utils.requests.get", return_value=response) as get:
        assert get_codeberg_repository_data("someone/project") == {
            "repository_stars_count": 5,
            "repository_forks_count": 1,
        }
    assert get.call_args.kwargs.get("timeout"), "a request timeout must be set"


@pytest.mark.parametrize("status", [404, 429, 500])
def test_codeberg_http_error_is_skipped(status):
    response = MagicMock(status_code=status)

    with patch("utils.requests.get", return_value=response):
        assert get_codeberg_repository_data("someone/project") == {}


def test_codeberg_network_error_is_skipped():
    with patch("utils.requests.get", side_effect=requests.exceptions.ConnectionError):
        assert get_codeberg_repository_data("someone/project") == {}
