"""Read and write the local work queue of candidate articles (data/news/candidates.jsonl)."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "data" / "news" / "candidates.jsonl"


def load() -> list[dict]:
    if not QUEUE.exists():
        return []
    with QUEUE.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def save(rows: list[dict]) -> None:
    """Rewrite the whole queue atomically, so an interrupted run can't leave half a file."""
    tmp = QUEUE.with_suffix(".tmp")
    with tmp.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, QUEUE)
