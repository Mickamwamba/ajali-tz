// Data loader: serves ../data/processed/news_crashes.csv (approved news-reported crashes) for download.
import {readFileSync} from "node:fs";
process.stdout.write(readFileSync("../data/processed/news_crashes.csv"));
