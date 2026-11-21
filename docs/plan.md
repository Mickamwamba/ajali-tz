# Build plan

Taken from [scope-v1.md](scope-v1.md). Work through one step at a time; tick each one off when it is done.

## Phase 0 — Setup
- [x] Repo, folder layout, Python env (uv)
- [x] Official dataset schema ([schema-official.md](schema-official.md))

## Phase 1 — Official baseline (weeks 1–2) ✅
Done when: one CSV of national and regional deaths, injuries and crashes by year, 2018–2025.
- [x] 1a. Find and download the NBS/police reports for 2018–2025 into `data/raw/nbs/`, and record each URL in `data/raw/nbs/SOURCES.md`
- [x] 1b. For each report, locate the road traffic tables (national totals, by region, by cause, by vehicle type)
- [x] 1c. Extract the tables to CSV (pdfplumber; enter by hand if a table won't parse)
  - [x] National tables (Tanzania / Mainland / Zanzibar) → `data/interim/national_raw.csv` via `extract_national.py`
  - [x] Regional tables → `data/interim/regional_raw.csv` via `extract_regional.py` (2023 hand-entered in `manual/regional-2023.csv`)
  - [x] Motorcycle tables → `data/interim/motorcycle_raw.csv` via `extract_motorcycle.py`
  - [x] Causes tables → `data/interim/causes_raw.csv` via `extract_causes.py`
- [x] 1d. Standardise region names; map police regions to administrative regions (`region_map.csv`, `map_regions.py` → `data/interim/*_admin.csv`)
- [x] 1e. Add WHO/GBD estimated deaths for the years available (WHO 2018–2023 → `data/interim/estimates_raw.csv`; GBD deferred, needs an IHME account)
- [x] 1f. Checks: regional values sum to the national total; flag jumps from one year to the next
  - [x] Pick one value per year/metric from the duplicate sources
  - [x] Add deaths per 100,000 people by region (2022 census populations)
  - [x] Ratio of WHO estimate to official deaths per year
  - Results: `docs/checks-official.md`; data: `data/interim/official_checked.csv`
- [x] 1g. Write `data/processed/official.csv` (+ `official_national_summary.csv`, `README.md`; rebuild all: `bash pipeline/official/run_all.sh`)

## Phase 2 — News agent (weeks 2–4) ✅
Done when: 90% of fields are correct in a hand check of 50 random records.
- [x] 2a. Check which outlets can be collected (`pipeline/news/SOURCES.md`): Citizen + Mwananchi by RSS, Daily News + HabariLeo + Chanzo by WordPress search; IPP blocked; Millard Ayo down; GDELT rate-limited
- [x] 2a+. Collector (`pipeline/news/collect.py`): keyword pre-filter, retries, dedup by URL → `data/news/candidates.jsonl` (local, not committed). 12-month backfill of the 3 WordPress sites: 166 candidates
- [x] 2b. Filter (`pipeline/news/filter.py`, Claude Haiku 5.5): 166 backfill candidates → 35 relevant, 131 rejected; hand review found no wrong accepts and no clear misses. Cost $0.13 per 1,000 articles
- [x] 2c. Extract (`pipeline/news/extract.py`, Claude Haiku 5.5): 31 articles → 32 crash records; spot checks of 5 records all correct; no names recorded. $0.66 per 1,000 articles. 4 Chanzo articles waiting (site DNS failing)
  - Note for 2e: reports of one crash disagree on vehicle type (bus vs minibus) and cause, so match on date ± 2 days + region + overlapping vehicles, not identical vehicles
- [x] 2d. Geocode (`pipeline/news/geocode.py`): district gazetteer from OCHA boundaries (170 districts, `data/reference/`) + aliases + OpenStreetMap fallback. 28 of 32 crashes at district level, 4 at region level; ambiguous place names flagged for review
- [x] 2e. Deduplicate (`pipeline/news/dedupe.py`): date ±2 days + same region + overlapping vehicle families + same district; never merge two crashes from one article. 32 records → 24 crashes in `data/news/crashes.json`; keeps highest toll and every source link
- [x] 2f. Storage (file-based, chosen over Supabase for v1): `data/news/` state committed (summaries deleted after screening), review queue via `pipeline/news/review.py`, decisions in `data/news/review.json`, `publish.py` → `data/processed/news_crashes.csv/.json`. 24 crashes: 18 auto-approved, 6 waiting for review
- [x] 2g. GitHub Actions every 3 hours (`.github/workflows/news.yml`); a run with zero articles fails and GitHub emails the owner. Private repo; needs secret ANTHROPIC_API_KEY
- [x] 2h. Backfill 12 months (3 WordPress outlets); hand-check of all 45 extracted records: 360/360 fields correct (100%, target 90%). See `docs/accuracy-check-2h.md`

## Phase 3 — Dashboard (weeks 4–6)
Done when: the overview page loads in under 3 seconds on 3G.
- [x] 3a. Set up Observable Framework 1.13.4 in `site/` (`npm run dev` to preview, `npm run build` → `site/dist/`); data loaders in `site/src/data/` read `data/processed/` and `data/reference/`
- [x] 3b. Overview page (`site/src/index.md`): headline sentence (official figure first, then the WHO estimate), 3 headline numbers, police vs WHO chart with uncertainty band, table view; checked at desktop and phone widths
- [x] 3c. Map page (`site/src/map.md`): regional choropleth (per 100k or deaths/year, 2018–20 or 2023–25), news crash dots, click or choose a region for its yearly deaths and news crashes; table view
  - Follow-up: Zanzibar islands are tiny but have the highest rates; add an enlarged inset
- [x] 3d. Recent crashes page (`site/src/crashes.md`): search + region, vehicle and date filters, monthly deaths chart, one card per crash with all source links, CSV download; checked at desktop and phone widths
- [x] 3e. About the data page (`site/src/about.md`): three sources and what each misses, how official figures were prepared, known report problems, news method + accuracy + privacy, 3 CSV downloads, suggested citation, build date
- [x] 3f. Share buttons (`site/src/components/share.js`) on all 4 charts: PNG with title, source line and site name, in the reader's theme; phone share sheet or download
- [ ] 3g. Deploy as a static site and rebuild after each pipeline run
- [ ] 3h. Speed check: overview under 3 seconds on 3G

## Phase 4 — Soft launch (weeks 6–7)
- [ ] 3–5 journalists and NGOs test it; fix what confuses them

## Phase 5 — Public launch (week 8)
- [ ] Launch together with a story built on the data
