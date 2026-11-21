"""Step 2b: AI filter. Is this article about a specific road crash in Tanzania?

Reads candidates with status "new" from data/news/candidates.jsonl, asks Claude Haiku using only the
headline and the outlet's summary, and sets status to "relevant" or "rejected" with the category and a
short reason. Articles that error stay "new" and are retried on the next run.

Needs ANTHROPIC_API_KEY in the project's .env file.

Usage:
  uv run python pipeline/news/filter.py             # all new candidates
  uv run python pipeline/news/filter.py --limit 10  # try a few first
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Literal

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import news_queue

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6  # USD per token, Claude Haiku 5.5
WORKERS = 4

SYSTEM = """You screen Tanzanian news articles for a public database of road crashes in Tanzania.
You see only an article's headline and a short summary, in English or Swahili. Choose one category:

- road_crash: the article reports a specific road traffic crash that happened in Tanzania (mainland or
  Zanzibar): a collision or overturn involving any road vehicle (car, bus, minibus/daladala, lorry, truck,
  motorcycle/bodaboda, bajaji, bicycle, cart) or a pedestrian hit by a vehicle. Follow-up reports about one
  specific crash also count (updated death toll, condolences, victims identified, driver arrested or
  charged, protests after a named crash). A train hitting a road vehicle at a crossing counts.
- road_safety_general: road safety in general (campaigns, enforcement, laws, road building, hospital
  preparedness) with no specific crash reported.
- aggregate_statistics: totals over a period or area (e.g. "1,066 people died in road crashes in 2025/26")
  rather than one crash.
- non_road_incident: a crash or accident that is not on a road: boat or ferry, aircraft, train with no road
  vehicle, mine, fire, workplace, lightning, drowning.
- outside_tanzania: a road crash in another country (e.g. Kenya, Uganda, Zambia).
- unrelated: the keyword appears in another sense (e.g. a market or price "crash", a business "accident"
  insurance product, sports).

If the summary is too short to be sure but a specific road crash in Tanzania is plausible, choose
road_crash: a later step reads the full article and can still reject it. Give a reason of at most
15 words, in English."""


class Screening(BaseModel):
    category: Literal["road_crash", "road_safety_general", "aggregate_statistics", "non_road_incident",
                      "outside_tanzania", "unrelated"]
    reason: str = Field(description="At most 15 words, in English")


def screen(client: anthropic.Anthropic, row: dict) -> tuple[dict, Screening | None, str | None, tuple[int, int]]:
    text = f"Outlet: {row['outlet']}\nHeadline: {row['title']}\nSummary: {row['excerpt'] or '(none)'}"
    try:
        resp = client.messages.parse(
            model=MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},  # a quick judgement; low effort keeps it cheap
            system=SYSTEM,
            messages=[{"role": "user", "content": text}],
            output_format=Screening,
        )
    except anthropic.RateLimitError:
        return row, None, "rate limited", (0, 0)
    except anthropic.APIStatusError as e:
        body = e.body if isinstance(e.body, dict) else {}
        detail = body.get("error", {}).get("message", "") if isinstance(body.get("error"), dict) else ""
        return row, None, f"API error {e.status_code}: {detail or e.message}"[:160], (0, 0)
    except anthropic.APIConnectionError:
        return row, None, "connection error", (0, 0)
    usage = (resp.usage.input_tokens, resp.usage.output_tokens)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return row, None, f"no answer (stop_reason {resp.stop_reason})", usage
    return row, resp.parsed_output, None, usage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="screen at most this many candidates")
    args = ap.parse_args()

    env_file = news_queue.ROOT / ".env"
    load_dotenv(env_file)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print(f"No API key found. Create {env_file} containing one line:\n  ANTHROPIC_API_KEY=sk-ant-...")
        return 1
    client = anthropic.Anthropic()

    rows = news_queue.load()
    todo = [r for r in rows if r["status"] == "new"][: args.limit]
    print(f"{len(todo)} candidates to screen with {MODEL}\n")
    if not todo:
        return 0

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tokens_in = tokens_out = 0
    counts: dict[str, int] = {}
    errors = 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for row, result, error, (ti, to) in pool.map(lambda r: screen(client, r), todo):
            tokens_in += ti
            tokens_out += to
            if error:
                errors += 1
                print(f"  ERROR  {row['title'][:70]}  ({error})")
                continue
            row["filter"] = {"category": result.category, "reason": result.reason, "model": MODEL, "at": now}
            row["excerpt"] = None  # publisher's text is only needed for screening
            row["status"] = "relevant" if result.category == "road_crash" else "rejected"
            counts[result.category] = counts.get(result.category, 0) + 1
            mark = "✓" if row["status"] == "relevant" else " "
            print(f"  {mark} {result.category:21} {row['title'][:70]}")

    news_queue.save(rows)
    cost = tokens_in * PRICE_IN + tokens_out * PRICE_OUT
    screened = len(todo) - errors
    print(f"\nScreened {screened}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    if errors:
        print(f"{errors} errors (left as new; rerun to retry)")
    print(f"Tokens: {tokens_in:,} in, {tokens_out:,} out. Cost ${cost:.4f}"
          + (f" (${cost / screened * 1000:.2f} per 1,000 articles)" if screened else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
