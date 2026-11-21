---
title: About the data
toc: true
---

<style>
.lede { font-size: 1.1rem; max-width: 46rem; }
.tag { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--theme-foreground-faintest); color: var(--theme-foreground-muted); white-space: nowrap; }
.downloads { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin: 1rem 0; }
.downloads .card { margin: 0; display: flex; flex-direction: column; gap: 0.35rem; }
.downloads .card a { font-weight: 600; }
.downloads .card span { color: var(--theme-foreground-muted); font-size: 0.85rem; }
.cite { font-family: var(--monospace); font-size: 0.85rem; padding: 0.75rem 1rem; border-left: 3px solid var(--theme-foreground-faint); background: var(--theme-background-alt); max-width: 46rem; }
.updated { color: var(--theme-foreground-muted); font-size: 0.85rem; }
</style>

```js
const info = FileAttachment("data/build_info.json").json();
```

# About the data

<p class="lede">This dashboard puts three kinds of numbers side by side. Each does a different job, and every figure on the site says which one it comes from.</p>

<p class="updated">Site last rebuilt ${new Date(info.built).toUTCString().replace(" GMT", " UTC")}. News log: ${info.news_crashes} published crashes, ${info.news_first} to ${info.news_last}.</p>

## Three sources, three jobs

| Source | What it gives | Years | Used for |
| --- | --- | --- | --- |
| **Tanzania Police Force / National Bureau of Statistics** | Crashes, deaths and injuries recorded by police, nationally and by police region, by cause and for motorcycles | 2018–2025 | The official trend and the map |
| **World Health Organization** | A modelled estimate of the true number of road deaths | 2018–2023 | The "estimated real toll" comparison |
| **News reports** <span class="tag">reported in the media</span> | Individual crashes: date, place, vehicles, deaths, injuries, source links | December 2025 onward | The recent-crash list and the dots on the map |

## What each source misses

**Police figures count only what police recorded.** Deaths that never reach a police report, such as a victim who dies later in hospital or a crash in a remote area, are missing. WHO estimates that the true number of road deaths in Tanzania is roughly 5 to 7 times the police count. The gap is not new: for 2013 the ministry reported 4,002 deaths and WHO estimated about 16,000 ([Pulitzer Center](https://pulitzercenter.org/stories/tanzania-where-are-missing-bodies)).

**WHO figures are estimates, not counts.** WHO builds them from many sources with a statistical model, and gives a range (the shaded band on the overview chart). WHO published a count for 2021: 10,052 deaths, with a 95% range of 8,246 to 11,858. For other years we multiply WHO's published death rate per 100,000 people by the population; this method reproduces WHO's 2021 count to within 5 deaths. 2022 and 2023 are WHO projections with wider uncertainty, and there is no WHO estimate yet for 2024 or 2025.

**News reports are a small, uneven slice.** The news covers mostly large crashes, crashes near cities, and crashes involving officials. A month with more news coverage is not necessarily a month with more crashes. News counts are always labelled "reported in the media" and are never presented as a total.

## How the official figures were prepared

- **Source documents.** The police's annual *Crime and Traffic Incidents Statistics* reports for 2018–2020 and 2023–2025, published by the [National Bureau of Statistics](https://www.nbs.go.tz/statistics/topic/crime-statistics). The 2021 and 2022 reports are not online; national totals for those years come from the NBS *Statistical Abstract 2022* (Table 16.2), and there are no regional figures for 2021 or 2022.
- **Checks.** Each year appears in two reports (its own, and the next year's comparison column); every such pair matches. Regions add up to the national totals. The few inconsistencies printed in the reports themselves are listed below.
- **Regions.** Police use police regions. We merge them into the 31 administrative regions: Ilala, Temeke and Kinondoni into Dar es Salaam; Rufiji into Pwani; Tarime–Rorya into Mara. Specialist police units (Marine, Railway, TAZARA, Airports) count in the national totals only.
- **Rates.** Deaths per 100,000 people use the 2022 census population ([NBS](https://www.nbs.go.tz/uploads/statistics/documents/en-1720088450-2022%20PHC%20Initial%20Results%20-%20English.pdf)) for every year, so compare regions within a period rather than one region across periods. The map uses three-year averages because yearly regional numbers are small.
- **Zanzibar.** Zanzibar's regions show the highest recorded death rates. That may partly reflect more complete recording there rather than more dangerous roads.

### Known problems in the reports themselves

- **Causes of crashes:** the tables are labelled "Mainland" every year, but from 2022 their totals match all of Tanzania. We label them accordingly.
- **2025 causes look unreliable:** compared with 2024, "careless passengers" jumps from 0 to 226 and "over speeding" falls from 291 to 5. The 2025 report's own 2024 column matches the 2024 report, so this is not a reading error. These figures are marked unconfirmed.
- **Motorcycle injuries, 2018:** printed as 570, but Mainland (595) plus Zanzibar (39) and the regional table give 634.
- **Small gaps of 1 to 5** between Mainland and Zanzibar splits in different tables of the same report (2018, 2023, 2025). National totals agree.

## How the news crash log is made

An automated process runs every three hours:

1. **Collect** new articles from The Citizen, Mwananchi, Daily News, HabariLeo and The Chanzo, keeping those whose headline mentions a road word in English or Swahili.
2. **Screen**: an AI model (Claude) reads the headline and summary and decides whether the article reports a specific road crash in Tanzania. Boat and train accidents, crashes abroad, and yearly totals are set aside.
3. **Extract**: the AI reads the full article and fills in date, region, district, place, vehicles, deaths, injuries, victim types and reported cause. It records only what the article states, never guesses numbers, and never records names.
4. **Place** each crash in a district, using official district boundaries and OpenStreetMap. Map points are district centres, never exact crash locations.
5. **Merge** reports of the same crash (same region, dates within two days, matching vehicles), keeping the highest reported toll and a link to every article.
6. **Review**: records the process is unsure about wait for a person to check before they are published.

**Accuracy.** In a hand check of all 45 records extracted so far, each compared field by field with its article, 360 out of 360 fields were correct. That does not mean the process is never wrong; check the linked articles before quoting a single record.

**Copyright and privacy.** Article text is read once and not stored. The site keeps only facts and links back to the original reporting, and never stores or shows names or photos of victims.

## Download the data

<div class="downloads">
  <div class="card">
    <a href="./data/official_national_summary.csv" download="ajali-tz-national-summary.csv">National summary (CSV)</a>
    <span>One row per year, 2018–2025: police crashes, deaths and injuries; WHO estimate and range; the ratio. Start here.</span>
  </div>
  <div class="card">
    <a href="./data/official.csv" download="ajali-tz-official.csv">Full official dataset (CSV)</a>
    <span>Every figure: national, Mainland/Zanzibar, 31 regions, motorcycles, causes, WHO, rates, 3-year averages. Each row names its source report, table and page.</span>
  </div>
  <div class="card">
    <a href="./data/news_crashes.csv" download="ajali-tz-news-crashes.csv">News-reported crashes (CSV)</a>
    <span>One row per crash: date, region, district, vehicles, deaths, injuries, cause, source links. <span class="tag">reported in the media</span></span>
  </div>
</div>

Free to use. Please cite the original sources named in each file.

### Suggested citation

<div class="cite">Police recorded 1,368 road deaths in Tanzania in 2021 (NBS Statistical Abstract 2022). The World Health Organization estimates the true number at 10,052 (WHO Global status report on road safety 2023), about 7 times higher. Compiled by Ajali TZ.</div>

## Sources

- Tanzania Police Force / National Bureau of Statistics, [*Crime and Traffic Incidents Statistics*](https://www.nbs.go.tz/statistics/topic/crime-statistics), annual reports 2018–2025, and *Statistical Abstract 2022*.
- World Health Organization, [Global status report on road safety 2023: Tanzania profile](https://cdn.who.int/media/docs/default-source/country-profiles/road-safety/road-safety-2023-tza.pdf) and the [Global Health Observatory](https://www.who.int/data/gho).
- National Bureau of Statistics, *2022 Population and Housing Census, Initial Results*.
- World Bank, population (SP.POP.TOTL), used only to scale WHO rates between years.
- Administrative boundaries: NBS / UN OCHA, 2018, via the [Humanitarian Data Exchange](https://data.humdata.org/dataset/cod-ab-tza).
- News: [The Citizen](https://www.thecitizen.co.tz), [Mwananchi](https://www.mwananchi.co.tz), [Daily News](https://dailynews.co.tz), [HabariLeo](https://habarileo.co.tz), [The Chanzo](https://thechanzo.com).
