"""Step 2e: merge reports of the same crash into one record.

Two crash records are the same crash when all of these hold:
  - same region, and crash dates at most 2 days apart
  - their vehicles overlap by family (bus~minibus, lorry~fuel tanker, car~pickup); unknown vehicles match anything
  - if both name a district, it is the same district
  - they do not come from the same article (an article listing two crashes means two crashes)

The merged crash keeps the highest stated death and injury counts (tolls rise as reports update), the
most common exact date, the most specific location, and a link to every source article.

Output: data/news/crashes.json (the media-reported crash log; local until step 2f moves it to the database).
Run: uv run python pipeline/news/dedupe.py
"""

import hashlib
import json
import sys
from collections import Counter
from datetime import date

import news_queue

OUT = news_queue.ROOT / "data" / "news" / "crashes.json"
MAX_DAYS = 2
FAMILY = {"bus": "bus", "minibus": "bus", "lorry": "lorry", "fuel_tanker": "lorry", "car": "car",
          "pickup_or_van": "car", "motorcycle": "motorcycle", "bajaji": "bajaji", "bicycle": "bicycle",
          "cart": "cart", "train": "train", "other": "other"}


def records() -> list[dict]:
    out = []
    for row in news_queue.load():
        if row["status"] != "extracted":
            continue
        for i, c in enumerate(row["extraction"]["crashes"]):
            out.append({**c, "_article": row["id"], "_key": f"{row['id']}#{i}",
                        "_source": {"url": row["url"], "outlet": row["outlet"], "title": row["title"],
                                    "published_at": row["published_at"]}})
    return out


def day(r: dict) -> date | None:
    try:
        return date.fromisoformat(r["crash_date"]) if r.get("crash_date") else None
    except ValueError:
        return None


def families(r: dict) -> set[str]:
    return {FAMILY.get(v, "other") for v in r.get("vehicles") or []}


def same_crash(a: dict, b: dict) -> bool:
    if a["_article"] == b["_article"]:
        return False
    if a["geo"]["region"] != b["geo"]["region"] or not a["geo"]["region"]:
        return False
    da, db = day(a), day(b)
    if not da or not db or abs((da - db).days) > MAX_DAYS:
        return False
    fa, fb = families(a), families(b)
    if fa and fb and not fa & fb:
        return False
    xa, xb = a["geo"]["district"], b["geo"]["district"]
    return not (xa and xb and xa != xb)


def cluster(recs: list[dict]) -> list[list[dict]]:
    """Each record joins the cluster it matches best (closest date); a cluster never holds two records
    from the same article, and every member must match the newcomer."""
    clusters: list[list[dict]] = []
    for r in sorted(recs, key=lambda r: (r.get("crash_date") or "", r["_key"])):
        best, best_gap = None, None
        for c in clusters:
            if any(m["_article"] == r["_article"] for m in c) or not all(same_crash(m, r) for m in c):
                continue
            gap = min(abs((day(m) - day(r)).days) for m in c)
            if best is None or gap < best_gap:
                best, best_gap = c, gap
        if best is None:
            clusters.append([r])
        else:
            best.append(r)
    return clusters


def merge(members: list[dict]) -> dict:
    exact = [m["crash_date"] for m in members if m.get("date_precision") == "exact" and m.get("crash_date")]
    dates = exact or [m["crash_date"] for m in members if m.get("crash_date")]
    crash_date = Counter(dates).most_common(1)[0][0] if dates else None
    by_conf = sorted(members, key=lambda m: -m["confidence"])
    district_level = [m["geo"] for m in members if m["geo"]["level"] == "district"]
    geo = Counter(json.dumps(g, sort_keys=True) for g in district_level).most_common(1)[0][0] if district_level else None
    geo = json.loads(geo) if geo else by_conf[0]["geo"]
    with_vehicles = [m for m in by_conf if m.get("vehicles")]
    vehicles = max(with_vehicles, key=lambda m: (len(m["vehicles"]), m["confidence"]))["vehicles"] if with_vehicles else []
    deaths = [m["deaths"] for m in members if m.get("deaths") is not None]
    injuries = [m["injuries"] for m in members if m.get("injuries") is not None]
    causes = [m["cause"] for m in members if m.get("cause") not in (None, "not_reported")]
    cause = Counter(causes).most_common(1)[0][0] if causes else "not_reported"
    cause_text = next((m["cause_text"] for m in by_conf if m.get("cause") == cause and m.get("cause_text")), None)
    sources = sorted((m["_source"] for m in members), key=lambda s: s["published_at"] or "")
    first = sources[0]["url"]
    flags = []
    if len(set(deaths)) > 1:
        flags.append(f"sources give different death tolls: {sorted(set(deaths))}")
    if len({m['crash_date'] for m in members if m.get('crash_date')}) > 1:
        flags.append("sources give different dates")
    if not exact:
        flags.append("no exact date")
    if any(m["geo"].get("conflict") for m in members):
        flags.append("; ".join(sorted({m['geo']['conflict'] for m in members if m['geo'].get('conflict')})))
    return {
        "crash_id": hashlib.sha1(f"{first}|{crash_date}".encode()).hexdigest()[:12],
        "crash_date": crash_date,
        "region": geo["region"], "district": geo["district"], "district_pcode": geo["district_pcode"],
        "lat": geo["lat"], "lon": geo["lon"], "location_level": geo["level"],
        "place": next((m["place"] for m in by_conf if m.get("place")), None),
        "vehicles": vehicles,
        "deaths": max(deaths) if deaths else None,
        "injuries": max(injuries) if injuries else None,
        "victim_types": sorted({v for m in members for v in m.get("victim_types") or []}),
        "cause": cause, "cause_text": cause_text,
        "confidence": round(min(m["confidence"] for m in members), 2) if len(members) == 1 else round(max(m["confidence"] for m in members), 2),
        "n_sources": len(sources), "sources": sources, "flags": flags,
        "member_keys": sorted(m["_key"] for m in members),
    }


def main() -> int:
    recs = [r for r in records() if r.get("geo")]
    clusters = cluster(recs)
    crashes = sorted((merge(c) for c in clusters), key=lambda c: c["crash_date"] or "", reverse=True)
    OUT.write_text(json.dumps(crashes, ensure_ascii=False, indent=1))
    for c in crashes:
        loc = f"{c['region']}/{c['district'] or '-'}"
        print(f"  {c['crash_date'] or '????-??-??'} {loc:26} d={c['deaths'] if c['deaths'] is not None else '?':>3} "
              f"i={c['injuries'] if c['injuries'] is not None else '?':>3} {','.join(c['vehicles'])[:20]:20} "
              f"{c['n_sources']} src  {c['sources'][0]['title'][:40]}")
        for f in c["flags"]:
            print(f"{'':16}⚠ {f}")
    print(f"\n{len(recs)} crash records from articles -> {len(crashes)} distinct crashes -> {OUT.relative_to(news_queue.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
