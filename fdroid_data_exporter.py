import os
import json
import time
import calendar
import pandas as pd
from github import Github
from github.GithubException import UnknownObjectException
from github.GithubException import RateLimitExceededException
from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError


def _extract_repository_name(repository: str, repository_domain: str) -> str:
    repository_name = (
        repository.split("://")[-1].split(f"{repository_domain}/")[-1].strip("/")
    )
    if repository_name.count("/") > 1:
        repository_name = (
            repository_name.split("/")[0] + "/" + repository_name.split("/")[1]
        )
    return repository_name


def _get_repository_stats(
    g: Github, gl: Gitlab, repository: str, repository_domain: str
) -> dict[str, str]:
    if not repository:
        return {}
    repository_name = _extract_repository_name(repository, repository_domain)

    if repository_domain == "github.com":
        try:
            repo = g.get_repo(repository_name)
        except UnknownObjectException:
            print(f"Repository {repository_name} was not found on Github.")
            return {}
        except RateLimitExceededException:
            core_rate_limit = g.get_rate_limit().core
            reset_timestamp = calendar.timegm(core_rate_limit.reset.timetuple())
            sleep_time = reset_timestamp - calendar.timegm(time.gmtime()) + 10
            print(f"Rate-limit detected, sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)
            repo = g.get_repo(repository_name)
        return {
            "repository_stars_count": repo.stargazers_count,
            "repository_forks_count": repo.forks_count,
            "repository_subscribers_count": repo.subscribers_count,
            "repository_watchers_count": repo.watchers_count,
        }
    elif repository_domain == "gitlab.com":
        try:
            repo = gl.projects.get(repository_name)
        except GitlabGetError:
            print(f"Repository {repository_name} was not found on Gitlab.")
            return {}
        return {
            "repository_stars_count": repo.star_count,
            "repository_forks_count": repo.forks_count,
        }

    return {}


g = Github(os.environ.get("GITHUB_TOKEN"))
gl = Gitlab(private_token=os.environ.get("GILAB_TOKEN"))

with open("index-v2.json", "rb") as f:
    json_object = json.load(f)

# two parent objects: repo and packages
# repo object: name, description, icon, address, mirrors, timestamp, antiFeatures, categories, releaseChannels
# packages object: name of all the apps (4137+)

list_data = []
for app_name, app_raw_data in json_object["packages"].items():
    metadata = app_raw_data["metadata"]
    repository = metadata.get("sourceCode", "")
    repository_domain = repository.split("://")[1].split("/")[0] if repository else ""
    repository_stats = _get_repository_stats(g, gl, repository, repository_domain)
    summary_en = metadata["summary"].get("en-US", "") if "summary" in metadata else ""
    description_en = (
        metadata["description"].get("en-US", "") if "description" in metadata else ""
    )
    icon_url = metadata["icon"].get("en-US", "") if "icon" in metadata else ""
    if icon_url:
        icon_url = f"https://f-droid.org/repo{icon_url['name']}"

    list_data.append(
        {
            "name": metadata["name"]["en-US"],
            "icon": icon_url,
            "id": app_name,
            "repository": repository,
            **repository_stats,
            "repository_domain": repository_domain,
            "summary": summary_en,
            # 'description': description_en,
            "categories": metadata["categories"],
            "added": metadata["added"],
            "last_updated": metadata["lastUpdated"],
            "url": f"https://f-droid.org/en/packages/{app_name}",
        }
    )

df = pd.DataFrame.from_records(list_data)
df = df.astype(
    {
        "repository_stars_count": "Int64",
        "repository_forks_count": "Int64",
        "repository_subscribers_count": "Int64",
        "repository_watchers_count": "Int64",
    }
)
df = df.sort_values(by=["name"])
df.to_csv("export.csv", index=False)
