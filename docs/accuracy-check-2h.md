# Extraction accuracy check (step 2h)

Checked 2026-11-21 by the project owner, using the Crash Record Check page: each AI-extracted crash record
compared field by field against its source article.

| | |
| --- | --- |
| Records checked | 45 (every record extracted so far, from 34 articles) |
| Fields judged | 360 (8 per record) |
| Correct | 360 |
| Accuracy | **100%** (target: 90%) |

| Field | Correct | Wrong |
| --- | --- | --- |
| Date | 45 | 0 |
| Location (region / district) | 45 | 0 |
| Place | 45 | 0 |
| Vehicles | 45 | 0 |
| Deaths | 45 | 0 |
| Injuries | 45 | 0 |
| Victims | 45 | 0 |
| Cause | 45 | 0 |

## How to read this

- 45 out of 45 records correct means the record-level error rate is very probably below about 7%
  (the "rule of three": 3 / 45). It does not prove the pipeline is never wrong.
- The check came after two prompt fixes found during development (vehicle types by description, not
  brand; dates for follow-up articles) and the geocoding fixes, so it measures the current pipeline.
- Model: Claude Haiku 5.5. Extraction prompt: `pipeline/news/extract.py`.

## Next check

Repeat on a fresh sample of about 30 records after 3 months, as part of the scope's success measures,
and whenever the extraction prompt or model changes.
