"""Step 2a: find which news outlets have usable feeds.

For each outlet, tries likely feed URLs and reports: HTTP status, whether robots.txt allows the path,
number of items, newest item date, and how many items mention a crash keyword.
Also tests GDELT and Google News search feeds.

Run: uv run python pipeline/news/probe_feeds.py
"""

import time
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import feedparser
import requests

UA = "ajali-tz-research/0.1 (road safety data project)"
TIMEOUT = 20
KEYWORDS = ["ajali", "barabarani", "road accident", "crash", "bodaboda", "pikipiki", "basi", "bus", "lori",
            "truck", "wamefariki", "wafariki", "killed", "dead", "die"]

OUTLETS = {
    "The Citizen": ["https://www.thecitizen.co.tz/rss", "https://www.thecitizen.co.tz/tanzania/rss",
                    "https://www.thecitizen.co.tz/feed", "https://www.thecitizen.co.tz/rss.xml"],
    "Mwananchi": ["https://www.mwananchi.co.tz/rss", "https://www.mwananchi.co.tz/mw/rss",
                  "https://www.mwananchi.co.tz/feed", "https://www.mwananchi.co.tz/rss.xml"],
    "Daily News": ["https://dailynews.co.tz/feed/", "https://www.dailynews.co.tz/feed/"],
    "HabariLeo": ["https://habarileo.co.tz/feed/", "https://www.habarileo.co.tz/feed/"],
    "The Guardian (IPP)": ["https://www.ippmedia.com/feed", "https://www.ippmedia.com/rss",
                           "https://www.ippmedia.com/en/rss.xml", "https://www.ippmedia.com/en/feed"],
    "The Chanzo": ["https://thechanzo.com/feed/", "https://thechanzo.com/sw/feed/"],
    "Millard Ayo": ["https://millardayo.com/feed/", "https://www.millardayo.com/feed/"],
}

SEARCHES = {
    "GDELT (Tanzania sources, 7 days)":
        "https://api.gdeltproject.org/api/v2/doc/doc?format=json&mode=artlist&maxrecords=75&timespan=7d&query="
        + quote('(ajali OR "road accident" OR "bus accident" OR bodaboda) sourcecountry:tanzania'),
    "Google News, Swahili (ajali barabarani)":
        "https://news.google.com/rss/search?q=" + quote("ajali barabarani") + "&hl=sw&gl=TZ&ceid=TZ:sw",
    "Google News, English (Tanzania road accident)":
        "https://news.google.com/rss/search?q=" + quote("Tanzania road accident") + "&hl=en-TZ&gl=TZ&ceid=TZ:en",
}

_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def robots_allows(url: str) -> str:
    host = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(f"{host}/robots.txt", headers={"User-Agent": UA}, timeout=TIMEOUT)
            rp.parse(r.text.splitlines() if r.ok else [])
            _robots[host] = rp
        except requests.RequestException:
            _robots[host] = None
    rp = _robots[host]
    if rp is None:
        return "robots.txt unreachable"
    return "allowed" if rp.can_fetch(UA, url) else "DISALLOWED"


def crash_hits(entries) -> int:
    n = 0
    for e in entries:
        text = f"{e.get('title', '')} {e.get('summary', '')}".lower()
        n += any(k in text for k in KEYWORDS)
    return n


def newest(entries) -> str:
    dates = [e.get("published_parsed") or e.get("updated_parsed") for e in entries]
    dates = [datetime(*d[:6], tzinfo=timezone.utc) for d in dates if d]
    return max(dates).strftime("%Y-%m-%d %H:%M") if dates else "no dates"


def probe_feed(url: str) -> dict:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    except requests.RequestException as e:
        return {"url": url, "status": f"error: {type(e).__name__}"}
    out = {"url": url, "status": r.status_code, "type": r.headers.get("content-type", "")[:40]}
    if r.ok:
        feed = feedparser.parse(r.content)
        out.update(items=len(feed.entries), newest=newest(feed.entries), crash=crash_hits(feed.entries),
                   sample=[e.get("title", "")[:90] for e in feed.entries[:2]])
    return out


def main() -> None:
    print(f"Probe run {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n")
    for outlet, urls in OUTLETS.items():
        print(f"## {outlet}")
        found = False
        for url in urls:
            res = probe_feed(url)
            ok = res.get("items", 0) > 0
            line = f"  {res['status']}  {url}"
            if ok:
                line += f"  -> {res['items']} items, newest {res['newest']}, crash-related {res['crash']}  [{robots_allows(url)}]"
            print(line)
            if ok:
                for s in res["sample"]:
                    print(f"       e.g. {s}")
                found = True
                break  # first working feed is enough
            time.sleep(1)
        if not found:
            print("  -> no working feed found")
        print()

    for name, url in SEARCHES.items():
        print(f"## {name}")
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        except requests.RequestException as e:
            print(f"  error: {type(e).__name__}\n")
            continue
        if "gdelt" in url:
            try:
                arts = r.json().get("articles", [])
            except ValueError:
                print(f"  {r.status_code}, not JSON: {r.text[:120]!r}\n")
                continue
            domains = sorted({a.get("domain", "") for a in arts})
            print(f"  {r.status_code}  {len(arts)} articles from {len(domains)} sites: {', '.join(domains[:12])}")
            for a in arts[:3]:
                print(f"       e.g. [{a.get('language')}] {a.get('title', '')[:90]}")
        else:
            feed = feedparser.parse(r.content)
            sources = sorted({e.get("source", {}).get("title", "?") for e in feed.entries})
            print(f"  {r.status_code}  {len(feed.entries)} items, newest {newest(feed.entries)}, "
                  f"from {len(sources)} sites: {', '.join(sources[:12])}")
            for e in feed.entries[:3]:
                print(f"       e.g. {e.get('title', '')[:90]}")
        print()
        time.sleep(1)


if __name__ == "__main__":
    main()
