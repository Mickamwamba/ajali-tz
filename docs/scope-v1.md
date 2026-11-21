# Tanzania Road Crash Dashboard — Project Scope (v1)

Nov 21, 2026 · @Michael

## Purpose

Version 1 is a public dashboard that shows how many people die and are injured on Tanzania's roads, where, and how much official figures may undercount it. It is built by one person on a low budget.

**Problem.** Road crashes kill well over 1,000 Tanzanians a year by official count. Coverage in the news is scattered across single incidents, so the total scale rarely gets attention. Official police figures and WHO estimates have historically differed by several times. In 2013, for example, the ministry reported 4,002 deaths and WHO estimated about 16,000 ([Pulitzer Center](https://pulitzercenter.org/stories/tanzania-where-are-missing-bodies)).

**Goal.** Put three views in one place: the official trend, an estimate of the true toll, and a running log of individual crashes found in the news.

## Scope

Version 1 covers road crashes only, nationally (mainland and Zanzibar), using three data sources.

| Area | In scope for v1 | Out of scope (later) |
| --- | --- | --- |
| Accident types | Road crashes of every vehicle type: bodaboda, bajaji, car, bus, truck, pedestrian | Marine/ferry, mining, fire, workplace, rail |
| Geography | Mainland by region, plus Zanzibar | Street-level hotspot maps with exact coordinates |
| History | Official figures 2018–2025, news records from launch onward (plus a backfill of about 12 months) | Records from before 2018 |
| Data sources | Police/NBS reports, WHO/GBD estimates, news articles | Crowdsourced reports, hospital data, insurers, police RAIS access |
| Languages | English and Swahili sources; English dashboard | Swahili dashboard (strong candidate for v2) |
| Features | Public dashboard, methodology page, CSV download | Alerts, user accounts, mobile app, public API |

## Audience and key questions

The main audience is the public and journalists. Every chart should be easy to read on a phone and easy to share.

The dashboard must answer these questions:

1. How many people die and are injured on Tanzania's roads each year, and is the number going up or down?
2. How big might the real toll be compared with what is officially reported?
3. Which regions and roads have the most crashes?
4. Which road users are most affected: bodaboda riders, bus passengers or pedestrians?
5. What crashes happened recently, and where can I read about them?
6. What causes are most often reported?

Journalists also need a story-ready number with its source, plus a CSV they can cite.

## Data sources

The three sources do different jobs, and the dashboard always labels which one a number comes from.

| Source | What it gives | Format and update | Job on the dashboard |
| --- | --- | --- | --- |
| [Police/NBS Crime and Traffic Incidents Statistics](https://www.nbs.go.tz/uploads/statistics/documents/en-1774441493-CRIME%20STATISTICS%20REPORT%20ENGLISH%202025.pdf) | Crashes, deaths and injuries by region, cause and vehicle type | PDF; half-yearly and annual reports | Official trend from 2018 onward |
| [WHO road safety country profile](https://cdn.who.int/media/docs/default-source/country-profiles/road-safety/road-safety-2023-tza.pdf) and the GBD study | Modelled estimate of true road deaths | PDF and data portals; every few years | "Estimated real toll" comparison |
| News: The Citizen, Daily News, Mwananchi, HabariLeo, The Guardian/IPP, The Chanzo, Millard Ayo | Individual crashes with date, place, vehicles and casualties | Web and RSS; daily | Recent-crash log, map, vehicle mix |
| Zanzibar Road Safety Board | Zanzibar figures, which may be reported separately | Press releases | Fills the Zanzibar gap |

News coverage favours large and urban crashes, so news counts are labelled "reported in the media" and never presented as the total.

## News agent pipeline

Once a day, a scheduled job turns news articles into clean crash records.

1. **Collect.** Pull new articles from RSS feeds, Google News and GDELT, searching for terms such as "ajali", "ajali ya barabarani", "road accident", "bodaboda" and "basi".
2. **Filter.** A cheap AI call asks one question: is this article about a specific road crash in Tanzania? Anything else is dropped.
3. **Extract.** An AI model fills in the fields below as JSON. It works for both English and Swahili articles.
4. **Geocode.** Match the place name to a region and district using a fixed gazetteer, with coordinates where possible.
5. **Deduplicate.** Merge reports of the same crash by date (within 2 days), region and vehicle types. Keep the highest confirmed death toll and list every source.
6. **Review.** Records with low confidence go into a review queue that you check weekly.
7. **Publish.** Approved records appear on the dashboard.

Each crash record has these fields:

| Field | Example |
| --- | --- |
| crash\_date | 2026-11-14 |
| region, district, road/place | Morogoro, Gairo, Morogoro–Dodoma highway |
| vehicles\_involved | bus; truck |
| deaths, injuries | 12, 30 |
| victim\_types | passengers; pedestrian |
| reported\_cause | overtaking |
| source\_urls | links to every article |
| confidence, review\_status | 0.86, approved |

Article text is not stored. Only the extracted facts and links are kept, and victims' names are never recorded.

## Dashboard pages

Version 1 has four pages, and the first one should make the point within five seconds.

1. **Overview.** Headline numbers: official deaths last year, the WHO-estimated toll, and crashes reported in the media in the last 30 days. Also a trend line for 2018 to now, and a chart comparing official and estimated deaths.
2. **Map.** Crashes and deaths by region, shown as a choropleth map. Clicking a region shows its trend and recent crashes.
3. **Recent crashes.** A searchable list of news-reported crashes with date, place, vehicles, deaths and source links. Filters for region, vehicle type and date.
4. **About the data.** Where each number comes from, what it misses, how the AI extraction works, and a CSV download.

Every chart gets a share button that creates an image with the source line included, for use on social media.

## Tech stack and budget

Everything runs on free tiers except the AI calls, so the rough running cost is under about $20 a month. These are estimates and should be checked against current pricing.

| Part | Choice | Approx. cost / month |
| --- | --- | --- |
| Pipeline code | Python scripts (feedparser, trafilatura for article text) | $0 |
| Scheduler | GitHub Actions, daily cron | $0 (free tier) |
| Database | Supabase Postgres + PostGIS | $0 (free tier) |
| AI filter + extraction | A small, cheap model such as Claude Haiku, roughly 100–200 articles a day | about $5–15 |
| Geocoding | Fixed gazetteer of regions and districts; OpenStreetMap Nominatim as fallback | $0 |
| Review queue | Simple admin page, or a Supabase table view | $0 |
| Dashboard | Static site (Observable Framework or Next.js) on Vercel, Netlify or GitHub Pages | $0 |
| Domain | e.g. ajalitz.org | about $1–2 (about $15/yr) |

The dashboard should be a static site rebuilt daily. A static site costs nothing to host and stays up if a story goes viral.

## Phased plan

At part-time pace, a public version 1 takes about 8 weeks. Each phase ends with something usable.

1. **Weeks 1–2: Official baseline.** Extract the 2018–2025 police/NBS tables and WHO/GBD estimates into a clean dataset. *Done when:* one CSV of national and regional deaths, injuries and crashes by year.
2. **Weeks 2–4: News agent.** Build the collect, filter, extract, geocode and deduplicate steps for 5–6 outlets, then backfill 12 months. *Done when:* hand-checking 50 random records finds at least 90% of fields correct.
3. **Weeks 4–6: Dashboard.** Build the four pages on the static site. *Done when:* the overview page loads in under 3 seconds on a phone with 3G.
4. **Weeks 6–7: Review and soft launch.** Share with 3–5 journalists and road safety NGOs, then fix what confuses them.
5. **Week 8: Public launch.** Pair the launch with a story built on the data, such as "What the official numbers miss".

After launch, plan on about 1–2 hours a week for the review queue and fixing scrapers when outlets change their websites.

## Risks and mitigations

The biggest risk is that people misread news counts as the total, so every page labels each number with its source.

| Risk | Mitigation |
| --- | --- |
| News undercounts rural and single-victim crashes | Label figures "reported in the media"; show them next to official figures and estimates |
| The same crash is counted twice | Deduplication rules, a review queue, and source links on every record |
| AI misreads a death toll or place | Confidence scores; anything uncertain is reviewed by a person; monthly spot checks |
| Copyright or site terms on news sites | Store only facts and links, never article text; respect robots.txt; check each outlet's terms |
| Victims' privacy | Never store or show names or photos |
| Data seen as criticising the government | Use neutral wording, cite official figures first, and publish the method openly |
| Websites change and scrapers break | Prefer RSS and GDELT; send yourself an alert when a day brings zero articles |
| Solo maintainer burnout | Keep version 1 small; automate everything except the weekly review |

## Success measures

Three months after launch, version 1 counts as working if:

- At least 3 news stories cite the dashboard or its data
- The news pipeline catches at least 80% of the fatal crashes covered by the main outlets (checked against a manual sample)
- At least 1 road safety organisation or researcher uses the CSV
- Upkeep stays under 2 hours a week

## Open questions

- [ ] Project name and domain (Swahili, English or both?)
- [ ] Should the dashboard be in English only, or bilingual from day one?
- [ ] Which 5–6 news outlets have usable RSS feeds? Needs checking.
- [ ] Is the WHO or GBD estimate the better "true toll" figure, and for which years is it available?
- [ ] Who are the first 3–5 journalists or NGOs to test it with?

## Sources

- [Police/NBS Crime and Traffic Incidents Statistics, Jan–Dec 2025](https://www.nbs.go.tz/uploads/statistics/documents/en-1774441493-CRIME%20STATISTICS%20REPORT%20ENGLISH%202025.pdf)
- [WHO road safety country profile: Tanzania, 2023](https://cdn.who.int/media/docs/default-source/country-profiles/road-safety/road-safety-2023-tza.pdf)
- [Pulitzer Center: Tanzania, where are the missing bodies?](https://pulitzercenter.org/stories/tanzania-where-are-missing-bodies)
- [World Bank: Trauma Incidence and Care in Tanzania](https://openknowledge.worldbank.org/entities/publication/99be0495-cd50-5657-bdeb-ca8a87699f8f)
