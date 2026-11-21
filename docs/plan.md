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

## Phase 2 — News agent (weeks 2–4)
Done when: 90% of fields are correct in a hand check of 50 random records.
- [x] 2a. Check which outlets can be collected (`pipeline/news/SOURCES.md`): Citizen + Mwananchi by RSS, Daily News + HabariLeo + Chanzo by WordPress search; IPP blocked; Millard Ayo down; GDELT rate-limited
- [x] 2a+. Collector (`pipeline/news/collect.py`): keyword pre-filter, retries, dedup by URL → `data/news/candidates.jsonl` (local, not committed). 12-month backfill of the 3 WordPress sites: 166 candidates
- [ ] 2b. Filter: a cheap AI call answers "is this a specific road crash in Tanzania?"
- [ ] 2c. Extract: AI returns the crash record as JSON (English and Swahili)
- [ ] 2d. Geocode: match place names against a region/district gazetteer
- [ ] 2e. Deduplicate: same date ±2 days, same region, same vehicle types
- [ ] 2f. Storage: Supabase table plus review queue
- [ ] 2g. Daily GitHub Actions cron; alert when a day brings zero articles
- [ ] 2h. Backfill 12 months; hand-check 50 records

## Phase 3 — Dashboard (weeks 4–6)
Done when: the overview page loads in under 3 seconds on 3G.
- [ ] Overview · Map · Recent crashes · About + CSV download · share-image buttons

## Phase 4 — Soft launch (weeks 6–7)
- [ ] 3–5 journalists and NGOs test it; fix what confuses them

## Phase 5 — Public launch (week 8)
- [ ] Launch together with a story built on the data
