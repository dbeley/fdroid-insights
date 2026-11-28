"""Cache of the repository stats (stars/forks) fetched for each app.

Those numbers are purely decorative, but re-fetching ~5,000 repositories on
every run is what made the weekly export slow (and burned most of the API
quota). Entries are reused for a month, so a run only queries the apps that
were added to F-Droid since the last one.

The cache file is committed, so entries are stored as a compact
``[fetched_at (epoch seconds), stars, forks]`` list: ~330 KiB for the whole
catalogue, one line per repository, which keeps both the file and its diffs
small.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_TTL_DAYS = 30
STATS_KEYS = ("repository_stars_count", "repository_forks_count")
_ENTRY_LENGTH = 3


def load(path: str) -> dict:
    try:
        with open(path) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(cache, dict):
        logger.warning(f"Ignoring malformed cache file {path}.")
        return {}
    return cache


def save(path: str, cache: dict) -> None:
    with open(path, "w") as f:
        json.dump(cache, f, indent=1, sort_keys=True)
        f.write("\n")


def get(cache: dict, key: str, ttl_days: int = DEFAULT_TTL_DAYS, now=None):
    """Return the cached stats for `key`, or None when missing or too old."""
    entry = cache.get(key)
    if not isinstance(entry, list) or len(entry) != _ENTRY_LENGTH:
        return None
    fetched_at, stars, forks = entry
    if isinstance(fetched_at, bool) or not isinstance(fetched_at, (int, float)):
        return None
    now = now or datetime.now(timezone.utc)
    if now.timestamp() - fetched_at > ttl_days * 86400:
        return None
    return dict(zip(STATS_KEYS, (stars, forks)))


def put(cache: dict, key: str, stats: dict, now=None) -> None:
    now = now or datetime.now(timezone.utc)
    cache[key] = [
        int(now.timestamp()),
        *(stats.get(name) for name in STATS_KEYS),
    ]
