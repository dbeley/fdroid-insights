import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
from github import Github
from gitlab import Gitlab

import stats_cache
from utils import (
    get_codeberg_repository_data,
    get_github_repository_data,
    get_gitlab_repository_data,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s :: %(message)s")
logger = logging.getLogger(__name__)

# A single unhandled error used to abort the whole export and freeze the
# published data, so apps are now exported individually. Above a certain
# failure ratio the run still aborts, to avoid silently publishing a partial
# dataset (for instance after a change in the F-Droid metadata format).
MAX_UNEXPECTED_ERROR_RATIO = 0.01

# Every app costs one HTTP request, so the export is I/O bound: fetching the
# repositories one by one took ~30 min and had no headroom left, which is how
# the CI job ended up being killed by its timeout. Stats are also cached
# between runs (see stats_cache), so only new apps are queried.
MAX_WORKERS = 5
API_TIMEOUT_SECONDS = 30
STATS_CACHE_FILE = "repository_stats_cache.json"

_thread_local = threading.local()


def _repository_apis() -> dict:
    """Build the API clients, one set per thread (sessions are not shared)."""
    apis = getattr(_thread_local, "apis", None)
    if apis is None:
        apis = _thread_local.apis = {
            "github.com": Github(
                os.environ.get("GITHUB_TOKEN"), timeout=API_TIMEOUT_SECONDS
            ),
            "gitlab.com": Gitlab(
                private_token=os.environ.get("GITLAB_TOKEN"),
                timeout=API_TIMEOUT_SECONDS,
            ),
            "invent.kde.org": Gitlab(
                url="https://invent.kde.org",
                private_token=os.environ.get("GITLAB_KDE_TOKEN"),
                timeout=API_TIMEOUT_SECONDS,
            ),
        }
    return apis


def _extract_repository_name(repository: str, repository_domain: str) -> str:
    repository_name = (
        repository.split("://")[-1].split(f"{repository_domain}/")[-1].strip("/")
    )
    if repository_name.count("/") > 1:
        repository_name = (
            repository_name.split("/")[0] + "/" + repository_name.split("/")[1]
        )
    return repository_name


def _fetch_repository_stats(repository: str, repository_domain: str) -> dict:
    repository_name = _extract_repository_name(repository, repository_domain)
    apis = _repository_apis()
    match repository_domain:
        case "github.com":
            return get_github_repository_data(apis["github.com"], repository_name)
        case "codeberg.org":
            return get_codeberg_repository_data(repository_name)
        case "gitlab.com":
            return get_gitlab_repository_data(apis["gitlab.com"], repository_name)
        case "invent.kde.org":
            return get_gitlab_repository_data(apis["invent.kde.org"], repository_name)
    return {}


def _get_repository_stats(repository: str, repository_domain: str, cache: dict, now):
    if not repository:
        return {}
    cache_key = (
        f"{repository_domain}/"
        f"{_extract_repository_name(repository, repository_domain)}"
    )
    cached_stats = stats_cache.get(cache, cache_key, now=now)
    if cached_stats is not None:
        return cached_stats
    repository_stats = _fetch_repository_stats(repository, repository_domain)
    if repository_stats:
        stats_cache.put(cache, cache_key, repository_stats, now=now)
    return repository_stats


def _export_app(item, total_apps: int, cache: dict, now) -> dict | None:
    index, (app_name, app_raw_data) = item
    try:
        metadata = app_raw_data["metadata"]
        repository = metadata.get("sourceCode", "")
        repository_domain = (
            repository.split("://")[1].split("/")[0] if repository else ""
        )
        repository_stats = _get_repository_stats(
            repository, repository_domain, cache, now
        )
        summary_en = (
            metadata["summary"].get("en-US", "") if "summary" in metadata else ""
        )
        icon_url = metadata["icon"].get("en-US", "") if "icon" in metadata else ""
        if icon_url:
            icon_url = f"https://f-droid.org/repo{icon_url['name']}"

        categories = ", ".join(metadata.get("categories", []))

        record = {
            "name": metadata["name"]["en-US"],
            "icon": icon_url,
            "id": app_name,
            "repository": repository,
            **repository_stats,
            "repository_domain": repository_domain,
            "summary": summary_en,
            # "description" is left out on purpose: too large for the page.
            "categories": categories,
            "added": metadata["added"],
            "last_updated": metadata["lastUpdated"],
            "url": f"https://f-droid.org/en/packages/{app_name}",
        }
        logger.info("[%s/%s] fetched %s", index, total_apps, app_name)
        return record
    except Exception as error:
        logger.warning(
            "Skipping %s: unexpected %s (%s)",
            app_name,
            type(error).__name__,
            error,
        )
        return None


def main() -> None:
    with open("index-v2.json", "rb") as f:
        json_object = json.load(f)

    # two parent objects: repo and packages
    # repo object: name, description, icon, address, mirrors, timestamp,
    # antiFeatures, categories, releaseChannels
    # packages object: name of all the apps (5000+)
    json_items = list(json_object["packages"].items())
    total_apps = len(json_items)
    logger.info("Fetching data for %s apps...", total_apps)

    cache = stats_cache.load(STATS_CACHE_FILE)
    now = datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        records = list(
            pool.map(
                lambda item: _export_app(item, total_apps, cache, now),
                enumerate(json_items, 1),
            )
        )
    # Saved even when the run aborts below: what was fetched is still valid.
    stats_cache.save(STATS_CACHE_FILE, cache)

    list_data = [record for record in records if record is not None]
    unexpected_errors = total_apps - len(list_data)
    if unexpected_errors:
        logger.warning("%s/%s apps were skipped.", unexpected_errors, total_apps)
        if unexpected_errors > max(10, total_apps * MAX_UNEXPECTED_ERROR_RATIO):
            raise RuntimeError(
                f"{unexpected_errors}/{total_apps} apps could not be exported, "
                "aborting instead of publishing a partial export."
            )

    df = pd.DataFrame.from_records(list_data)
    # Columns are missing when every lookup failed (rate limit, invalid token):
    # fail on the export itself rather than on a KeyError at the end of a run.
    for column in ("repository_stars_count", "repository_forks_count"):
        if column not in df.columns:
            df[column] = pd.NA
    df = df.astype(
        {
            "repository_stars_count": "Int64",
            "repository_forks_count": "Int64",
        }
    )
    df = df.sort_values(by=["name"])
    df.to_csv("export.csv", index=False)


if __name__ == "__main__":
    main()
