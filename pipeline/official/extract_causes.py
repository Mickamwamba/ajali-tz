"""Step 1c (part 4): extract the causes-of-accidents tables.

The 17 causes appear in the same order in every report, in Swahili (2018-2020) and English (2023-2025),
grouped as human factors (11), defective vehicles (2) and environmental factors (4), each with a subtotal.

Two traps handled here:
  - Column year headers can be wrong (2020 report labels the 2018 column "2016"), and
  - the area changes: tables are titled "Tanzania Bara/Mainland" in every report, but from 2022 the
    grand total equals all-Tanzania accidents, not Mainland.
Both are resolved by matching each column's grand total to the accident totals in national_raw.csv.

Writes data/interim/causes_raw.csv.
Run: uv run python pipeline/official/extract_causes.py
"""

import csv
import re
import sys
from pathlib import Path

from extract_national import NUM, RAW, ROOT, page_text, to_number

INDEX = Path(__file__).with_name("table_index.csv")
NATIONAL = ROOT / "data" / "interim" / "national_raw.csv"
OUT = ROOT / "data" / "interim" / "causes_raw.csv"

GROUPS = {
    "human": ["dangerous_driving", "careless_driving", "careless_cyclists", "careless_motorcyclists",
              "careless_passengers", "overspeeding", "unattended_livestock", "careless_overtaking",
              "careless_pedestrians", "careless_pushcart_operators", "intoxication"],
    "vehicle": ["vehicle_defects", "poor_vehicle_lighting"],
    "environment": ["fire", "road_barriers", "poor_road_infrastructure", "railway_crossing"],
}
CAUSES = [c for cs in GROUPS.values() for c in cs]
# First word(s) of each row label, Swahili and English, to confirm the order.
LABELS = ["uendeshaji|dangerous", "uzembe wa dereva|careless driving", "baiskeli|cyclists",
          "pikipiki|motorcyclists", "abiria|passengers", "mwendo|speeding", "mifugo|livestock",
          "kupita|overtaking", "watembea|pedestrians", "mikokoteni|pushcart", "ulevi|intoxication",
          "ubovu wa magari|vehicle defects", "taa|lighting", "moto|fire", "vizuizi|barriers",
          "barabara|road infra", "reli|railway"]
SUBTOTAL = re.compile(r"(?i)^(jumla|sub ?total|grand total)")


def parse_causes(text: str) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    """Return (cause values per column, subtotals per column) for each year column in the table."""
    lines = [l.strip() for l in text.splitlines()]
    start = next(i for i, l in enumerate(lines) if re.search(r"(?i)idadi\s+asilimia|number\s+percent", l))
    rows, subs, label_buf = [], [], ""
    for line in lines[start + 1 :]:
        if re.match(r"(?i)^(chanzo|source)", line):
            break
        nums = NUM.findall(line)
        label = NUM.sub("", line).strip()
        if len(nums) < 4:  # group heading, or first half of a label split over two lines
            label_buf = f"{label_buf} {label}".strip()
            continue
        values = [int(to_number(n)) for n in nums[0::2]]  # number, percent, number, percent, ...
        full_label = f"{label_buf} {label}".strip().lower()
        label_buf = ""
        (subs if SUBTOTAL.match(full_label) else rows).append((full_label, values))

    if len(rows) != len(CAUSES) or len(subs) != 4:
        raise ValueError(f"expected {len(CAUSES)} causes + 4 subtotals, got {len(rows)} + {len(subs)}")
    for (label, _), pattern in zip(rows, LABELS):
        if not re.search(pattern, label):
            raise ValueError(f"row order mismatch: '{label}' should match '{pattern}'")

    ncols = len(rows[0][1])
    cols = [{c: rows[i][1][k] for i, c in enumerate(CAUSES)} for k in range(ncols)]
    sub_cols = [dict(zip(["human", "vehicle", "environment", "total"], (s[1][k] for s in subs))) for k in range(ncols)]
    return cols, sub_cols


def main() -> int:
    with INDEX.open() as f:
        index = [r for r in csv.DictReader(f) if r["content"] == "causes"]
    # accidents total -> (year, area), for identifying each column
    with NATIONAL.open() as f:
        totals = {}
        for r in csv.DictReader(f):
            if r["metric"] == "accidents" and r["area"] in ("Tanzania", "Tanzania Mainland"):
                totals.setdefault(int(r["value"]), set()).add((int(r["year"]), r["area"]))

    records, warnings = [], 0
    for idx in index:
        text = page_text(RAW / idx["file"], int(idx["pdf_page"]), ocr=idx["text_layer"] == "ocr")
        cols, subs = parse_causes(text)
        found = []
        for values, sub in zip(cols, subs):
            # Subtotals: groups add up, and the grand total is the sum of the groups.
            for g, members in GROUPS.items():
                s = sum(values[c] for c in members)
                if s != sub[g]:
                    print(f"WARN {idx['file']} total {sub['total']}: {g} causes sum to {s}, subtotal printed {sub[g]}")
                    warnings += 1
            if sub["human"] + sub["vehicle"] + sub["environment"] != sub["total"]:
                print(f"WARN {idx['file']}: group subtotals don't add to grand total {sub['total']}")
                warnings += 1

            matches = totals.get(sub["total"], set())
            if len(matches) > 1:
                print(f"FAIL {idx['file']}: grand total {sub['total']} matches several: {sorted(matches)}")
                return 1
            if not matches:  # older comparison columns (2016, 2017) - outside v1
                found.append(f"skipped(total {sub['total']})")
                continue
            year, area = next(iter(matches))
            found.append(f"{year} {area}")
            for cause in CAUSES:
                group = next(g for g, m in GROUPS.items() if cause in m)
                records.append({"year": year, "area": area, "cause_group": group, "cause": cause,
                                "accidents": values[cause], "source": "police_nbs", "source_doc": idx["file"],
                                "source_table": idx["table_id"], "source_page": idx["pdf_page"]})
        if not any(f.startswith(idx["report_year"]) for f in found):
            print(f"FAIL {idx['file']}: the report's own year {idx['report_year']} was not identified ({found})")
            return 1
        print(f"ok  {idx['file']:30} columns: {', '.join(found)}")

    # Same year/area from two reports should agree.
    seen = {}
    for r in records:
        key = (r["year"], r["area"], r["cause"])
        if key in seen and seen[key][0] != r["accidents"]:
            print(f"WARN {key}: {seen[key][1]} says {seen[key][0]}, {r['source_doc']} says {r['accidents']}")
            warnings += 1
        seen.setdefault(key, (r["accidents"], r["source_doc"]))

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    print(f"\n{len(records)} rows -> {OUT.relative_to(ROOT)}; {warnings} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
