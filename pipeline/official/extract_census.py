"""Extract 2022 census population by region (NBS, 2022 PHC Initial Results, Table 1, PDF page 17).

Writes data/interim/population_2022.csv. Checks that regions add up to the printed Mainland,
Zanzibar and Tanzania totals and that every admin region in region_map.csv is present.
Run: uv run python pipeline/official/extract_census.py
"""

import csv
import re
import sys
from pathlib import Path

import pdfplumber

from map_regions import load_map

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "data" / "raw" / "census" / "nbs-2022-phc-initial-results-en.pdf"
PAGE = 17
OUT = ROOT / "data" / "interim" / "population_2022.csv"
ROW = re.compile(r"^(?P<name>[A-Za-z ]+?) (?P<both>[\d,]+) (?P<male>[\d,]+) (?P<female>[\d,]+)$")


def main() -> int:
    with pdfplumber.open(PDF) as doc:
        text = doc.pages[PAGE - 1].extract_text()
    rows = {}
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if m:
            rows[m["name"]] = {k: int(m[k].replace(",", "")) for k in ("both", "male", "female")}

    totals = {k: rows.pop(k) for k in ("Tanzania", "Tanzania Mainland", "Tanzania Zanzibar")}
    zanzibar = {"Kaskazini Unguja", "Kusini Unguja", "Mjini Magharibi", "Kaskazini Pemba", "Kusini Pemba"}
    for total, members in (("Tanzania Mainland", set(rows) - zanzibar), ("Tanzania Zanzibar", zanzibar)):
        s = sum(rows[n]["both"] for n in members)
        if s != totals[total]["both"]:
            print(f"FAIL {total}: regions sum to {s:,}, printed {totals[total]['both']:,}")
            return 1
    expected = {m["admin_region"] for m in load_map().values() if m["admin_region"]}
    if set(rows) != expected:
        print(f"FAIL region names differ: missing {expected - set(rows)}, extra {set(rows) - expected}")
        return 1

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["admin_region", "population_2022", "source_doc", "source_page"])
        for name in sorted(rows):
            w.writerow([name, rows[name]["both"], PDF.name, PAGE])
    print(f"ok  {len(rows)} regions, Tanzania {totals['Tanzania']['both']:,} -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
