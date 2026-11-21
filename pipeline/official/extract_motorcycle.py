"""Step 1c (part 3): extract the motorcycle (bodaboda) tables.

  - `motorcycle` tables: Tanzania / Mainland / Zanzibar, two years each -> accidents, deaths, injuries
  - `motorcycle_regional` tables: by police region (2023 hand-entered in manual/)

Writes data/interim/motorcycle_raw.csv (area_level national|region).
Run: uv run python pipeline/official/extract_motorcycle.py
"""

import csv
import sys
from pathlib import Path

from extract_national import AREAS, RAW, ROOT, page_text, parse_two_year_table
from extract_regional import MANUAL, SUBTOTALS, ZANZIBAR, parse_regional, read_manual

INDEX = Path(__file__).with_name("table_index.csv")
OUT = ROOT / "data" / "interim" / "motorcycle_raw.csv"
METRICS = ["accidents", "deaths", "injuries"]
REG_COLS = ["offences", "accidents", "deaths_m", "deaths_f", "injured_m", "injured_f"]


def main() -> int:
    with INDEX.open() as f:
        index = list(csv.DictReader(f))

    records, warnings = [], 0
    national = {}  # (report, year, area, metric) -> value

    for idx in (r for r in index if r["content"] == "motorcycle"):
        text = page_text(RAW / idx["file"], int(idx["pdf_page"]), ocr=idx["text_layer"] == "ocr")
        years, values = parse_two_year_table(text, idx["table_id"], METRICS)
        area = AREAS[idx["area"]]
        for metric, pair in values.items():
            for year, value in zip(years, pair):
                national[(idx["report_year"], year, area, metric)] = int(value)
                records.append({"year": year, "area_level": "national", "area": area, "metric": metric,
                                "value": int(value), "source": "police_nbs", "source_doc": idx["file"],
                                "source_table": idx["table_id"], "source_page": idx["pdf_page"]})
        print(f"ok  {idx['file']:30} {idx['table_id']:12} {idx['area']:9} {years}")

    # Mainland + Zanzibar = Tanzania within each report.
    for (rep, year, area, metric), v in national.items():
        if area == "Tanzania":
            ml, zn = national.get((rep, year, "Tanzania Mainland", metric)), national.get((rep, year, "Zanzibar", metric))
            if None not in (ml, zn) and ml + zn != v:
                print(f"WARN report {rep}, {year} {metric}: Mainland {ml} + Zanzibar {zn} = {ml + zn}, Tanzania printed {v}")
                warnings += 1

    for idx in (r for r in index if r["content"] == "motorcycle_regional"):
        year = int(idx["report_year"])
        manual = MANUAL / f"motorcycle_regional-{year}.csv"
        if manual.exists():
            table, how = read_manual(manual, REG_COLS), f"manual ({manual.name})"
        else:
            table, how = parse_regional(page_text(RAW / idx["file"], int(idx["pdf_page"]), ocr=False), REG_COLS), "text"
        for v in table.values():
            v["deaths"], v["injuries"] = v["deaths_m"] + v["deaths_f"], v["injured_m"] + v["injured_f"]

        subtotals = {SUBTOTALS[n]: v for n, v in table.items() if n in SUBTOTALS}
        regions = {n: v for n, v in table.items() if n not in SUBTOTALS}
        if set(subtotals) != {"Tanzania Mainland", "Zanzibar", "Tanzania"}:
            print(f"FAIL {year}: subtotals found {sorted(subtotals)}")
            return 1
        for group, members in (("Tanzania Mainland", [n for n in regions if n not in ZANZIBAR]),
                               ("Zanzibar", [n for n in regions if n in ZANZIBAR])):
            for col in REG_COLS[1:]:
                s = sum(regions[n][col] for n in members)
                if s != subtotals[group][col]:
                    print(f"WARN {year} {group} {col}: regions sum to {s}, printed {subtotals[group][col]}")
                    warnings += 1
        for area, sub in subtotals.items():
            for metric in METRICS:
                nat = national.get((str(year), year, area, metric))
                if nat is not None and nat != sub[metric]:
                    print(f"WARN {year} {area} {metric}: regional table {sub[metric]}, national table {nat}")
                    warnings += 1

        for name, v in regions.items():
            if all(v[c] == 0 for c in REG_COLS):
                continue
            for metric in METRICS:
                records.append({"year": year, "area_level": "region", "area": name, "metric": metric,
                                "value": v[metric], "source": "police_nbs", "source_doc": idx["file"],
                                "source_table": idx["table_id"], "source_page": idx["pdf_page"]})
        print(f"ok  {year}  regional  {len(regions)} rows  {how}  Tanzania deaths {subtotals['Tanzania']['deaths']}")

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    print(f"\n{len(records)} rows -> {OUT.relative_to(ROOT)}; {warnings} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
