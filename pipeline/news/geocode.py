"""Step 2d: place each extracted crash in a district.

For every crash record in the queue (status "extracted"), sets crash["geo"]:
  region, district, district_pcode, lat, lon, level ("district" | "region"), method, conflict

Methods, in order:
  1. gazetteer   the extracted district (or a word of the place) matches data/reference/tz_districts.csv
                 or district_aliases.csv, within the extracted region
  2. nominatim   OpenStreetMap search for "place, region, Tanzania", then the district containing that point
  3. region      no district found: the region's point
The map point is always the district's (or region's) reference point, never the exact crash location.

If a district matches only in a different region from the one extracted, the crash is flagged with
geo.conflict for the review queue (2f), and placed at region level.

Nominatim policy: at most 1 request per second, identifying user agent, results cached in
data/news/geocache.json so each place is looked up once.

Run: uv run python pipeline/news/geocode.py
"""

import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

import news_queue
from collect import UA

ROOT = news_queue.ROOT
REF = ROOT / "data" / "reference"
CACHE = ROOT / "data" / "news" / "geocache.json"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

# Words around district names in English and Swahili news.
URBAN_WORDS = r"municipal(ity)?|city|town|township|urban|manispaa|jiji|mji"
FILLER = rf"\b(district|council|dc|mc|tc|cc|wilaya|halmashauri|ya|la|wa|of|the|{URBAN_WORDS})\b"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[’'`\-–]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(FILLER, " ", norm(s))).strip()


class Gazetteer:
    def __init__(self):
        self.districts = list(csv.DictReader((REF / "tz_districts.csv").open()))
        self.by_name: dict[str, list[dict]] = {}
        for d in self.districts:
            self.by_name.setdefault(norm(d["district"]), []).append(d)
        self.aliases = {norm(a["alias"]): a for a in csv.DictReader((REF / "district_aliases.csv").open())}
        regions = json.loads((REF / "tz_regions.geojson").read_text())["features"]
        self.region_point = {f["properties"]["region"]: (f["properties"]["lat"], f["properties"]["lon"]) for f in regions}
        feats = json.loads((REF / "tz_districts.geojson").read_text())["features"]
        self.shapes = [shape(f["geometry"]) for f in feats]
        self.props = [f["properties"] for f in feats]
        self.tree = STRtree(self.shapes)

    def get(self, district: str, region: str) -> dict:
        return next(d for d in self.by_name[norm(district)] if d["region"] == region)

    def match(self, text: str, region: str | None) -> tuple[dict | None, str | None]:
        """Return (district row, conflict). Prefers the urban unit when the text says city/municipal/jiji."""
        if not text:
            return None, None
        urban = re.search(URBAN_WORDS, norm(text)) is not None
        key = core(text)
        candidates: list[dict] = []
        if key in self.aliases:
            a = self.aliases[key]
            candidates = [self.get(a["district"], a["region"])]
        else:
            names = [f"{key} urban", f"{key} township authority", f"{key} mji"] if urban else []
            for name in names + [key]:
                if name in self.by_name:
                    candidates = self.by_name[name]
                    break
        if not candidates:
            return None, None
        in_region = [c for c in candidates if c["region"] == region]
        if in_region or region is None:
            return (in_region or candidates)[0], None
        other = candidates[0]
        return None, f"'{text}' is a district in {other['region']}, but the crash was placed in {region}"

    def district_at(self, lat: float, lon: float) -> dict | None:
        pt = Point(lon, lat)
        for i in self.tree.query(pt):
            if self.shapes[i].contains(pt):
                p = self.props[i]
                return self.get(p["district"], p["region"])
        return None


def nominatim(query: str, cache: dict) -> list[tuple[float, float]]:
    """All matches (up to 5), so places that share a name can be spotted."""
    cached = cache.get(query)
    if cached is None or (cached and not isinstance(cached[0], list)):  # missing, or old single-hit format
        time.sleep(1.1)  # usage policy: max 1 request per second
        r = requests.get(NOMINATIM, headers=UA, timeout=30,
                         params={"q": query, "countrycodes": "tz", "format": "jsonv2", "limit": 5})
        r.raise_for_status()
        cache[query] = [[float(h["lat"]), float(h["lon"])] for h in r.json()]
    return [tuple(x) for x in cache[query]]


def place_parts(place: str, region: str | None = None) -> list[str]:
    """'Kisesa Village, Sanjo Division, Mwanza–Musoma highway' -> ['Kisesa', 'Sanjo', ...] most specific first."""
    parts = []
    for p in re.split(r",|\bnear\b|\bin\b", place or ""):
        p = re.sub(r"(?i)\b(village|ward|division|area|junction|street|road|highway|escarpment|town|kijiji|kata|eneo)\b", " ", p)
        p = re.sub(r"\s+", " ", p).strip(" -–")
        if p and not re.search(r"[–-]", p):  # skip road names like 'Mwanza–Musoma'
            if region and core(re.sub(r"(?i)\b(region|mkoa)\b", "", p)) == core(region):
                continue  # "Singida" in a place means the region, not Singida district
            parts.append(p)
    return parts


def geocode(crash: dict, gz: Gazetteer, cache: dict) -> dict:
    region = crash.get("region")
    conflicts = []
    # 1. district field, then each part of the place
    for text in [crash.get("district")] + place_parts(crash.get("place"), region):
        d, conflict = gz.match(text, region)
        if conflict:
            conflicts.append(conflict)
        if d:
            return {"region": d["region"], "district": d["district"], "district_pcode": d["pcode"],
                    "lat": float(d["lat"]), "lon": float(d["lon"]), "level": "district", "method": "gazetteer",
                    "conflict": None}
    # 2. OpenStreetMap search for the most specific place name
    if region:
        for part in place_parts(crash.get("place"), region)[:2]:
            found = [gz.district_at(*hit) for hit in nominatim(f"{part}, {region}, Tanzania", cache)]
            in_region = {d["district"]: d for d in found if d and d["region"] == region}
            if len(in_region) == 1:
                d = next(iter(in_region.values()))
                return {"region": region, "district": d["district"], "district_pcode": d["pcode"],
                        "lat": float(d["lat"]), "lon": float(d["lon"]), "level": "district", "method": "nominatim",
                        "conflict": None, "matched_place": part}
            if len(in_region) > 1:
                conflicts.append(f"ambiguous: OpenStreetMap has '{part}' in {' and '.join(sorted(in_region))}")
                break
            if any(found):
                conflicts.append(f"OpenStreetMap places '{part}' outside {region}")
    # 3. region only
    lat, lon = gz.region_point.get(region, (None, None))
    return {"region": region, "district": None, "district_pcode": None, "lat": lat, "lon": lon,
            "level": "region" if region else "none", "method": "region",
            "conflict": "; ".join(conflicts) or None}


def main() -> int:
    gz = Gazetteer()
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    rows = news_queue.load()
    counts: dict[str, int] = {}
    for row in rows:
        if row["status"] != "extracted":
            continue
        for c in row["extraction"]["crashes"]:
            c["geo"] = geocode(c, gz, cache)
            g = c["geo"]
            counts[g["method"]] = counts.get(g["method"], 0) + 1
            flag = f"  ⚠ {g['conflict']}" if g["conflict"] else ""
            print(f"  {g['method']:9} {str(g['region']):15} {str(g['district']):20} "
                  f"<- district={c.get('district')!s:14} place={str(c.get('place'))[:40]}{flag}")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    news_queue.save(rows)
    total = sum(counts.values())
    print(f"\n{total} crashes: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
