---
title: Tanzania road deaths
---

# Tanzania road deaths

```js
const summary = FileAttachment("data/official_national_summary.csv").csv({typed: true});
const crashes = FileAttachment("data/news_crashes.json").json();
const regions = FileAttachment("data/tz_regions.json").json();
```

Setup check (step 3a): the site can read every data file.

```js
display(Inputs.table(summary));
display(html`<p>${crashes.length} news-reported crashes · ${regions.features.length} regions in the map file</p>`);
```
