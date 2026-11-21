"""Step 1e: WHO estimates of the true road death toll.

Sources (data/raw/who/):
  - who-gho-RS_198-tza.json  WHO GHO "Estimated road traffic death rate (per 100 000)", 2000-2023, with 95% range
  - who-gho-RS_196-tza.json  WHO GHO "Estimated number of road traffic deaths", 2021 only
  - who-road-safety-profile-2023-tza.pdf  WHO country profile (2021: 10,052 deaths; population 63,588,334)
  - worldbank-population-tza.json  World Bank SP.POP.TOTL, used only for year-to-year population growth

WHO publishes a death *count* for 2021 only. For other years:
    deaths = WHO rate x population / 100,000
with population = WHO's 2021 population (63,588,334) scaled by World Bank growth relative to 2021.
This keeps WHO's own population base; it reproduces the published 2021 count to within rounding of
the rate (one decimal). Derived rows are marked method=derived.

Writes data/interim/estimates_raw.csv.
Run: uv run python pipeline/official/extract_estimates.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHO = ROOT / "data" / "raw" / "who"
OUT = ROOT / "data" / "interim" / "estimates_raw.csv"

WHO_POP_2021 = 63_588_334  # WHO Global status report on road safety 2023, Tanzania profile
FIRST_YEAR = 2018


def gho(indicator: str) -> list[dict]:
    rows = json.loads((WHO / f"who-gho-{indicator}-tza.json").read_text())["value"]
    return [r for r in rows if r["Dim1"] in (None, "SEX_BTSX")]  # both sexes


def main() -> int:
    meta, wb = json.loads((WHO / "worldbank-population-tza.json").read_text())
    wb_pop = {int(r["date"]): r["value"] for r in wb if r["value"]}

    def population(year: int) -> float:
        return WHO_POP_2021 * wb_pop[year] / wb_pop[2021]

    records = []
    rates = {r["TimeDim"]: r for r in gho("RS_198") if r["TimeDim"] >= FIRST_YEAR}
    for year, r in sorted(rates.items()):
        records.append({"year": year, "area": "Tanzania", "metric": "deaths_rate_per_100k",
                        "value": r["NumericValue"], "value_low": r["Low"], "value_high": r["High"],
                        "method": "published", "source": "who", "source_doc": "who-gho-RS_198-tza.json",
                        "note": "WHO GHO RS_198, both sexes"})
        pop = population(year)
        note = "rate x population (WHO 2021 base, World Bank growth)"
        if year > 2021:
            note += "; WHO projection beyond the 2021 report year, wide uncertainty"
        records.append({"year": year, "area": "Tanzania", "metric": "deaths",
                        "value": round(r["NumericValue"] * pop / 1e5), "value_low": round(r["Low"] * pop / 1e5),
                        "value_high": round(r["High"] * pop / 1e5), "method": "derived", "source": "who",
                        "source_doc": "who-gho-RS_198-tza.json; worldbank-population-tza.json", "note": note})

    # The one published count replaces the derived 2021 value, and checks the method.
    (pub,) = gho("RS_196")
    derived_2021 = next(r for r in records if r["year"] == 2021 and r["metric"] == "deaths")
    gap = abs(derived_2021["value"] - pub["NumericValue"]) / pub["NumericValue"]
    print(f"check 2021: derived {derived_2021['value']:,} vs WHO published {pub['NumericValue']:,.0f} ({gap:.1%})")
    if gap > 0.01:
        print("FAIL derivation is more than 1% off WHO's published 2021 count")
        return 1
    derived_2021.update({"value": int(pub["NumericValue"]), "value_low": int(pub["Low"]),
                         "value_high": int(pub["High"]), "method": "published",
                         "source_doc": "who-gho-RS_196-tza.json; who-road-safety-profile-2023-tza.pdf",
                         "note": "WHO GHO RS_196 / Global status report on road safety 2023"})

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    for r in records:
        if r["metric"] == "deaths":
            print(f"  {r['year']}  {r['value']:>7,}  [{r['value_low']:,}-{r['value_high']:,}]  {r['method']}")
    print(f"{len(records)} rows -> {OUT.relative_to(ROOT)}  (World Bank data last updated {meta.get('lastupdated')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
