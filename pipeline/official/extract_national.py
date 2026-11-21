"""Step 1c (part 1): extract the national road traffic tables from the police/NBS reports.

Reads pipeline/official/table_index.csv, pulls every `national` table (Tanzania, Mainland, Zanzibar),
plus Statistical Abstract 2022 Table 16.2 for 2021, and writes data/interim/national_raw.csv.

Every report table gives two years (previous and current), so most years are extracted twice.
Both copies are kept; picking one value per year happens in step 1f.

Run: uv run python pipeline/official/extract_national.py
"""

import csv
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "nbs"
INDEX = Path(__file__).with_name("table_index.csv")
OUT = ROOT / "data" / "interim" / "national_raw.csv"

# Row order is the same in every report, in both Swahili and English.
METRICS = ["accidents", "fatal_accidents", "injury_accidents", "normal_accidents", "deaths", "injuries"]
AREAS = {"Tanzania": "Tanzania", "Mainland": "Tanzania Mainland", "Zanzibar": "Zanzibar"}
NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def to_number(tok: str) -> float:
    return float(tok.replace(",", ""))


def page_text(pdf: Path, page: int, ocr: bool) -> str:
    if not ocr:
        with pdfplumber.open(pdf) as doc:
            return doc.pages[page - 1].extract_text() or ""
    with tempfile.TemporaryDirectory() as tmp:
        img = Path(tmp) / "page.png"
        pdfium.PdfDocument(pdf)[page - 1].render(scale=3).to_pil().save(img)
        return subprocess.run(
            ["tesseract", str(img), "-", "--psm", "6"], capture_output=True, text=True, check=True
        ).stdout


def parse_two_year_table(text: str, table_id: str) -> tuple[list[int], dict[str, tuple[float, float]]]:
    """Find the table caption, read its year header and the next six rows of numbers."""
    number = table_id.split()[-1]  # "28", "3.1"
    lines = text.splitlines()
    cap = re.compile(rf"^\s*(Table|Jedwali)\s*(Na\.?)?\s*{re.escape(number)}\b[.:]?\s+(Number|Idadi)", re.I)
    start = next((i for i, l in enumerate(lines) if cap.search(l)), None)
    if start is None:
        raise ValueError(f"caption for {table_id} not found")

    years, rows = None, []
    for line in lines[start + 1 :]:
        found = [int(y) for y in re.findall(r"\b(20[12]\d)\b", line)]
        if years is None and len(found) == 2 and re.search(r"(?i)incident|tukio", line):
            years = found
            continue
        nums = NUM.findall(line)
        if years is not None and len(nums) >= 4 and not re.search(r"(?i)table|jedwali|figure|mchoro", line):
            rows.append([to_number(n) for n in nums[-4:]])
            if len(rows) == len(METRICS):
                break
    if years is None or len(rows) != len(METRICS):
        raise ValueError(f"{table_id}: years={years}, rows found={len(rows)}")

    values = {}
    for metric, (prev, curr, diff, _pct) in zip(METRICS, rows):
        if curr - prev != diff:
            raise ValueError(f"{table_id} {metric}: {curr} - {prev} != {diff}")
        values[metric] = (prev, curr)
    # Not fatal: the reports themselves are occasionally inconsistent here (e.g. 2018 Zanzibar).
    for i in (0, 1):
        parts = sum(values[m][i] for m in ("fatal_accidents", "injury_accidents", "normal_accidents"))
        if parts != values["accidents"][i]:
            print(f"WARN {table_id} {years[i]}: accident types sum to {parts:.0f}, printed total {values['accidents'][i]:.0f}")
    return years, values


def parse_abstract_16_2(text: str) -> list[dict]:
    """Statistical Abstract 2022, Table 16.2: national figures 2016-2022 (Tanzania Police Force)."""
    labels = {
        "Roads accidents": "accidents",
        "Fatal road accidents": "fatal_accidents",
        "Number of deaths": "deaths",
        "Number of injured persons": "injuries",
    }
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("Table 16.2"))
    years = [int(y) for y in re.findall(r"20\d\d", lines[start + 1])]
    out = []
    for line in lines[start + 2 : start + 2 + len(labels)]:
        metric = next(m for label, m in labels.items() if line.startswith(label))
        nums = [to_number(n) for n in NUM.findall(line)][-len(years) :]
        out += [{"year": y, "metric": metric, "value": v} for y, v in zip(years, nums)]
    return out


def main() -> int:
    with INDEX.open() as f:
        index = list(csv.DictReader(f))

    records = []
    for row in index:
        pdf = RAW / row["file"]
        page = int(row["pdf_page"])
        text = page_text(pdf, page, ocr=row["text_layer"] == "ocr")
        base = {"source": "police_nbs", "source_doc": row["file"], "source_table": row["table_id"], "source_page": page}

        if row["content"] == "national":
            years, values = parse_two_year_table(text, row["table_id"])
            for metric, pair in values.items():
                for year, value in zip(years, pair):
                    records.append({**base, "year": year, "area": AREAS[row["area"]], "metric": metric, "value": int(value)})
            print(f"ok  {row['file']:36} {row['table_id']:12} {row['area']:9} {years}")

        elif row["table_id"] == "Table 16.2":
            for r in parse_abstract_16_2(text):
                records.append({**base, "area": "Tanzania", **r, "value": int(r["value"])})
            print(f"ok  {row['file']:36} {row['table_id']:12} Tanzania  2016-2022")

    # Check: Mainland + Zanzibar = Tanzania, within each report table set.
    by_key = {(r["source_doc"], r["year"], r["area"], r["metric"]): r["value"] for r in records}
    problems = 0
    for (doc, year, area, metric), value in by_key.items():
        if area != "Tanzania":
            continue
        ml, zn = by_key.get((doc, year, "Tanzania Mainland", metric)), by_key.get((doc, year, "Zanzibar", metric))
        if ml is not None and zn is not None and ml + zn != value:
            print(f"WARN {doc} {year} {metric}: Mainland {ml} + Zanzibar {zn} != Tanzania {value}")
            problems += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["year", "area", "metric", "value", "source", "source_doc", "source_table", "source_page"]
    records.sort(key=lambda r: (r["year"], r["area"], METRICS.index(r["metric"]), r["source_doc"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(records)
    print(f"\n{len(records)} rows -> {OUT.relative_to(ROOT)}; {problems} sum warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
