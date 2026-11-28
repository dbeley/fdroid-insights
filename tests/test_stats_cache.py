"""Tests for the repository stats cache.

The cache only exists to keep the weekly export cheap: it must never serve
values older than its TTL, and a broken cache file must never abort a run.
"""

from datetime import datetime, timedelta, timezone

import stats_cache

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
KEY = "github.com/dbeley/fdroid-insights"
STATS = {"repository_stars_count": 12, "repository_forks_count": 3}


def test_fresh_entry_is_used():
    cache = {}
    stats_cache.put(cache, KEY, STATS, now=NOW)

    assert stats_cache.get(cache, KEY, now=NOW + timedelta(days=1)) == STATS


def test_stale_entry_is_refetched():
    cache = {}
    stats_cache.put(cache, KEY, STATS, now=NOW)

    later = NOW + timedelta(days=stats_cache.DEFAULT_TTL_DAYS, seconds=1)

    assert stats_cache.get(cache, KEY, now=later) is None


def test_missing_and_malformed_entries_are_ignored():
    cache = {
        "github.com/a/b": "not an entry",
        "github.com/c/d": ["only two", 1],
        "github.com/e/f": ["not a timestamp", 1, 2],
        "github.com/g/h": [True, 1, 2],
    }

    for key in cache:
        assert stats_cache.get(cache, key, now=NOW) is None
    assert stats_cache.get(cache, "github.com/unknown/repo", now=NOW) is None


def test_load_ignores_broken_or_missing_file(tmp_path):
    assert stats_cache.load(str(tmp_path / "does-not-exist.json")) == {}

    broken = tmp_path / "broken.json"
    broken.write_text("{not json")
    assert stats_cache.load(str(broken)) == {}

    not_a_mapping = tmp_path / "list.json"
    not_a_mapping.write_text("[1, 2, 3]")
    assert stats_cache.load(str(not_a_mapping)) == {}


def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "cache.json")
    cache = {}
    stats_cache.put(
        cache,
        "gitlab.com/group/project",
        {"repository_stars_count": 7, "repository_forks_count": None},
        now=NOW,
    )

    stats_cache.save(path, cache)

    assert stats_cache.get(
        stats_cache.load(path), "gitlab.com/group/project", now=NOW
    ) == {"repository_stars_count": 7, "repository_forks_count": None}
