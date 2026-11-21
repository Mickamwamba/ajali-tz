"""Step 1g: write the public official dataset.

Reads data/interim/official_checked.csv (step 1f) and writes:
  data/processed/official.csv                   full long-format dataset (docs/schema-official.md)
  data/processed/official_national_summary.csv  one row per year: police vs WHO, for quick citing

Adds 3-year regional averages (deaths_avg_3yr, deaths_per_100k_avg_3yr) where three consecutive years
exist: 2018-2020 and 2023-2025. Regional numbers swing a lot from year to year; the map uses these.

Run: uv run python pipeline/official/publish_official.py
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "interim" / "official_checked.csv"
OUT = ROOT / "data" / "processed" / "official.csv"
SUMMARY = ROOT / "data" / "processed" / "official_national_summary.csv"


def main() -> int:
    with SRC.open() as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0])

    # 3-year regional averages.
    by_region = defaultdict(dict)  # (area, breakdown, metric) -> {year: row}
    for r in rows:
        if r["area_level"] == "region" and r["metric"] in ("deaths", "deaths_per_100k"):
            by_region[(r["area"], r["breakdown"], r["metric"])][int(r["year"])] = r
    added = 0
    for (area, breakdown, metric), years in sorted(by_region.items()):
        for end in sorted(years):
            span = [end - 2, end - 1, end]
            if not all(y in years for y in span):
                continue
            vals = [float(years[y]["value"]) for y in span]
            avg = round(sum(vals) / 3, 1)
            last = years[end]
            rows.append({**{c: "" for c in cols}, "year": end, "area_level": "region", "area": area,
                         "metric": f"{metric}_avg_3yr", "breakdown": breakdown, "value": avg,
                         "source": last["source"], "source_doc": "; ".join(sorted({d for y in span for d in years[y]["source_doc"].split("; ")})),
                         "notes": f"Average of {span[0]}-{span[-1]}"})
            added += 1

    rows.sort(key=lambda r: (r["source"], r["metric"], r["breakdown"], r["area_level"], r["area"], int(r["year"])))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # National summary, one row per year.
    def get(year, metric, source, field="value"):
        for r in rows:
            if (r["year"] == str(year) and r["area"] == "Tanzania" and r["breakdown"] == "total"
                    and r["metric"] == metric and r["source"] == source):
                return r[field]
        return ""

    years = sorted({int(r["year"]) for r in rows if r["source"] == "police_nbs" and r["area"] == "Tanzania"})
    summary_cols = ["year", "police_crashes", "police_deaths", "police_injuries", "who_estimated_deaths",
                    "who_estimated_deaths_low", "who_estimated_deaths_high", "who_to_police_ratio", "notes"]
    with SUMMARY.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(summary_cols)
        for y in years:
            notes = []
            if y == 2021:
                notes.append("Police figures from NBS Statistical Abstract 2022")
            who_note = get(y, "deaths", "who", "notes")
            if who_note.startswith("derived"):
                notes.append("WHO figure derived from WHO rate x population")
            if "projection" in who_note:
                notes.append("WHO projection, wide uncertainty")
            if not who_note:
                notes.append("No WHO estimate yet")
            w.writerow([y, get(y, "crashes", "police_nbs"), get(y, "deaths", "police_nbs"),
                        get(y, "injuries", "police_nbs"), get(y, "deaths", "who"), get(y, "deaths", "who", "value_low"),
                        get(y, "deaths", "who", "value_high"), get(y, "who_to_official_ratio", "derived"),
                        "; ".join(notes)])

    print(f"{len(rows)} rows ({added} 3-year averages) -> {OUT.relative_to(ROOT)}")
    print(f"{len(years)} years -> {SUMMARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
