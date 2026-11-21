# Build plan

Taken from [scope-v1.md](scope-v1.md). Work through one step at a time; tick each one off when it is done.

## Phase 0 — Setup
- [x] Repo, folder layout, Python env (uv)
- [x] Official dataset schema ([schema-official.md](schema-official.md))

## Phase 1 — Official baseline (weeks 1–2)
Done when: one CSV of national and regional deaths, injuries and crashes by year, 2018–2025.
- [x] 1a. Find and download the NBS/police reports for 2018–2025 into `data/raw/nbs/`, and record each URL in `data/raw/nbs/SOURCES.md`
- [ ] 1b. For each report, locate the road traffic tables (national totals, by region, by cause, by vehicle type)
- [ ] 1c. Extract the tables to CSV (pdfplumber; enter by hand if a table won't parse)
- [ ] 1d. Standardise region names; map police regions to administrative regions
- [ ] 1e. Add WHO/GBD estimated deaths for the years available
- [ ] 1f. Checks: regional values sum to the national total; flag jumps from one year to the next
- [ ] 1g. Write `data/processed/official.csv`

## Phase 2 — News agent (weeks 2–4)
Done when: 90% of fields are correct in a hand check of 50 random records.
- [ ] 2a. Collect: check which outlets have RSS feeds; add GDELT and Google News queries
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
