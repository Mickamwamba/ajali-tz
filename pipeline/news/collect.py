"""Collect candidate crash articles from the news sources in SOURCES.md.

Fetches each source, keeps articles whose headline or summary matches a road-crash keyword, and appends
new ones to data/news/candidates.jsonl (a local work queue, not committed: it holds publishers' headlines
and summaries). Already-seen URLs are skipped, so it is safe to run as often as you like.

Usage:
  uv run python pipeline/news/collect.py                  # normal run (WordPress sites: last 3 days)
  uv run python pipeline/news/collect.py --since-days 365 # backfill WordPress sites for a year
"""

import argparse
import hashlib
import html
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "data" / "news" / "candidates.jsonl"
UA = {"User-Agent": "ajali-tz-research/0.1 (road safety data project)"}
TIMEOUT = 30
PAUSE = 1.0  # seconds between requests to the same site

SOURCES = [
    {"outlet": "The Citizen", "lang": "en", "kind": "rss", "url": "https://www.thecitizen.co.tz/rss.xml"},
    {"outlet": "Mwananchi", "lang": "sw", "kind": "rss", "url": "https://www.mwananchi.co.tz/rss.xml"},
    {"outlet": "Daily News", "lang": "en", "kind": "wp", "url": "https://dailynews.co.tz", "terms": ["accident", "crash", "collision"]},
    {"outlet": "HabariLeo", "lang": "sw", "kind": "wp", "url": "https://habarileo.co.tz", "terms": ["ajali"]},
    {"outlet": "The Chanzo", "lang": "en", "kind": "wp", "url": "https://thechanzo.com", "terms": ["accident", "crash", "collision"]},
]

# Road-related words. Loose on purpose: the AI filter (step 2b) makes the real decision.
# "basi" (bus) is left out because it also means "so/enough" in Swahili.
KEYWORDS = {
    "en": ["accident", "accidents", "crash", "crashes", "collision", "collided", "overturned", "knocked down",
           "run over", "bus", "buses", "lorry", "lorries", "truck", "trucks", "motorcycle", "motorcyclist",
           "motorbike", "bodaboda", "boda boda", "bajaji", "pedestrian", "pedestrians", "road carnage", "road deaths",
           "road safety", "highway"],
    "sw": ["ajali", "mabasi", "lori", "malori", "pikipiki", "bodaboda", "boda boda", "bajaji", "dereva",
           "madereva", "kugongwa", "aligongwa", "waligongwa", "kugongana", "yamegongana", "yaligongana",
           "kupinduka", "lilipinduka", "ilipinduka", "barabarani", "watembea kwa miguu", "mtembea kwa miguu",
           "usalama barabarani"],
}
# One pattern for both languages: English articles quote Swahili and the reverse.
ANY = re.compile(r"\b(" + "|".join(re.escape(k) for words in KEYWORDS.values() for k in words) + r")\b", re.I)


def fetch(url: str, params: dict | None = None) -> requests.Response:
    """GET with retries: news sites have brief outages (seen: HTTP 500s, DNS failures)."""
    waits = [5, 15, 0]
    for attempt, wait in enumerate(waits, 1):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT)
            if r.status_code < 500:
                return r
            err: Exception = requests.HTTPError(f"HTTP {r.status_code}")
        except requests.RequestException as e:
            err = e
        if attempt == len(waits):
            raise err
        time.sleep(wait)
    raise RuntimeError("unreachable")


def canonical(url: str) -> str:
    s = urlsplit(url.strip())
    return urlunsplit((s.scheme.lower(), s.netloc.lower().removeprefix("www."), s.path.rstrip("/"), "", ""))


def clean(text: str, limit: int = 400) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def matches(title: str, excerpt: str) -> list[str]:
    return sorted({m.lower() for m in ANY.findall(f"{title} {excerpt}")})


def from_rss(src: dict) -> list[dict]:
    r = fetch(src["url"])
    r.raise_for_status()
    out = []
    for e in feedparser.parse(r.content).entries:
        d = e.get("published_parsed") or e.get("updated_parsed")
        out.append({"url": e.get("link", ""), "title": clean(e.get("title", ""), 300),
                    "excerpt": clean(e.get("summary", "")),
                    "published_at": datetime(*d[:6], tzinfo=timezone.utc).isoformat() if d else None})
    return out


def from_wordpress(src: dict, since: datetime) -> list[dict]:
    out = []
    for term in src["terms"]:
        page, pages = 1, 1
        while page <= pages:
            r = fetch(f"{src['url']}/wp-json/wp/v2/posts", params={
                "search": term, "after": since.strftime("%Y-%m-%dT%H:%M:%S"), "per_page": 100, "page": page,
                "orderby": "date", "order": "desc", "_fields": "date_gmt,link,title,excerpt"})
            if r.status_code == 400 and page > 1:  # past the last page
                break
            r.raise_for_status()
            pages = int(r.headers.get("X-WP-TotalPages", 1))
            for p in r.json():
                out.append({"url": p["link"], "title": clean(p["title"]["rendered"], 300),
                            "excerpt": clean(p["excerpt"]["rendered"]),
                            "published_at": p["date_gmt"] + "+00:00" if p.get("date_gmt") else None})
            page += 1
            time.sleep(PAUSE)
    return out


def load_seen() -> set[str]:
    if not QUEUE.exists():
        return set()
    with QUEUE.open() as f:
        return {json.loads(line)["id"] for line in f if line.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=3, help="how far back to search the WordPress sites")
    args = ap.parse_args()
    since = datetime.now(timezone.utc) - timedelta(days=args.since_days)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    seen = load_seen()
    new_rows, failures = [], 0
    print(f"{'source':12} {'fetched':>7} {'matched':>7} {'new':>5}")
    for src in SOURCES:
        try:
            items = from_rss(src) if src["kind"] == "rss" else from_wordpress(src, since)
        except (requests.RequestException, ValueError) as e:
            print(f"{src['outlet']:12} FAILED: {type(e).__name__}: {str(e)[:100]}")
            failures += 1
            continue
        matched = new = 0
        batch_ids = set()
        for it in items:
            terms = matches(it["title"], it["excerpt"])
            if not it["url"] or not terms:
                continue
            matched += 1
            cid = hashlib.sha1(canonical(it["url"]).encode()).hexdigest()[:16]
            if cid in seen or cid in batch_ids:
                continue
            batch_ids.add(cid)
            new += 1
            new_rows.append({"id": cid, "url": it["url"], "outlet": src["outlet"], "lang": src["lang"],
                             "title": it["title"], "excerpt": it["excerpt"], "published_at": it["published_at"],
                             "collected_at": now, "method": src["kind"], "matched_terms": terms, "status": "new"})
        seen |= batch_ids
        print(f"{src['outlet']:12} {len(items):>7} {matched:>7} {new:>5}")
        time.sleep(PAUSE)

    with QUEUE.open("a") as f:
        for row in new_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\n{len(new_rows)} new candidates -> {QUEUE.relative_to(ROOT)} ({len(seen)} total)")
    if failures:
        print(f"{failures} source(s) failed")
    # Zero articles from every source usually means a site changed or blocked us (scope: alert on this).
    return 1 if failures == len(SOURCES) else 0


if __name__ == "__main__":
    sys.exit(main())
