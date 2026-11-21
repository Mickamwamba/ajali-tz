"""Step 1f: combine, choose one value per figure, add derived measures, and run the checks.

Inputs (data/interim/): national_raw, regional_admin, motorcycle_raw, motorcycle_regional_admin,
causes_raw, estimates_raw, population_2022.

Choosing one value when several reports give the same figure:
  1. the report for that year (e.g. the 2023 report for 2023)
  2. otherwise the next year's report (its comparison column)
  3. otherwise the Statistical Abstract
Disagreements between sources are noted on the row.

Derived measures:
  - deaths_per_100k by region: police deaths / 2022 census population. The 2022 population is used for
    every year, so compare regions within a year, not one region across years.
  - who_to_official_ratio: WHO estimated deaths / police deaths.

Outputs:
  data/interim/official_checked.csv   long format, columns as in docs/schema-official.md
  docs/checks-official.md             what was checked and what was found (regenerated each run)

Run: uv run python pipeline/official/build_official.py
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
OUT = INTERIM / "official_checked.csv"
REPORT = ROOT / "docs" / "checks-official.md"

RENAME = {"accidents": "crashes", "fatal_accidents": "fatal_crashes", "injury_accidents": "injury_crashes",
          "normal_accidents": "other_crashes", "deaths": "deaths", "injuries": "injuries"}
LEVEL = {"Tanzania": "national", "Tanzania Mainland": "zone", "Zanzibar": "zone"}
COLS = ["year", "area_level", "area", "metric", "breakdown", "value", "value_low", "value_high",
        "source", "source_doc", "source_table", "source_page", "notes"]

# Known problems found during extraction (see pipeline/official/TABLES.md).
KNOWN_NOTES = {
    (2021, "Tanzania", "total"): "Statistical Abstract 2022 only; no Mainland/Zanzibar or regional split for 2021",
    (2018, "Tanzania", "vehicle:motorcycle", "injuries"):
        "Printed as 570 in the 2018 and 2019 reports, but Mainland + Zanzibar and the regional table give 634",
}
SUSPECT_CAUSES_2025 = ("Suspect: 2025 cause distribution differs sharply from earlier years "
                       "(e.g. careless passengers 0 -> 226, over speeding 291 -> 5); not confirmed")


def read(name: str) -> list[dict]:
    with (INTERIM / name).open() as f:
        return list(csv.DictReader(f))


def priority(row: dict) -> int:
    m = re.search(r"crime-traffic-(\d{4})", row["source_doc"])
    if m:
        return 0 if int(m[1]) == int(row["year"]) else int(m[1]) - int(row["year"])
    return 99  # Statistical Abstract


def choose(rows: list[dict], key_fn, value_key: str = "value") -> tuple[list[dict], list[str]]:
    """One row per key: best-priority source; note any disagreement."""
    groups = defaultdict(list)
    for r in rows:
        groups[key_fn(r)].append(r)
    chosen, conflicts = [], []
    for key, rs in groups.items():
        rs.sort(key=priority)
        best = dict(rs[0])
        others = {r["source_doc"]: r[value_key] for r in rs[1:] if r[value_key] != best[value_key]}
        if others:
            best["notes"] = f"Other sources differ: {others}"
            conflicts.append(f"{key}: chose {best[value_key]} from {best['source_doc']}; {others}")
        best["n_sources"] = len(rs)
        chosen.append(best)
    return chosen, conflicts


def row(**kw) -> dict:
    out = {c: "" for c in COLS}
    out.update({k: v for k, v in kw.items() if k in COLS})
    return out


def main() -> int:
    records, report, failures = [], [], 0
    agree_stats = defaultdict(lambda: [0, 0])  # table kind -> [figures, figures with 2+ sources]

    # --- national and zone totals -------------------------------------------------------------
    nat, conflicts = choose(read("national_raw.csv"), lambda r: ("national", r["year"], r["area"], r["metric"]))
    for r in nat:
        y = int(r["year"])
        if y < 2018:
            continue
        agree_stats["national"][0] += 1
        agree_stats["national"][1] += r["n_sources"] > 1
        records.append(row(year=y, area_level=LEVEL[r["area"]], area=r["area"], metric=RENAME[r["metric"]],
                           breakdown="total", value=r["value"], source="police_nbs", source_doc=r["source_doc"],
                           source_table=r["source_table"], source_page=r["source_page"],
                           notes=r.get("notes") or KNOWN_NOTES.get((y, r["area"], "total"), "")))

    # --- motorcycle, national and zone --------------------------------------------------------
    moto = [r for r in read("motorcycle_raw.csv") if r["area_level"] == "national"]
    moto_chosen, c2 = choose(moto, lambda r: ("motorcycle", r["year"], r["area"], r["metric"]))
    conflicts += c2
    for r in moto_chosen:
        y = int(r["year"])
        if y < 2018:
            continue
        agree_stats["motorcycle"][0] += 1
        agree_stats["motorcycle"][1] += r["n_sources"] > 1
        note = r.get("notes") or KNOWN_NOTES.get((y, r["area"], "vehicle:motorcycle", r["metric"]), "")
        records.append(row(year=y, area_level=LEVEL[r["area"]], area=r["area"], metric=RENAME[r["metric"]],
                           breakdown="vehicle:motorcycle", value=r["value"], source="police_nbs",
                           source_doc=r["source_doc"], source_table=r["source_table"],
                           source_page=r["source_page"], notes=note))

    # --- regions (one source per year already) ------------------------------------------------
    pop = {r["admin_region"]: int(r["population_2022"]) for r in read("population_2022.csv")}
    for fname, breakdown in (("regional_admin.csv", "total"), ("motorcycle_regional_admin.csv", "vehicle:motorcycle")):
        for r in read(fname):
            if r["admin_region"] == "unallocated":
                continue
            base = dict(year=int(r["year"]), area_level="region", area=r["admin_region"], breakdown=breakdown,
                        source="police_nbs", source_doc=r["source_doc"], source_table=r["source_table"],
                        source_page=r["source_page"])
            records.append(row(**base, metric=RENAME[r["metric"]], value=r["value"]))
            if r["metric"] == "deaths":
                rate = round(int(r["value"]) / pop[r["admin_region"]] * 1e5, 1)
                records.append(row(**base | {"source_doc": f"{r['source_doc']}; nbs-2022-phc-initial-results-en.pdf"},
                                   metric="deaths_per_100k", value=rate,
                                   notes="Per 100,000 people, 2022 census population (used for every year)"))

    # --- causes --------------------------------------------------------------------------------
    causes, c3 = choose(read("causes_raw.csv"), lambda r: ("causes", r["year"], r["area"], r["cause"]), "accidents")
    conflicts += c3
    for r in causes:
        y = int(r["year"])
        agree_stats["causes"][0] += 1
        agree_stats["causes"][1] += r["n_sources"] > 1
        note = r.get("notes", "")
        if y == 2025:
            note = SUSPECT_CAUSES_2025
        records.append(row(year=y, area_level=LEVEL[r["area"]], area=r["area"], metric="crashes",
                           breakdown=f"cause:{r['cause']}", value=r["accidents"], source="police_nbs",
                           source_doc=r["source_doc"], source_table=r["source_table"],
                           source_page=r["source_page"], notes=note))

    # --- WHO estimates and ratio ---------------------------------------------------------------
    police_deaths = {int(r["year"]): int(r["value"]) for r in records
                     if r["area"] == "Tanzania" and r["metric"] == "deaths" and r["breakdown"] == "total"}
    for r in read("estimates_raw.csv"):
        y = int(r["year"])
        records.append(row(year=y, area_level="national", area="Tanzania", metric=r["metric"], breakdown="total",
                           value=r["value"], value_low=r["value_low"], value_high=r["value_high"], source="who",
                           source_doc=r["source_doc"], notes=f"{r['method']}: {r['note']}"))
        if r["metric"] == "deaths" and y in police_deaths:
            p = police_deaths[y]
            records.append(row(year=y, area_level="national", area="Tanzania", metric="who_to_official_ratio",
                               breakdown="total", value=round(int(r["value"]) / p, 1),
                               value_low=round(int(r["value_low"]) / p, 1), value_high=round(int(r["value_high"]) / p, 1),
                               source="derived", source_doc="who + police_nbs",
                               notes="WHO estimated deaths / police-recorded deaths"))

    # =============================== checks ======================================================
    idx = {(r["year"], r["area_level"], r["area"], r["metric"], r["breakdown"], r["source"]): float(r["value"])
           for r in records}

    report.append("## 1. Do reports agree with each other?\n")
    for kind, (n, multi) in agree_stats.items():
        report.append(f"- {kind}: {n} figures, {multi} given by two or more sources")
    report.append(f"- **Disagreements: {len(conflicts)}**")
    report += [f"  - {c}" for c in conflicts]

    report.append("\n## 2. Do regions and zones add up to the national total?\n")
    report.append("| Year | Breakdown | Metric | Regions sum | Mainland + Zanzibar | Tanzania | Result |")
    report.append("| --- | --- | --- | --- | --- | --- | --- |")
    years = sorted({r["year"] for r in records if r["source"] == "police_nbs"})
    for y in years:
        for bd in ("total", "vehicle:motorcycle"):
            for m in ("crashes", "deaths", "injuries"):
                nat_v = idx.get((y, "national", "Tanzania", m, bd, "police_nbs"))
                if nat_v is None:
                    continue
                reg = [v for k, v in idx.items() if k[0] == y and k[1] == "region" and k[3] == m and k[4] == bd]
                zones = [idx.get((y, "zone", z, m, bd, "police_nbs")) for z in ("Tanzania Mainland", "Zanzibar")]
                reg_sum = sum(reg) if reg else None
                zone_sum = sum(zones) if None not in zones else None
                diffs = [s for s in (reg_sum, zone_sum) if s is not None and s != nat_v]
                result = "ok" if not diffs else f"differs by {', '.join(f'{s - nat_v:+.0f}' for s in diffs)}"
                if reg_sum is None and zone_sum is None:
                    result = "national only"
                fmt = lambda v: "–" if v is None else f"{v:,.0f}"
                report.append(f"| {y} | {bd} | {m} | {fmt(reg_sum)} | {fmt(zone_sum)} | {nat_v:,.0f} | {result} |")

    report.append("\nKnown gaps: 2025 regions sum to 4 fewer injuries than Tanzania because 4 injuries were recorded "
                  "by Airports police, which has no region. 2018 motorcycle injuries: see the note on that row.")
    report.append("\n## 3. Large changes from one year to the next\n")
    report.append("National and zone: changes of 20% or more. Regions: deaths changing by 50% or more "
                  "and by at least 20 deaths. Only consecutive years are compared.\n")
    jumps = []
    for (y, lvl, area, m, bd, src), v in sorted(idx.items()):
        if src != "police_nbs" or m not in ("crashes", "deaths", "injuries") or bd not in ("total", "vehicle:motorcycle"):
            continue
        prev = idx.get((y - 1, lvl, area, m, bd, src))
        if not prev:
            continue
        change = (v - prev) / prev
        if lvl != "region" and abs(change) >= 0.20:
            jumps.append(f"- {y - 1}→{y} {area}, {bd}, {m}: {prev:,.0f} → {v:,.0f} ({change:+.0%})")
        elif lvl == "region" and m == "deaths" and abs(change) >= 0.5 and abs(v - prev) >= 20:
            jumps.append(f"- {y - 1}→{y} {area} (region), {bd}, deaths: {prev:,.0f} → {v:,.0f} ({change:+.0%})")
    report += jumps or ["- none"]
    report.append("\nMost national changes are confirmed by two reports, so they reflect what police recorded, "
                  "not extraction errors. Regional deaths swing a lot from year to year because the numbers are small.")

    report.append("\n## 4. Official deaths against the WHO estimate\n")
    report.append("| Year | Police deaths | WHO estimate (95% range) | Ratio |")
    report.append("| --- | --- | --- | --- |")
    for r in records:
        if r["metric"] == "who_to_official_ratio":
            w = next(x for x in records if x["source"] == "who" and x["metric"] == "deaths" and x["year"] == r["year"])
            report.append(f"| {r['year']} | {police_deaths[r['year']]:,} | {int(w['value']):,} "
                          f"({int(w['value_low']):,}–{int(w['value_high']):,}) | {r['value']}× |")

    report.append("\n## 5. Coverage\n")
    report.append("| Data | Years |")
    report.append("| --- | --- |")
    cover = defaultdict(set)
    for r in records:
        label = f"{r['area_level']} · {r['breakdown'].split(':')[0]} · {r['source']}"
        cover[label].add(r["year"])
    for label, ys in sorted(cover.items()):
        report.append(f"| {label} | {', '.join(map(str, sorted(ys)))} |")

    # Failures: any police-region or zone sum that doesn't match for deaths (the headline number).
    for line in report:
        if line.startswith("| ") and "| deaths |" in line and "differs" in line and "| total |" in line:
            failures += 1

    records.sort(key=lambda r: (r["source"], r["metric"], r["breakdown"], r["area_level"], r["area"], r["year"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(records)
    REPORT.write_text("# Official data checks\n\nGenerated by `pipeline/official/build_official.py`; "
                      "do not edit by hand.\n\n" + "\n".join(report) + "\n")
    print("\n".join(report))
    print(f"\n{len(records)} rows -> {OUT.relative_to(ROOT)}; report -> {REPORT.relative_to(ROOT)}; "
          f"{failures} headline failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
