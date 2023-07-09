# fdroid-insights

[**F-Droid Insights**](https://dbeley.github.io/fdroid-insights) is a simple website that let you explore F-Droid apps enriched by data coming from external websites such as Github. It facilitates the discovery of popular and well-maintained projects which might be challenging to locate on the regular F-Droid website.

## Motivation

F-Droid is the best app store to find FOSS Android apps.

It allows thousands of independent developers to freely publish their apps and making them available to the general public.

Operating ssolely on donations to sustain their infrastructure, F-Droid offers an ad-free experience, without any premium features or sponsored apps.

They also don't track their users.
However, the lack of information regarding app metrics (download count, similar apps) represents a challenge when selecting among multiple options.

The idea behind **F-Droid Insights** is to leverage external metrics to help finding popular and well-maintained F-Droid apps.

## Usage

- Download `index-v2.json` from [F-Droid](https://f-droid.org/en/docs/All_our_APIs).
- `fdroid_data_exporter.py`: Create `export.csv` containing F-Droid apps data.
- `fdroid_html_builder.py`: Create `docs/index.html` with `export.csv` and `template.html`.

## External data

- Github: number of stars, forks
- Gitlab : number of stars, forks
- Codeberg : number of stars, forks
