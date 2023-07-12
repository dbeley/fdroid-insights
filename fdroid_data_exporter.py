import os
import json
import logging
import pandas as pd
from github import Github
from gitlab import Gitlab
from utils import get_github_repository_data
from utils import get_gitlab_repository_data
from utils import get_codeberg_repository_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s :: %(message)s")
logger = logging.getLogger(__name__)

REPOSITORY_APIS = {
    "github.com": Github(os.environ.get("GITHUB_TOKEN")),
    "gitlab.com": Gitlab(private_token=os.environ.get("GILAB_TOKEN")),
    "invent.kde.org": Gitlab(
        url="https://invent.kde.org", private_token=os.environ.get("GILAB_KDE_TOKEN")
    ),
}


def _extract_repository_name(repository: str, repository_domain: str) -> str:
    repository_name = (
        repository.split("://")[-1].split(f"{repository_domain}/")[-1].strip("/")
    )
    if repository_name.count("/") > 1:
        repository_name = (
            repository_name.split("/")[0] + "/" + repository_name.split("/")[1]
        )
    return repository_name


def _get_repository_stats(repository: str, repository_domain: str) -> dict[str, str]:
    if not repository:
        return {}
    repository_name = _extract_repository_name(repository, repository_domain)
    match repository_domain:
        case "github.com":
            return get_github_repository_data(
                REPOSITORY_APIS["github.com"], repository_name
            )
        case "codeberg.org":
            return get_codeberg_repository_data(repository_name)
        case "gitlab.com":
            return get_gitlab_repository_data(
                REPOSITORY_APIS["gitlab.com"], repository_name
            )
        case "invent.kde.org":
            return get_gitlab_repository_data(
                REPOSITORY_APIS["invent.kde.org"], repository_name
            )
    return {}


with open("index-v2.json", "rb") as f:
    json_object = json.load(f)

# two parent objects: repo and packages
# repo object: name, description, icon, address, mirrors, timestamp, antiFeatures, categories, releaseChannels
# packages object: name of all the apps (4137+)

list_data = []
json_items = json_object["packages"].items()
logger.info("Fetching data for %s apps...", len(json_items))
for index, (app_name, app_raw_data) in enumerate(json_items, 1):
    logger.info(
        "[%s/%s] Fetching data for %s",
        str(index).zfill(len(str(len(json_items)))),
        len(json_items),
        app_name,
    )
    metadata = app_raw_data["metadata"]
    repository = metadata.get("sourceCode", "")
    repository_domain = repository.split("://")[1].split("/")[0] if repository else ""
    repository_stats = _get_repository_stats(repository, repository_domain)
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
    }
)
df = df.sort_values(by=["name"])
df.to_csv("export.csv", index=False)
