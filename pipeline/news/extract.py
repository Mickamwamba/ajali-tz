"""Step 2c: extract crash records from relevant articles.

For each candidate with status "relevant": checks robots.txt, fetches the article, pulls out the main text
with trafilatura, and asks Claude Haiku to fill in one record per crash the article reports. The article
text is used only in memory and then discarded; the queue keeps the extracted facts, the text's length and
a SHA-256 fingerprint (to show later which version of the article was read). No names are ever recorded.

Status after this step: "extracted" (one or more crashes), "not_crash" (the full text showed it isn't a
specific road crash in Tanzania), or unchanged "relevant" on a fetch or API error, to retry later.

Usage:
  uv run python pipeline/news/extract.py             # all relevant candidates
  uv run python pipeline/news/extract.py --limit 5   # try a few first
"""

import argparse
import hashlib
import os
import sys
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Literal, Optional
from urllib.parse import urlsplit

import anthropic
import trafilatura
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import news_queue
from collect import UA, fetch

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6  # USD per token, Claude Haiku 5.5
WORKERS = 4
MAX_CHARS = 40_000  # longer texts are flagged, not silently cut

Region = Literal[
    "Arusha", "Dar es Salaam", "Dodoma", "Geita", "Iringa", "Kagera", "Katavi", "Kigoma", "Kilimanjaro",
    "Lindi", "Manyara", "Mara", "Mbeya", "Morogoro", "Mtwara", "Mwanza", "Njombe", "Pwani", "Rukwa", "Ruvuma",
    "Shinyanga", "Simiyu", "Singida", "Songwe", "Tabora", "Tanga",
    "Kaskazini Pemba", "Kaskazini Unguja", "Kusini Pemba", "Kusini Unguja", "Mjini Magharibi",
]
Vehicle = Literal["bus", "minibus", "car", "pickup_or_van", "lorry", "fuel_tanker", "motorcycle", "bajaji",
                  "bicycle", "cart", "train", "other"]
Victim = Literal["driver", "passenger", "pedestrian", "motorcyclist", "cyclist", "other"]
Cause = Literal["overspeeding", "dangerous_driving", "careless_overtaking", "drunk_driving", "fatigue",
                "vehicle_defect", "brake_failure", "tyre_burst", "poor_road", "weather", "pedestrian_error",
                "other", "not_reported"]


class Crash(BaseModel):
    crash_date: Optional[str] = Field(description="YYYY-MM-DD; resolve 'yesterday'/'jana' from the publication date; null if unknown")
    date_precision: Literal["exact", "approximate", "unknown"]
    region: Optional[Region] = Field(description="Tanzanian administrative region; Dar es Salaam districts (Ilala, Temeke, Kinondoni, Ubungo, Kigamboni) map to Dar es Salaam")
    district: Optional[str] = Field(description="District or council name if stated")
    place: Optional[str] = Field(description="Road, junction, village or landmark, e.g. 'Kiponzelo junction, Iringa-Mbeya highway'")
    vehicles: list[Vehicle]
    deaths: Optional[int] = Field(description="People killed in this crash as stated; null if not stated")
    injuries: Optional[int] = Field(description="People injured as stated; null if not stated")
    victim_types: list[Victim]
    cause: Cause
    cause_text: Optional[str] = Field(description="The cause as reported, at most 15 words, in English")
    confidence: float = Field(description="0 to 1: how sure you are that the fields above are right")
    notes: Optional[str] = Field(description="Caveats, e.g. 'death toll updated from 21 to 23', 'follow-up report', at most 25 words")


class Extraction(BaseModel):
    is_road_crash_in_tanzania: bool = Field(description="True if the article reports at least one specific road crash in Tanzania")
    crashes: list[Crash]


SYSTEM = """You extract facts about road crashes in Tanzania from news articles (English or Swahili) for a
public database. Return one entry in `crashes` for each distinct road crash the article reports in Tanzania.
Leave out crashes in other countries, crashes on water, rail-only or air incidents, and totals over a period.

Rules:
- Record only what the article states. Use null for anything not stated; never guess numbers. Use 0 for
  deaths or injuries only when the article says nobody died or was hurt.
- deaths and injuries are for that crash only, at the latest figure the article gives.
- A follow-up article (condolences, funerals, arrests, updated toll) about one crash still gets one entry,
  dated to the crash itself, not to the follow-up.
- Resolve relative dates ("yesterday", "jana", "on Sunday", "usiku wa kuamkia leo") from the publication date.
  If only the month or week is known, give your best date and set date_precision to "approximate".
  If the article gives no date for the crash at all, use the publication date with date_precision
  "approximate" (news reports usually follow a crash within days).
- Never record anyone's name, in any field. Describe roles instead ("a police officer", "the driver").
- vehicles: one entry per vehicle involved (two buses = "bus", "bus"), classified by how the article
  describes it, not by brand: "Fuso minibus" is minibus, "Fuso truck" or "Scania truck" is lorry. Coaster,
  daladala and Hiace are "minibus"; bodaboda is "motorcycle"; bajaji/tuk-tuk is "bajaji". Pedestrians are
  victims, not vehicles.
- Write cause_text and notes in English."""


_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


def allowed(url: str) -> bool:
    host = "{0.scheme}://{0.netloc}".format(urlsplit(url))
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = fetch(f"{host}/robots.txt")
            rp.parse(r.text.splitlines() if r.ok else [])
        except Exception:
            rp.parse([])
        _robots[host] = rp
    return _robots[host].can_fetch(UA["User-Agent"], url)


def article_text(url: str) -> str:
    if not allowed(url):
        raise PermissionError("robots.txt disallows this URL")
    r = fetch(url)
    r.raise_for_status()
    text = trafilatura.extract(r.text, include_comments=False, include_tables=False, favor_precision=True)
    if not text or len(text) < 200:
        raise ValueError(f"no article text found ({len(text or '')} chars)")
    return text


def process(client: anthropic.Anthropic, row: dict):
    try:
        text = article_text(row["url"])
    except Exception as e:
        return row, None, f"fetch: {type(e).__name__}: {str(e)[:80]}", None, (0, 0)
    meta = {"chars": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
            "truncated": len(text) > MAX_CHARS}
    prompt = (f"Outlet: {row['outlet']}\nPublished: {(row['published_at'] or 'unknown')[:10]}\n"
              f"Headline: {row['title']}\n\nArticle:\n{text[:MAX_CHARS]}")
    try:
        resp = client.messages.parse(
            model=MODEL, max_tokens=4096, output_config={"effort": "medium"}, system=SYSTEM,
            messages=[{"role": "user", "content": prompt}], output_format=Extraction)
    except anthropic.APIStatusError as e:
        body = e.body.get("error", {}) if isinstance(e.body, dict) else {}
        return row, None, f"API error {e.status_code}: {body.get('message', e.message)}"[:160], meta, (0, 0)
    except anthropic.APIConnectionError:
        return row, None, "API connection error", meta, (0, 0)
    usage = (resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return row, None, f"no answer (stop_reason {resp.stop_reason})", meta, usage
    return row, resp.parsed_output, None, meta, usage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    load_dotenv(news_queue.ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"No API key found in {news_queue.ROOT / '.env'}")
        return 1
    client = anthropic.Anthropic()

    rows = news_queue.load()
    todo = [r for r in rows if r["status"] == "relevant"][: args.limit]
    print(f"{len(todo)} articles to extract with {MODEL}\n")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tin = tout = errors = n_crashes = 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for row, result, error, meta, (ti, to) in pool.map(lambda r: process(client, r), todo):
            tin, tout = tin + ti, tout + to
            if error:
                errors += 1
                row["extract_attempts"] = row.get("extract_attempts", 0) + 1
                print(f"  ERROR {row['title'][:60]}  ({error})")
                continue
            row["extraction"] = {"model": MODEL, "at": now, "text": meta, **result.model_dump()}
            row["status"] = "extracted" if result.is_road_crash_in_tanzania and result.crashes else "not_crash"
            if row["status"] == "not_crash":
                print(f"  —     not a crash on full read: {row['title'][:70]}")
            for c in result.crashes:
                n_crashes += 1
                print(f"  {c.crash_date or '????-??-??'} {str(c.region or '?')[:13]:13} d={c.deaths if c.deaths is not None else '?':>3} "
                      f"i={c.injuries if c.injuries is not None else '?':>3} {','.join(c.vehicles)[:22]:22} "
                      f"conf {c.confidence:.2f}  {row['title'][:45]}")
    news_queue.save(rows)
    done = len(todo) - errors
    cost = tin * PRICE_IN + tout * PRICE_OUT
    print(f"\n{done} articles read, {n_crashes} crash records, {errors} errors (kept for retry)")
    print(f"Tokens: {tin:,} in, {tout:,} out. Cost ${cost:.4f}" + (f" (${cost / done * 1000:.2f} per 1,000 articles)" if done else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
