# Road traffic tables in the police/NBS reports

`table_index.csv` lists every road table to extract: report, table number, PDF page (1-based page in the
file, not the printed page number), what it holds, and whether the text can be read directly or needs OCR.

## The same tables appear every year

| Kind (`content`) | Swahili heading (2018–2020) | English heading (2023–2025) | Use on the dashboard |
| --- | --- | --- | --- |
| `national` | Idadi ya Ajali, Vifo, Majeruhi (Tanzania / Bara / Zanzibar) | Number of Road Traffic Accidents, Deaths and Injured Persons | Headline trend |
| `regional` | Matukio ya Usalama Barabarani kwa Mikoa ya Kipolisi | Traffic Offences … by Police Region | Map |
| `motorcycle` / `motorcycle_regional` | Ajali za Pikipiki, Vifo na Majeruhi | Motorcycle Accidents, Deaths and Injured Persons | Bodaboda view |
| `causes` | Idadi ya Ajali kwa Vyanzo Vyake | Number of Accidents by Cause | Causes chart (Mainland only) |
| `trend` | Makosa … Ajali Zilizosababisha Vifo … 2009/2010–20xx | Statistical Abstract Table 16.2 | Cross-check across years |

Each `national` table also gives the previous year, so 2022 comes from the 2023 report and every
year can be checked against two sources.

## Things to know before extracting (step 1c)

- **Regional tables split deaths and injuries by sex** (M/F columns). Regional deaths = M + F.
  Regional columns: total offences, minor offences, road accidents (total / fatal / injury / normal),
  dead persons M/F, injured persons M/F, and suspects (2018–2023 only).
- Regional tables use **police regions**: Ilala, Temeke and Kinondoni instead of Dar es Salaam, and
  others to be listed in step 1d.
- **2023 needs OCR** and the regional table OCR is noisy (e.g. `Is` for 15, `™` for a number).
  Enter that table by hand from the page images, then check that rows add up to the totals.
- **2023 regional table was entered by hand** (`manual/regional-2023.csv`) from the page image.
  It passes every sum check: regions → Mainland/Zanzibar subtotals → Tanzania total → national tables.
- **2025 report:** Mainland/Zanzibar injury split differs by 5 between the regional table (2,036 / 259)
  and the national tables (2,031 / 264). The Tanzania total (2,295) agrees. "Airports" police
  region has 4 injuries in 2025 only.
- **2021 regional figures do not exist** in the files we have. 2021 has national totals only, from
  Statistical Abstract 2022.
- **2025 causes table looks wrong for 2024:** "Over speeding" goes 291 → 5 and "Careless passengers"
  0 → 226. That may be a reclassification or a shifted row; check it against the 2024 report's own
  Table 3.9 and add a note.
- The `trend` tables (2018 report: 2009–2018; 2020 report: 2010–2020; Abstract: 2016–2022) give
  a second source for each year's national figures.
