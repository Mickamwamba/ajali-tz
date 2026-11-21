# ajali-tz

A public dashboard of road crash deaths and injuries in Tanzania. It shows three views side by side:
the official police/NBS trend, the WHO/GBD estimate of the true toll, and a log of crashes reported in the news.

Full scope: [docs/scope-v1.md](docs/scope-v1.md) · Build plan: [docs/plan.md](docs/plan.md)

## Layout

```
data/raw/nbs/        Police/NBS PDF reports, as downloaded
data/raw/who/        WHO/GBD source files
data/processed/      Clean CSVs the dashboard reads
pipeline/official/   Scripts: PDFs -> official dataset (Phase 1)
pipeline/news/       Daily news agent (Phase 2)
site/                Static dashboard (Observable Framework): cd site && npm install && npm run dev
docs/                Scope, plan, schemas, methodology notes
```

## Setup

```
uv sync
```

## Licence

Code: MIT (`LICENSE`). Compiled data: CC BY 4.0, with third-party sources keeping their own terms (`data/LICENSE.md`).
