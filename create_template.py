from string import Template
import pandas as pd

def read_template(file: str) -> Template:
    with open(file, "r") as f:
        content = f.read()
    return Template(content)

df = pd.read_csv("export_formatted.csv")
df = df.astype({"repository_stars_count": "Int64",
                "repository_forks_count": "Int64",
                "repository_subscribers_count": "Int64",
                "repository_watchers_count": "Int64"})

header = ""
# Export to html
for column_name in list(df.columns.values):
    header += f"<th>{column_name.replace('_', ' ').title()}</th>\n"

print(header)

table_data = ""
table_data += "<tbody>\n"
for index, row in df.iterrows():
    table_data += "<tr>\n"
    for column_name in list(df.columns.values):
        # print(row[column_name])
        table_data += f"<td>{row[column_name]}</td>"
    table_data += "</tr>\n"


formatted_message = read_template("datatables-template/dist/template.html").safe_substitute({"header": header, "table_data": table_data})
with open(f"datatables-template/dist/index.html", "w") as f:
    f.write(formatted_message)
