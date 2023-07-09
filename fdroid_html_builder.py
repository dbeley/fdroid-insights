from string import Template
import pandas as pd


def read_template(file: str) -> Template:
    with open(file, "r") as f:
        content = f.read()
    return Template(content)


df = pd.read_csv("export.csv")
df = df.astype(
    {
        "repository_stars_count": "Int64",
        "repository_forks_count": "Int64",
        "repository_subscribers_count": "Int64",
        "repository_watchers_count": "Int64",
    }
)
df = df.fillna(0)

header = (
    "<th>Name</th>"
    "<th>Repository</th>"
    "<th>Repository Stars Count</th>"
    "<th>Repository Forks Count</th>"
    "<th>Repository Subscribers Count</th>"
    "<th>Repository Watchers Count</th>"
    "<th>Repository Domain</th>"
    "<th>Summary</th>"
    "<th>Categories</th>"
    "<th>Added</th>"
    "<th>Last Updated</th>"
)

table_data = ""
table_data += "<tbody>\n"
for index, row in df.iterrows():
    repository = row["repository"]
    icon = row["icon"]
    url = row["url"]
    name_with_icon = (
        # f"<td><img src='{icon}' width='32' alt='{icon}'> <a href='{url}'>{row['name']}</a></td>"
        # if icon
        f"<td><a href='{url}'>{row['name']}</a></td>"
    )
    table_data += (
        "<tr>\n"
        f"{name_with_icon}"
        "\n"
        f"<td><a href='{repository}'>{repository}</a></td>"
        "\n"
        f"<td>{row['repository_stars_count']}</td>"
        "\n"
        f"<td>{row['repository_forks_count']}</td>"
        "\n"
        f"<td>{row['repository_subscribers_count']}</td>"
        "\n"
        f"<td>{row['repository_watchers_count']}</td>"
        "\n"
        f"<td>{row['repository_domain']}</td>"
        "\n"
        f"<td>{row['summary']}</td>"
        "\n"
        f"<td>{row['categories']}</td>"
        "\n"
        f"<td>{row['added']}</td>"
        "\n"
        f"<td>{row['last_updated']}</td>"
        "\n"
        "</tr>\n"
    )


formatted_message = read_template("template.html").safe_substitute(
    {"header": header, "table_data": table_data}
)
with open("docs/index.html", "w") as f:
    f.write(formatted_message)
