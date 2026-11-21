# WHO estimate source files

Downloaded 2026-11-21.

| File | What | URL |
| --- | --- | --- |
| who-road-safety-profile-2023-tza.pdf | WHO Global status report on road safety 2023, Tanzania profile. 2021: reported 1,368 deaths; WHO estimate 10,052 (95% CI 8,246–11,858); rate 15.8 per 100k; population 63,588,334 | https://cdn.who.int/media/docs/default-source/country-profiles/road-safety/road-safety-2023-tza.pdf |
| who-gho-RS_196-tza.json | WHO GHO: estimated number of road traffic deaths (2021 only) | `https://ghoapi.azureedge.net/api/RS_196?$filter=SpatialDim eq 'TZA'` |
| who-gho-RS_198-tza.json | WHO GHO: estimated road traffic death rate per 100k, 2000–2023, by sex, with 95% range | `https://ghoapi.azureedge.net/api/RS_198?$filter=SpatialDim eq 'TZA'` |
| worldbank-population-tza.json | World Bank SP.POP.TOTL, 2016–2025 (last updated 2026-11-11). Used only for population growth between years | `https://api.worldbank.org/v2/country/TZA/indicator/SP.POP.TOTL?format=json&date=2016:2025` |

## Method and limits

- Counts for years other than 2021 are **derived**: WHO rate × population. See `pipeline/official/extract_estimates.py`.
- 2022 and 2023 are WHO model projections past the latest report year; their uncertainty ranges are about twice as wide.
- No WHO estimate exists yet for 2024–2025.
- WHO estimates are national only: no regional, Mainland/Zanzibar or road-user split.

## GBD (not used yet)

The IHME Global Burden of Disease estimates need a free IHME account to download
(GBD Results Tool, https://vizhub.healthdata.org/gbd-results/), so they can't be fetched automatically.
WHO is the primary "estimated toll" figure for v1; GBD can be added later as a cross-check.
