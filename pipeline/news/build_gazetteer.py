"""Build the district gazetteer and simplified boundary files from the OCHA shapefiles.

Input (data/raw/boundaries/, see SOURCES.md there): OCHA COD-AB Tanzania 2018, regions (ADM1) and districts (ADM2).
Output (data/reference/):
  tz_districts.csv                  district, region, pcode, lat, lon (a point inside each district)
  tz_regions.geojson                31 regions, simplified, names matching pipeline/official/region_map.csv
  tz_districts.geojson              170 districts, simplified (for the dashboard map and point-in-district lookups)

Run: uv run python pipeline/news/build_gazetteer.py
"""

import csv
import json
import re
from pathlib import Path

import shapefile
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "boundaries"
OUT = ROOT / "data" / "reference"
TOLERANCE = 0.005  # degrees (~500 m): plenty for a national/regional map
REGION_FIX = {"Dar-es-salaam": "Dar es Salaam"}
NAME_FIX = {"Butiam": "Butiama"}  # typo in the source data


def clean(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    return NAME_FIX.get(name, name)


def rounded(geom: dict, nd: int = 4) -> dict:
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], nd), round(c[1], nd)]
    return {"type": geom["type"], "coordinates": r(geom["coordinates"])}


def read(path: Path):
    rd = shapefile.Reader(str(path))
    for sr in rd.iterShapeRecords():
        yield sr.record.as_dict(), shape(sr.shape.__geo_interface__)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    regions, districts, rows = [], [], []
    for rec, geom in read(RAW / "adm1" / "tza_admbnda_adm1_20181019.shp"):
        name = REGION_FIX.get(rec["ADM1_EN"], rec["ADM1_EN"])
        p = geom.representative_point()
        regions.append({"type": "Feature", "properties": {"region": name, "pcode": rec["ADM1_PCODE"],
                        "lat": round(p.y, 4), "lon": round(p.x, 4)},
                        "geometry": rounded(mapping(geom.simplify(TOLERANCE, preserve_topology=True)))})
    for rec, geom in read(RAW / "adm2" / "tza_admbnda_adm2_20181019.shp"):
        name, region = clean(rec["ADM2_EN"]), REGION_FIX.get(rec["ADM1_EN"], rec["ADM1_EN"])
        p = geom.representative_point()  # always inside the district, unlike a centroid
        rows.append({"district": name, "region": region, "pcode": rec["ADM2_PCODE"],
                     "lat": round(p.y, 4), "lon": round(p.x, 4)})
        districts.append({"type": "Feature", "properties": {"district": name, "region": region, "pcode": rec["ADM2_PCODE"]},
                          "geometry": rounded(mapping(geom.simplify(TOLERANCE, preserve_topology=True)))})

    rows.sort(key=lambda r: (r["region"], r["district"]))
    with (OUT / "tz_districts.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for fname, feats in (("tz_regions.geojson", regions), ("tz_districts.geojson", districts)):
        (OUT / fname).write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))

    ours = {r["admin_region"] for r in csv.DictReader((ROOT / "pipeline/official/region_map.csv").open()) if r["admin_region"]}
    got = {f["properties"]["region"] for f in regions}
    assert got == ours, f"region names differ: {got ^ ours}"
    for fname in ("tz_districts.csv", "tz_regions.geojson", "tz_districts.geojson"):
        print(f"{fname:22} {(OUT / fname).stat().st_size / 1024:7.0f} KB")
    print(f"{len(regions)} regions (names match region_map.csv), {len(rows)} districts")


if __name__ == "__main__":
    main()
