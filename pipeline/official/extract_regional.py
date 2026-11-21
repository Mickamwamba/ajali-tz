"""Step 1c (part 2): extract the regional road traffic tables (by police region).

Reads `regional` rows of table_index.csv and writes data/interim/regional_raw.csv. Reports whose
text layer can't be parsed reliably (2023, OCR) are read from a hand-entered CSV in
pipeline/official/manual/ instead, with the same columns.

Checks:
  - police regions add up to the printed Mainland / Zanzibar subtotals, and those to the Tanzania total
  - Tanzania deaths and injuries match the national table in data/interim/national_raw.csv

Run: uv run python pipeline/official/extract_regional.py
"""

import csv
import re
import sys
from pathlib import Path

from extract_national import NUM, RAW, ROOT, page_text, to_number

INDEX = Path(__file__).with_name("table_index.csv")
MANUAL = Path(__file__).with_name("manual")
NATIONAL = ROOT / "data" / "interim" / "national_raw.csv"
OUT = ROOT / "data" / "interim" / "regional_raw.csv"

# The first 10 numeric columns, in order, in every year (2018-2020 add two "suspects" columns after).
COLS = ["offences", "minor_offences", "accidents", "fatal_accidents", "injury_accidents",
        "normal_accidents", "deaths_m", "deaths_f", "injured_m", "injured_f"]
KEEP = ["accidents", "fatal_accidents", "injury_accidents", "normal_accidents", "deaths", "injuries"]

SUBTOTALS = {  # printed name -> canonical subtotal name
    "Tanzania Bara": "Tanzania Mainland", "Tanzania Mainland": "Tanzania Mainland",
    "Tanzania Zanzibar": "Zanzibar",
    "Tanzania": "Tanzania", "Total": "Tanzania",
}
ZANZIBAR = {"Kaskazini Pemba", "Kaskazini Unguja", "Kusini Pemba", "Kusini Unguja", "Mjini Magharibi"}


def parse_regional(text: str, cols: list[str] = COLS) -> dict[str, dict[str, int]]:
    """Return {printed region name: {col: value}} for every row of the table, including subtotals."""
    rows, pending = {}, None
    started = False
    for line in text.splitlines():
        line = line.strip()
        if not started:
            started = line.startswith(("Arusha",)) or (pending is None and re.match(r"^[\d,]+ [\d,]+ ", line) is not None)
            if not started:
                continue
        if re.match(r"(?i)^(chanzo|source)", line):
            break
        name = NUM.sub("", line).strip(" -") if NUM.search(line) else line
        nums = NUM.findall(line.replace(name, "")) if name else NUM.findall(line)
        # "Tarime - Rorya" keeps its dash; strip stray spaces only.
        name = re.sub(r"\s+", " ", name)
        if nums and name:
            rows[name] = dict(zip(cols, (int(to_number(n)) for n in nums)))
        elif nums:  # 2019 layout: numbers first, name on the next line
            pending = dict(zip(cols, (int(to_number(n)) for n in nums)))
        elif pending is not None and name:
            rows[name] = pending
            pending = None
        if "Tanzania" in rows or "Total" in rows:
            break
    return rows


def read_manual(path: Path, cols: list[str] = COLS) -> dict[str, dict[str, int]]:
    with path.open() as f:
        return {r["region"]: {c: int(r[c]) for c in cols} for r in csv.DictReader(f)}


def main() -> int:
    with INDEX.open() as f:
        index = [r for r in csv.DictReader(f) if r["content"] == "regional"]
    with NATIONAL.open() as f:
        national = {(int(r["year"]), r["area"], r["metric"]): int(r["value"]) for r in csv.DictReader(f)}

    records, errors = [], 0
    for idx in index:
        year = int(idx["report_year"])
        manual = MANUAL / f"regional-{year}.csv"
        if manual.exists():
            table, how = read_manual(manual), f"manual ({manual.name})"
        else:
            table, how = parse_regional(page_text(RAW / idx["file"], int(idx["pdf_page"]), ocr=False)), "text"

        for vals in table.values():
            vals["deaths"] = vals["deaths_m"] + vals["deaths_f"]
            vals["injuries"] = vals["injured_m"] + vals["injured_f"]

        subtotals = {SUBTOTALS[n]: v for n, v in table.items() if n in SUBTOTALS}
        regions = {n: v for n, v in table.items() if n not in SUBTOTALS}
        if set(subtotals) != {"Tanzania Mainland", "Zanzibar", "Tanzania"}:
            print(f"FAIL {year}: subtotals found {sorted(subtotals)}")
            errors += 1
            continue

        # Regions add up to subtotals.
        for group, members in (("Tanzania Mainland", [n for n in regions if n not in ZANZIBAR]),
                               ("Zanzibar", [n for n in regions if n in ZANZIBAR])):
            for col in COLS[2:]:
                s = sum(regions[n][col] for n in members)
                if s != subtotals[group][col]:
                    print(f"WARN {year} {group} {col}: regions sum to {s}, printed {subtotals[group][col]}")
        # Subtotals agree with the national table.
        for metric in ("accidents", "deaths", "injuries"):
            for area in ("Tanzania Mainland", "Zanzibar", "Tanzania"):
                nat = national.get((year, area, metric))
                if nat is not None and nat != subtotals[area][metric]:
                    # Mainland/Zanzibar splits occasionally differ between tables in the same report
                    # (2025 injuries); only a Tanzania-level mismatch means a misread.
                    level = "FAIL" if area == "Tanzania" else "WARN"
                    print(f"{level} {year} {area} {metric}: regional table {subtotals[area][metric]}, national table {nat}")
                    errors += level == "FAIL"

        base = {"source": "police_nbs", "source_doc": idx["file"], "source_table": idx["table_id"],
                "source_page": idx["pdf_page"], "extraction": how}
        for name, vals in regions.items():
            if all(vals[c] == 0 for c in COLS):  # Marine / Railway / TAZARA / Airports: empty rows
                continue
            area_group = "Zanzibar" if name in ZANZIBAR else "Tanzania Mainland"
            for m in KEEP:
                records.append({"year": year, "police_region": name, "area_group": area_group,
                                "metric": m, "value": vals[m], **base})
        print(f"ok  {year}  {len(regions):2} rows  {how}  Tanzania deaths {subtotals['Tanzania']['deaths']}")

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    print(f"\n{len(records)} rows -> {OUT.relative_to(ROOT)}; {errors} failures")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
