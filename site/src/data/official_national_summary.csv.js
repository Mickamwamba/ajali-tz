// Data loader: serves ../data/processed/official_national_summary.csv (written by the pipeline in ../pipeline/).
import {readFileSync} from "node:fs";
process.stdout.write(readFileSync("../data/processed/official_national_summary.csv"));
