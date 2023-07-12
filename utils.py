import calendar
import logging
import requests
import time
from github import Github
from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError
from github.GithubException import UnknownObjectException
from github.GithubException import RateLimitExceededException

logger = logging.getLogger(__name__)


def get_github_repository_data(g: Github, repository_name: str):
    try:
        repo = g.get_repo(repository_name)
    except UnknownObjectException:
        logger.warning(f"Repository {repository_name} was not found on Github.")
        return {}
    except RateLimitExceededException:
        core_rate_limit = g.get_rate_limit().core
        reset_timestamp = calendar.timegm(core_rate_limit.reset.timetuple())
        sleep_time = reset_timestamp - calendar.timegm(time.gmtime()) + 10
        logger.warning(f"Rate-limit detected, sleeping for {sleep_time} seconds.")
        time.sleep(sleep_time)
        repo = g.get_repo(repository_name)
    return {
        "repository_stars_count": repo.stargazers_count,
        "repository_forks_count": repo.forks_count,
    }


def get_gitlab_repository_data(gl: Gitlab, repository_name: str):
    try:
        repo = gl.projects.get(repository_name)
    except GitlabGetError:
        logger.warning(f"Repository {repository_name} was not found on Gitlab.")
        return {}
    return {
        "repository_stars_count": repo.star_count,
        "repository_forks_count": repo.forks_count,
    }


def get_codeberg_repository_data(repository_name: str):
    result = requests.get(f"https://codeberg.org/api/v1/repos/{repository_name}")
    if result.status_code == 200:
        json_result = result.json()
        return {
            "repository_stars_count": json_result.get("stars_count"),
            "repository_forks_count": json_result.get("forks_count"),
        }
    return {}
