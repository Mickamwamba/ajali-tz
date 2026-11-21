# Official dataset schema — `data/processed/official.csv`

Long format: one row per (year, area, metric, breakdown, source). Long format lets police figures and WHO
estimates sit in the same file without mixing them up, and adding a new breakdown later only adds rows.

Built by `pipeline/official/build_official.py` (step 1f) from the files in `data/interim/`.

| Column | Type | Example | Notes |
| --- | --- | --- | --- |
| `year` | int | 2024 | Calendar year (Jan–Dec) |
| `area_level` | enum | `national`, `zone`, `region` | zone = Tanzania Mainland or Zanzibar |
| `area` | text | `Tanzania`, `Zanzibar`, `Morogoro` | Regions are the 31 administrative regions (see below) |
| `metric` | enum | `deaths` | See metrics below |
| `breakdown` | text | `total` | `total`, `vehicle:motorcycle`, or `cause:<cause>` |
| `value` | number | 1715 | |
| `value_low`, `value_high` | number | | 95% uncertainty range, WHO estimates and the ratio only |
| `source` | enum | `police_nbs`, `who`, `derived` | Shown on every chart |
| `source_doc` | text | `nbs-crime-traffic-2024.pdf` | File(s) in `data/raw/` |
| `source_table` | text | `Table 3.4` | Table in that document |
| `source_page` | int | 53 | PDF page (1-based), so the number can be checked |
| `notes` | text | | Known problems, derivations, caveats |

## Metrics

| Metric | Meaning |
| --- | --- |
| `crashes` | All reported road crashes ("Accidents" / "Matukio ya Ajali") |
| `fatal_crashes` | Crashes with at least one death |
| `injury_crashes` | Crashes with injuries but no deaths |
| `other_crashes` | Neither fatal nor injury ("Normal accidents" / "Ajali za Kawaida") |
| `deaths` | People killed. `source=police_nbs`: recorded by police. `source=who`: WHO estimate |
| `injuries` | People injured (police) |
| `deaths_per_100k` | Police deaths per 100,000 people, regions only, using the 2022 census population for every year |
| `deaths_rate_per_100k` | WHO estimated death rate per 100,000 (national) |
| `who_to_official_ratio` | WHO estimated deaths ÷ police deaths |

## Coverage and gaps

- Police national totals: 2018–2025. 2021 comes from the Statistical Abstract only, with no zone or region split.
- Regions: 2018–2020 and 2023–2025 (no regional tables were found for 2021 or 2022).
- Causes: Mainland only for 2018–2020; all Tanzania for 2022–2025. 2025 causes are marked suspect.
- WHO estimates: 2018–2023. 2021 is published by WHO; other years are derived from WHO's rate.

## Region names

Police reports use **police regions**. `pipeline/official/region_map.csv` maps them to the 26 Mainland
administrative regions plus the 5 Zanzibar regions (Ilala, Temeke, Kinondoni → Dar es Salaam;
Rufiji → Pwani; Tarime–Rorya → Mara). Police units without a region (Marine, Railway, TAZARA, Airports)
count in national totals only.
