"""Step 2f: apply review decisions and publish the media-reported crash log.

Inputs:  data/news/crashes.json (from dedupe.py), data/news/review.json (your decisions, via review.py)
Outputs: data/processed/news_crashes.json and .csv: approved crashes only, with corrections applied

A crash is published when you approved it, or automatically when nothing about it needs a person:
no flags, confidence >= 0.75, and at least one casualty figure. Everything else waits in the review queue.

Run: uv run python pipeline/news/publish.py
"""

import csv
import json
import sys

import news_queue

NEWS = news_queue.ROOT / "data" / "news"
CRASHES = NEWS / "crashes.json"
REVIEW = NEWS / "review.json"
OUT = news_queue.ROOT / "data" / "processed"
MIN_CONFIDENCE = 0.75
COLUMNS = ["crash_id", "crash_date", "region", "district", "place", "lat", "lon", "location_level", "vehicles",
           "deaths", "injuries", "victim_types", "reported_cause", "cause_detail", "n_sources", "source_urls",
           "confidence", "review_status"]


def load_crashes() -> list[dict]:
    return json.loads(CRASHES.read_text()) if CRASHES.exists() else []


def load_review() -> dict:
    return json.loads(REVIEW.read_text()) if REVIEW.exists() else {}


def save_review(review: dict) -> None:
    REVIEW.write_text(json.dumps(review, ensure_ascii=False, indent=1, sort_keys=True))


def review_reasons(c: dict) -> list[str]:
    reasons = list(c.get("flags") or [])
    if not c.get("region"):
        reasons.append("no region")
    if not c.get("crash_date"):
        reasons.append("no date")
    if c.get("confidence", 0) < MIN_CONFIDENCE:
        reasons.append(f"low confidence ({c['confidence']})")
    if c.get("deaths") is None and c.get("injuries") is None:
        reasons.append("no death or injury figures")
    return reasons


def apply_edits(c: dict, edits: dict) -> dict:
    """Corrections from review.py. A changed district or region moves the map point too."""
    from geocode import Gazetteer  # only needed when a location is corrected
    c = {**c, **edits}
    if "district" in edits or "region" in edits:
        gz = Gazetteer()
        if c.get("district"):
            d = gz.get(c["district"], c["region"])
            c.update(district_pcode=d["pcode"], lat=float(d["lat"]), lon=float(d["lon"]), location_level="district")
        else:
            lat, lon = gz.region_point[c["region"]]
            c.update(district_pcode=None, lat=lat, lon=lon, location_level="region")
    return c


def decision_for(c: dict, review: dict) -> tuple[str, dict] | tuple[None, None]:
    """Your decision for this crash: by id, or else by any report (member key) the decision covered."""
    if c["crash_id"] in review:
        return c["crash_id"], review[c["crash_id"]]
    keys = set(c.get("member_keys", []))
    for cid, r in review.items():
        if keys & set(r.get("member_keys", [])):
            return cid, r
    return None, None


def status(c: dict, review: dict) -> tuple[str, dict]:
    """Return (review_status, crash with edits applied)."""
    _, r = decision_for(c, review)
    if r:
        return r["decision"], apply_edits(c, r.get("edits", {}))
    return ("approved_auto" if not review_reasons(c) else "pending"), c


def main() -> int:
    crashes, review = load_crashes(), load_review()
    published, counts = [], {}
    for c in crashes:
        st, c = status(c, review)
        counts[st] = counts.get(st, 0) + 1
        if st in ("approved", "approved_auto"):
            published.append({
                "crash_id": c["crash_id"], "crash_date": c["crash_date"], "region": c["region"],
                "district": c["district"], "place": c["place"], "lat": c["lat"], "lon": c["lon"],
                "location_level": c["location_level"], "vehicles": c["vehicles"], "deaths": c["deaths"],
                "injuries": c["injuries"], "victim_types": c["victim_types"], "reported_cause": c["cause"],
                "cause_detail": c["cause_text"], "n_sources": c["n_sources"],
                "sources": [{"url": s["url"], "outlet": s["outlet"], "title": s["title"],
                             "published_at": s["published_at"]} for s in c["sources"]],
                "confidence": c["confidence"], "review_status": "approved" if st == "approved" else "auto-approved",
            })
    published.sort(key=lambda c: c["crash_date"] or "", reverse=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "news_crashes.json").write_text(json.dumps(published, ensure_ascii=False, indent=1))
    with (OUT / "news_crashes.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for c in published:
            w.writerow({**{k: c.get(k) for k in COLUMNS}, "vehicles": "; ".join(c["vehicles"]),
                        "victim_types": "; ".join(c["victim_types"]),
                        "source_urls": " ".join(s["url"] for s in c["sources"])})
    print(f"{len(crashes)} crashes: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"Published {len(published)} -> data/processed/news_crashes.csv and .json")
    if counts.get("pending"):
        print(f"{counts['pending']} waiting for review: uv run python pipeline/news/review.py list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
