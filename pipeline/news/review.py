"""Weekly review queue for media-reported crashes.

  uv run python pipeline/news/review.py list                      crashes waiting for review
  uv run python pipeline/news/review.py show <id>                 everything about one crash, with source links
  uv run python pipeline/news/review.py approve <id> [note]       publish it as it is
  uv run python pipeline/news/review.py reject <id> <reason>      never publish it (e.g. not a road crash)
  uv run python pipeline/news/review.py set <id> deaths=23 district=Iramba ...   correct fields and approve
  uv run python pipeline/news/review.py undo <id>                 forget your decision (back to automatic)

<id> can be the first few characters of a crash id. Fields you can set: crash_date (YYYY-MM-DD), region,
district, place, deaths, injuries, vehicles (comma-separated), cause.
Decisions are saved in data/news/review.json; run publish.py afterwards (the daily job does this too).
"""

import sys
from datetime import date, datetime, timezone

from geocode import Gazetteer
from publish import decision_for, load_crashes, load_review, review_reasons, save_review, status

EDITABLE = {"crash_date", "region", "district", "place", "deaths", "injuries", "vehicles", "cause"}


def find(crashes: list[dict], prefix: str) -> dict:
    hits = [c for c in crashes if c["crash_id"].startswith(prefix)]
    if len(hits) != 1:
        sys.exit(f"'{prefix}' matches {len(hits)} crashes; use more characters of the id")
    return hits[0]


def line(c: dict) -> str:
    d = "?" if c["deaths"] is None else c["deaths"]
    i = "?" if c["injuries"] is None else c["injuries"]
    return (f"{c['crash_id']}  {c['crash_date'] or '????-??-??'}  {c['region']}/{c['district'] or '-'}  "
            f"deaths {d}, injured {i}  {', '.join(c['vehicles']) or 'vehicles unknown'}")


def parse_edits(pairs: list[str], crash: dict) -> dict:
    gz, edits = Gazetteer(), {}
    for p in pairs:
        if "=" not in p:
            sys.exit(f"expected field=value, got '{p}'")
        k, v = p.split("=", 1)
        if k not in EDITABLE:
            sys.exit(f"can't set '{k}'; fields: {', '.join(sorted(EDITABLE))}")
        if k in ("deaths", "injuries"):
            if v not in ("", "null", "?") and not v.isdigit():
                sys.exit(f"{k} must be a whole number (or ? if unknown), got '{v}'")
            edits[k] = None if v in ("", "null", "?") else int(v)
        elif k == "vehicles":
            edits[k] = [x.strip() for x in v.split(",") if x.strip()]
        elif k == "crash_date":
            date.fromisoformat(v)
            edits[k] = v
        else:
            edits[k] = v or None
    region = edits.get("region", crash["region"])
    if region not in gz.region_point:
        sys.exit(f"unknown region '{region}'")
    district = edits.get("district", crash["district"] if "region" not in edits else None)
    if district:
        d, conflict = gz.match(district, region)
        if not d:
            sys.exit(conflict or f"no district '{district}' in {region}")
        edits["district"], edits["region"] = d["district"], d["region"]
    return edits


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    crashes, review = load_crashes(), load_review()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if cmd == "list":
        pending = [c for c in crashes if status(c, review)[0] == "pending"]
        print(f"{len(pending)} crashes waiting for review\n")
        for c in pending:
            print(line(c))
            for r in review_reasons(c):
                print(f"    ⚠ {r}")
        return 0

    if not args:
        sys.exit(f"usage: review.py {cmd} <id> ...")
    c = find(crashes, args[0])

    if cmd == "show":
        st, shown = status(c, review)
        print(line(shown), f"\nstatus: {st}")
        print(f"place: {shown['place']}\ncause: {shown['cause']} ({shown['cause_text']})")
        print(f"victims: {', '.join(shown['victim_types']) or '-'}   confidence: {shown['confidence']}")
        for r in review_reasons(c):
            print(f"⚠ {r}")
        if decision_for(c, review)[1]:
            print(f"your decision: {decision_for(c, review)[1]}")
        print("sources:")
        for s in c["sources"]:
            print(f"  {(s['published_at'] or '')[:10]}  {s['outlet']}: {s['title']}\n      {s['url']}")
        return 0
    if cmd == "approve":
        review.pop(decision_for(c, review)[0], None)
        review[c["crash_id"]] = {"decision": "approved", "note": " ".join(args[1:]) or None, "at": now,
                                 "member_keys": c["member_keys"]}
    elif cmd == "reject":
        if len(args) < 2:
            sys.exit("give a reason, e.g.: review.py reject <id> not a road crash")
        review.pop(decision_for(c, review)[0], None)
        review[c["crash_id"]] = {"decision": "rejected", "note": " ".join(args[1:]), "at": now,
                                 "member_keys": c["member_keys"]}
    elif cmd == "set":
        edits = parse_edits(args[1:], c)
        old_id, old = decision_for(c, review)
        prior = (old or {}).get("edits", {})
        review.pop(old_id, None)
        review[c["crash_id"]] = {"decision": "approved", "edits": {**prior, **edits}, "at": now,
                                 "member_keys": c["member_keys"]}
    elif cmd == "undo":
        review.pop(decision_for(c, review)[0], None)
    else:
        sys.exit(f"unknown command '{cmd}'\n{__doc__}")
    save_review(review)
    print(f"{cmd}: {line(status(c, review)[1])} -> {status(c, review)[0]}")
    print("Run publish.py to update the published files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
