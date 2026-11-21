# Official dataset schema — `data/processed/official.csv`

Long format: one row per (year, area, metric, source). Long format lets police figures and WHO/GBD
estimates sit in the same file without mixing them up, and adding a new breakdown later
(by cause, by vehicle) only adds rows, not columns.

| Column | Type | Example | Notes |
| --- | --- | --- | --- |
| `year` | int | 2024 | Calendar year (Jan–Dec) |
| `area_level` | enum | `national`, `region` | |
| `area` | text | `Tanzania`, `Morogoro` | Standardised administrative region name (see below) |
| `metric` | enum | `crashes`, `deaths`, `injuries` | |
| `breakdown` | text | `total` | Later: `cause:overspeeding`, `vehicle:motorcycle`, … |
| `value` | number | 1715 | WHO/GBD estimates may be non-integer |
| `value_low`, `value_high` | number | | Uncertainty range, for estimates only |
| `source` | enum | `police_nbs`, `who`, `gbd` | Shown on every chart |
| `source_doc` | text | `nbs-crime-traffic-2024.pdf` | File in `data/raw/` |
| `source_page` | int | 42 | Page the number came from, so it can be checked |
| `notes` | text | | e.g. "Zanzibar not included" |

## Region names

Police reports use **police regions**, which are not the same as the administrative regions.
For example, Dar es Salaam is split into Kinondoni, Ilala, Temeke, Ubungo and Kigamboni, and some
reports list Tarime/Rorya or a Railway police region separately. Raw names are kept in the
extraction step, then mapped to the 26 mainland administrative regions plus Zanzibar using a
lookup table (`pipeline/official/region_map.csv`, written in step 1d).
