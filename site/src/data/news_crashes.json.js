// Data loader: serves ../data/processed/news_crashes.json (written by the pipeline in ../pipeline/).
import {readFileSync} from "node:fs";
process.stdout.write(readFileSync("../data/processed/news_crashes.json"));
