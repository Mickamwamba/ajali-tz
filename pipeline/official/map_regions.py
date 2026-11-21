"""Step 1d: map police regions to administrative regions.

Uses region_map.csv to turn data/interim/regional_raw.csv and the region rows of motorcycle_raw.csv
into administrative-region totals (26 Mainland regions + 5 Zanzibar regions).

Police units with no region (Marine, Railway, TAZARA, Airports) are reported as "unallocated":
they stay in national totals but are not on the map.

Checks:
  - every police region name in the data is in region_map.csv (fails otherwise)
  - every year has all 31 administrative regions (warns otherwise)
  - nothing lost: admin regions + unallocated = sum of police regions, for each year and metric

Writes data/interim/regional_admin.csv and data/interim/motorcycle_regional_admin.csv.
Run: uv run python pipeline/official/map_regions.py
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
MAP = Path(__file__).with_name("region_map.csv")
ADMIN_REGIONS = 31


def load_map() -> dict[str, dict]:
    with MAP.open() as f:
        return {r["police_region"]: r for r in csv.DictReader(f)}


def aggregate(rows: list[dict], name_col: str, value_col: str, out: Path, rmap: dict) -> int:
    unknown = sorted({r[name_col] for r in rows} - set(rmap))
    if unknown:
        print(f"FAIL unknown police regions: {unknown} - add them to region_map.csv")
        return 1

    totals = defaultdict(int)          # (year, admin_region, zone, metric) -> value
    police_sum = defaultdict(int)      # (year, metric) -> value
    meta = {}
    for r in rows:
        m = rmap[r[name_col]]
        admin = m["admin_region"] or "unallocated"
        key = (int(r["year"]), admin, m["zone"], r["metric"])
        totals[key] += int(r[value_col])
        police_sum[(key[0], key[3])] += int(r[value_col])
        meta[key[0]] = {k: r[k] for k in ("source", "source_doc", "source_table", "source_page")}

    # Nothing lost in the merge.
    mapped_sum = defaultdict(int)
    for (year, _admin, _zone, metric), v in totals.items():
        mapped_sum[(year, metric)] += v
    for k, v in police_sum.items():
        if mapped_sum[k] != v:
            print(f"FAIL {k}: police regions {v}, after mapping {mapped_sum[k]}")
            return 1

    for year in sorted({k[0] for k in totals}):
        regions = {k[1] for k in totals if k[0] == year and k[1] != "unallocated"}
        unalloc = {k[3]: v for k, v in totals.items() if k[0] == year and k[1] == "unallocated" and v}
        flag = "" if len(regions) == ADMIN_REGIONS else f"  WARN expected {ADMIN_REGIONS}"
        print(f"  {year}: {len(regions)} admin regions{flag}" + (f"; unallocated {unalloc}" if unalloc else ""))

    records = [{"year": y, "admin_region": a, "zone": z, "metric": m, "value": v, **meta[y]}
               for (y, a, z, m), v in sorted(totals.items())]
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    print(f"  {len(records)} rows -> {out.relative_to(ROOT)}")
    return 0


def main() -> int:
    rmap = load_map()
    admin = {m["admin_region"] for m in rmap.values() if m["admin_region"]}
    assert len(admin) == ADMIN_REGIONS, f"region_map.csv has {len(admin)} admin regions"

    with (INTERIM / "regional_raw.csv").open() as f:
        regional = list(csv.DictReader(f))
    with (INTERIM / "motorcycle_raw.csv").open() as f:
        moto = [r for r in csv.DictReader(f) if r["area_level"] == "region"]

    print("regional tables:")
    if aggregate(regional, "police_region", "value", INTERIM / "regional_admin.csv", rmap):
        return 1
    print("motorcycle regional tables:")
    return aggregate(moto, "area", "value", INTERIM / "motorcycle_regional_admin.csv", rmap)


if __name__ == "__main__":
    sys.exit(main())
