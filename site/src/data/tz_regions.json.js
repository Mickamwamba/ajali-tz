// Data loader: serves ../data/reference/tz_regions.geojson (written by the pipeline in ../pipeline/).
import {readFileSync} from "node:fs";
process.stdout.write(readFileSync("../data/reference/tz_regions.geojson"));
