# Boundary source files

Not committed (9 MB); `pipeline/news/build_gazetteer.py` turns them into `data/reference/`.

| File | What | URL |
| --- | --- | --- |
| adm1.zip | OCHA COD-AB Tanzania, regions (31), 2018-10-19 | https://data.humdata.org/dataset/cod-ab-tza (tza_admbnda_adm1_20181019.zip) |
| adm2.zip | OCHA COD-AB Tanzania, districts (170), 2018-10-19 | https://data.humdata.org/dataset/cod-ab-tza (tza_admbnda_adm2_20181019.zip) |

Source: Tanzania National Bureau of Statistics, via UN OCHA. Licence: CC BY-IGO. Downloaded 2026-11-21.

To restore: download both zips from the page above into this folder and unzip into `adm1/` and `adm2/`.

Councils created after 2018 (Ubungo, Kigamboni, Chalinze, Kibiti, ...) are not separate districts in these
files; `data/reference/district_aliases.csv` maps them to the district they belong to.
