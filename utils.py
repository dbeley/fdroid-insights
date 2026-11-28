import calendar
import logging
import requests
import time
from github import Github
from gitlab import Gitlab
from gitlab.exceptions import GitlabAuthenticationError
from gitlab.exceptions import GitlabError
from gitlab.exceptions import GitlabGetError
from github.GithubException import GithubException
from github.GithubException import UnknownObjectException
from github.GithubException import RateLimitExceededException

logger = logging.getLogger(__name__)

# Fetched repository metadata is only used to display stars/forks counts, so any
# repository we cannot read (blocked, deleted, renamed, rate-limited...) is
# skipped rather than aborting the whole export.

# Waiting for a rate-limit reset can cost a full hour, per hit, with no upper
# bound: that is what made the CI job run until it was killed by its timeout.
# Sleep only for short windows, skip the repository otherwise.
MAX_RATE_LIMIT_SLEEP_SECONDS = 300


def _seconds_until_rate_limit_reset(g: Github) -> int:
    core_rate_limit = g.get_rate_limit().core
    reset_timestamp = calendar.timegm(core_rate_limit.reset.timetuple())
    return reset_timestamp - calendar.timegm(time.gmtime()) + 10


def _fetch_github_repo(g: Github, repository_name: str):
    try:
        return g.get_repo(repository_name)
    except RateLimitExceededException:
        sleep_time = _seconds_until_rate_limit_reset(g)
        if sleep_time > MAX_RATE_LIMIT_SLEEP_SECONDS:
            logger.warning(
                f"Rate-limit detected, reset in {sleep_time} seconds: skipping "
                f"{repository_name} instead of stalling the export."
            )
            raise
        logger.warning(f"Rate-limit detected, sleeping for {sleep_time} seconds.")
        time.sleep(sleep_time)
        return g.get_repo(repository_name)


def get_github_repository_data(g: Github, repository_name: str):
    try:
        repo = _fetch_github_repo(g, repository_name)
    except UnknownObjectException:
        logger.warning(f"Repository {repository_name} was not found on Github.")
        return {}
    except GithubException as e:
        # e.g. 451: repository access blocked after a DMCA takedown, 403:
        # repository disabled or blocked from third-party access.
        logger.warning(
            f"Repository {repository_name} is not accessible on Github "
            f"(HTTP {e.status}), skipping it."
        )
        return {}
    return {
        "repository_stars_count": repo.stargazers_count,
        "repository_forks_count": repo.forks_count,
    }


def get_gitlab_repository_data(gl: Gitlab, repository_name: str):
    try:
        repo = gl.projects.get(repository_name)
    except GitlabAuthenticationError:
        logger.warning(f"Invalid GitLab token, skipping {repository_name}.")
        return {}
    except GitlabGetError:
        logger.warning(f"Repository {repository_name} was not found on Gitlab.")
        return {}
    except GitlabError as e:
        logger.warning(
            f"Repository {repository_name} is not accessible on Gitlab ({e}), "
            f"skipping it."
        )
        return {}
    return {
        "repository_stars_count": repo.star_count,
        "repository_forks_count": repo.forks_count,
    }


def get_codeberg_repository_data(repository_name: str):
    try:
        result = requests.get(
            f"https://codeberg.org/api/v1/repos/{repository_name}", timeout=30
        )
    except requests.RequestException as e:
        logger.warning(
            f"Repository {repository_name} could not be fetched on Codeberg ({e}), "
            f"skipping it."
        )
        return {}
    if result.status_code != 200:
        logger.warning(
            f"Repository {repository_name} is not accessible on Codeberg "
            f"(HTTP {result.status_code}), skipping it."
        )
        return {}
    json_result = result.json()
    return {
        "repository_stars_count": json_result.get("stars_count"),
        "repository_forks_count": json_result.get("forks_count"),
    }
