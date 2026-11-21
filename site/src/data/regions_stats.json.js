// Data loader: per-region police figures for the map page, from ../data/processed/official.csv.
// Output: [{region, zone, years: {2018: {deaths, crashes, injuries, rate}}, avg: {"2018_2020": {...}, "2023_2025": {...}}}]
import {readFileSync} from "node:fs";
import {csvParse} from "d3-dsv";

const ZANZIBAR = new Set(["Kaskazini Pemba", "Kaskazini Unguja", "Kusini Pemba", "Kusini Unguja", "Mjini Magharibi"]);
const rows = csvParse(readFileSync("../data/processed/official.csv", "utf8"))
  .filter((d) => d.area_level === "region" && d.breakdown === "total" && d.source === "police_nbs");

const out = new Map();
for (const d of rows) {
  const r = out.get(d.area) ?? {region: d.area, zone: ZANZIBAR.has(d.area) ? "Zanzibar" : "Mainland", years: {}, avg: {}};
  out.set(d.area, r);
  const v = +d.value;
  const year = (r.years[d.year] ??= {});
  if (d.metric === "deaths") year.deaths = v;
  if (d.metric === "crashes") year.crashes = v;
  if (d.metric === "injuries") year.injuries = v;
  if (d.metric === "deaths_per_100k") year.rate = v;
  const period = d.year === "2020" ? "2018_2020" : d.year === "2025" ? "2023_2025" : null;
  if (period && d.metric === "deaths_avg_3yr") (r.avg[period] ??= {}).deaths = v;
  if (period && d.metric === "deaths_per_100k_avg_3yr") (r.avg[period] ??= {}).rate = v;
}
process.stdout.write(JSON.stringify([...out.values()]));
