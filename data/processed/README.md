# Tanzania road crash data: official figures and WHO estimates

Two files. Both are free to use; please cite the original sources listed in each row.

## `official_national_summary.csv`: start here

One row per year, 2018–2025: police-recorded crashes, deaths and injuries, the WHO estimate of
true road deaths (with its 95% range), and how many times larger the WHO estimate is.

**Suggested citation:** "Police recorded 1,368 road deaths in 2021 (NBS Statistical Abstract 2022). WHO
estimates the true number at 10,052 (WHO Global status report on road safety 2023), about 7 times higher."

## `official.csv`: everything

The full dataset in long format: one row per year, area, measure and source. It includes:

- national, Mainland and Zanzibar totals
- the 31 administrative regions, including deaths per 100,000 people and 3-year averages
- motorcycle (bodaboda) crashes, deaths and injuries
- reported causes of crashes
- WHO estimates

Every row names its source document, table and page, so any number can be checked against the original.
Column and measure definitions: [docs/schema-official.md](../../docs/schema-official.md).

## Read before using

- **Police figures count only what police recorded.** WHO estimates the true number of road deaths is
  roughly 5–7 times higher.
- **2021** has national police totals only (from the NBS Statistical Abstract). There are no regional figures for 2021 or 2022.
- **Regions** are compared fairly using `deaths_per_100k` (2022 census population). Use the 3-year
  averages (`*_avg_3yr`) for maps: single-year regional numbers are small and swing a lot.
  High rates in Zanzibar may partly reflect more complete recording there.
- **Causes** cover Mainland only for 2018–2020 and all Tanzania from 2022. **2025 causes are marked
  suspect**: their pattern differs sharply from earlier years and has not been confirmed.
- **WHO figures** other than 2021 are derived from WHO's published rate per 100,000; 2022–2023 are WHO
  projections with wide uncertainty. There are no WHO estimates for 2024–2025 yet.

Every check that was run, and what it found: [docs/checks-official.md](../../docs/checks-official.md).

## Sources

- Tanzania Police Force / National Bureau of Statistics, *Crime and Traffic Incidents Statistics* reports, 2018–2025, and *Statistical Abstract 2022*
- World Health Organization, Global Health Observatory and *Global status report on road safety 2023*
- National Bureau of Statistics, *2022 Population and Housing Census, Initial Results*
- World Bank, population (SP.POP.TOTL), used only to scale WHO rates between years
