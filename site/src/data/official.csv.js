// Data loader: serves ../data/processed/official.csv (written by the pipeline in ../pipeline/).
import {readFileSync} from "node:fs";
process.stdout.write(readFileSync("../data/processed/official.csv"));
