# News sources: what can be collected (step 2a)

Probed 2026-11-21 with `probe_feeds.py`, using a generic user agent (`ajali-tz-research/0.1`).
robots.txt allows every feed and API path listed as usable.

| Outlet | Language | Method | What it gives | Window | Use |
| --- | --- | --- | --- | --- | --- |
| The Citizen | English | RSS `https://www.thecitizen.co.tz/rss.xml` | Latest 40 articles, all sections | ~28 hours | ✅ Collect every 3 hours |
| Mwananchi | Swahili | News sitemap `https://www.mwananchi.co.tz/sitemap.xml` (its RSS feed returned 404 from 2026-11-22) | Latest 25 articles with title, date, image caption | ~10 hours | ✅ Collect every 3 hours |
| Daily News | English | WordPress search API `https://dailynews.co.tz/wp-json/wp/v2/posts?search=…` | Every matching article, paged, with dates | Years | ✅ Daily search + backfill |
| HabariLeo | Swahili | WordPress search API `https://habarileo.co.tz/wp-json/wp/v2/posts?search=…` | Every matching article | Years | ✅ Daily search + backfill |
| The Chanzo | English | WordPress search API `https://thechanzo.com/wp-json/wp/v2/posts?search=…` | Every matching article | Years | ✅ Daily search + backfill |
| The Guardian (IPP) | English | — | All feed paths return 403 Forbidden | — | ❌ Blocks automated access; not collected. Its stories may still appear via GDELT |
| Millard Ayo | Swahili | WordPress feed `https://millardayo.com/feed/` | Site showed "We will be back soon!" (maintenance) | — | ⏸ Recheck later; probably WordPress, so the search API may work |
| GDELT DOC API | many | `api.gdeltproject.org/api/v2/doc/doc` | Global news index, filter by Tanzanian sources | Back to 2017 | ⏸ Returned 429 (rate limit, 1 request / 5 s) on every try; retry later |
| Google News RSS | many | `news.google.com/rss/search?q=…` | English search finds Tanzanian crashes from many outlets; Swahili search returns mostly Kenyan news | ~30 days | ⏸ Optional extra. Links are Google redirect URLs that need resolving |

## Decisions

- **Five outlets for v1:** The Citizen, Mwananchi, Daily News, HabariLeo, The Chanzo. That is two Swahili and three English.
- **Collect every 3 hours**, not once a day. Mwananchi's and Daily News's feeds only reach back 8–11 hours.
  Collecting is free (no AI call); only articles that pass the keyword pre-filter go to the AI filter.
- **Backfill (12 months):** the WordPress search APIs cover Daily News, HabariLeo and The Chanzo. The Citizen
  and Mwananchi have no archive feed (the Citizen sitemap lists only the latest 40), so their backfill depends
  on GDELT working, or is skipped. The news log is labelled "reported in the media" anyway.
- **Keyword pre-filter** before any AI call (Swahili + English): ajali, barabarani, gari, basi, lori, pikipiki,
  bodaboda, bajaji, wamefariki, kujeruhiwa, accident, crash, collision, bus, lorry, truck, motorcycle, killed, injured.
  It is deliberately loose: the AI filter (2b) decides.

## Search terms for the WordPress APIs

English sites: `accident`, `crash`, `collision`. Swahili sites: `ajali`.
Search matches broadly (e.g. "accident" finds hospital emergency plans), which the AI filter handles.

## Source health

Every collection run records when each source last worked in `data/news/source_health.json`. The GitHub job's
last step fails, and GitHub emails the repository owner, if any source has not worked for 24 hours.
