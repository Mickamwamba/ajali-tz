// Data loader: when the site was built, and how current each dataset is.
import {readFileSync} from "node:fs";
const news = JSON.parse(readFileSync("../data/processed/news_crashes.json", "utf8"));
const dates = news.map((c) => c.crash_date).filter(Boolean).sort();
process.stdout.write(JSON.stringify({
  built: new Date().toISOString(),
  news_crashes: news.length,
  news_first: dates[0] ?? null,
  news_last: dates.at(-1) ?? null
}));
