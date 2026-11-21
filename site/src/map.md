---
title: Map
toc: false
---

<style>
.source { color: var(--theme-foreground-muted); font-size: 0.8rem; margin-top: 0.25rem; max-width: 46rem; }
.panel h2 { margin: 0; }
.panel .zone { color: var(--theme-foreground-muted); font-size: 0.85rem; }
.panel .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin: 0.75rem 0; }
.panel .stat b { display: block; font-size: 1.7rem; font-weight: 600; line-height: 1.1; font-variant-numeric: tabular-nums; }
.panel .stat span { font-size: 0.75rem; color: var(--theme-foreground-muted); }
.panel ul { padding-left: 1.1rem; margin: 0.4rem 0; }
.panel li { margin: 0.35rem 0; font-size: 0.85rem; }
.panel .muted { color: var(--theme-foreground-muted); font-size: 0.85rem; }
.tag { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--theme-foreground-faintest); color: var(--theme-foreground-muted); }
.controls { display: flex; flex-wrap: wrap; gap: 0.25rem 2rem; align-items: flex-start; }
</style>

```js
import {shareButton} from "./components/share.js";
const regionsGeo = FileAttachment("data/tz_regions.json").json();
const stats = FileAttachment("data/regions_stats.json").json();
const crashes = FileAttachment("data/news_crashes.json").json();
```

# Where road deaths are recorded

Police-recorded road deaths by region, averaged over three years because single-year regional numbers are small and swing a lot. Click a region, or choose one below, for its details.

<div class="controls">

```js
const period = view(Inputs.radio(new Map([["2023–2025", "2023_2025"], ["2018–2020", "2018_2020"]]), {label: "Years", value: "2023_2025"}));
```

```js
const measure = view(Inputs.radio(new Map([["Deaths per 100,000 people", "rate"], ["Deaths per year", "deaths"]]), {label: "Show", value: "rate"}));
```

```js
const showNews = view(Inputs.toggle({label: "News-reported crashes", value: true}));
```

```js
const regionInput = Inputs.select([null, ...stats.map((d) => d.region).sort()], {label: "Region", format: (d) => d ?? "Choose a region", value: null});
const region = Generators.input(regionInput);
display(regionInput);
```

</div>

```js
const fmt = d3.format(",");
const byName = new Map(stats.map((d) => [d.region, d]));
const periodLabel = period === "2023_2025" ? "2023–2025" : "2018–2020";
const valueOf = (name) => byName.get(name)?.avg[period]?.[measure];
const label = measure === "rate" ? "Deaths per 100,000 people, yearly average" : "Deaths per year, average";
const show = (v) => (v == null ? "no data" : measure === "rate" ? v.toFixed(1) : fmt(Math.round(v)));

// Fixed class breaks, so the colours mean the same thing in both periods.
const thresholds = measure === "rate" ? [2, 4, 6, 10] : [20, 40, 60, 100];
// Sequential blue: light = fewer deaths on a light page; on a dark page the low end recedes into the dark instead.
const RAMP = dark
  ? ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"]
  : ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
const NEWS = dark ? "#d95926" : "#eb6834"; // orange: a separate job (news reports), not part of the blue scale

// News reports cover only the last ~12 months, so they belong with the 2023–2025 view.
const newsPoints = crashes.filter((c) => c.lat != null && c.lon != null);
const newsSince = d3.min(newsPoints, (c) => c.crash_date);
const ranked = stats.filter((d) => valueOf(d.region) != null).sort((a, b) => valueOf(b.region) - valueOf(a.region));
const rankOf = (name) => ranked.findIndex((d) => d.region === name) + 1;
```

<div class="grid grid-cols-3">
<div class="card grid-colspan-2">

```js
function mapChart(width) {
  const news = showNews && period === "2023_2025";
  const plot = Plot.plot({
    width,
    height: Math.round(width * 0.95),
    projection: {type: "mercator", domain: regionsGeo},
    color: {type: "threshold", domain: thresholds, range: RAMP, unknown: "var(--theme-foreground-faintest)", legend: true, label, width: Math.min(width, 360)},
    r: {range: [3, 13], domain: [0, 25]},
    marks: [
      Plot.geo(regionsGeo, {fill: (d) => valueOf(d.properties.region), stroke: "var(--theme-background)", strokeWidth: 1}),
      Plot.geo(regionsGeo, {filter: (d) => d.properties.region === region, fill: "none", stroke: "currentColor", strokeWidth: 2.5}),
      news ? Plot.dot(newsPoints, {x: "lon", y: "lat", r: (d) => d.deaths ?? 1, fill: NEWS, fillOpacity: 0.9, stroke: "var(--theme-background)", strokeWidth: 1.5}) : null,
      news ? Plot.tip(newsPoints, Plot.pointer({x: "lon", y: "lat", title: (c) => `${c.crash_date} · ${c.district ?? c.region}\n${c.deaths ?? "?"} deaths, ${c.injuries ?? "?"} injured\n${c.place ?? ""}\nReported in the media`, maxRadius: 12})) : null,
      Plot.tip(regionsGeo, Plot.pointer(Plot.centroid({
        title: (d) => {
          const name = d.properties.region;
          return `${name}\n${show(valueOf(name))} ${measure === "rate" ? "deaths per 100,000" : "deaths a year"} (${periodLabel})\nClick for details`;
        }
      })))
    ]
  });
  // Clicking a region selects it in the dropdown (which also works by keyboard).
  plot.addEventListener("click", () => {
    const v = plot.value;
    const name = v?.properties?.region;
    if (name) {
      regionInput.value = name;
      regionInput.dispatchEvent(new Event("input", {bubbles: true}));
    }
  });
  return plot;
}
```

<div id="map-chart">${resize((width) => mapChart(width))}</div>
${shareButton("#map-chart", {title: `Police-recorded road deaths by region, Tanzania, ${periodLabel}: ${label.toLowerCase()}`, source: "Tanzania Police Force / NBS annual reports; 2022 census" + (showNews && period === "2023_2025" ? "; orange dots: crashes reported in the media (not a full count)" : ""), filename: `ajali-tz-map-${period}.png`})}

<p class="source">${showNews && period === "2023_2025" ? html`Orange dots: crashes <span class="tag">reported in the media</span> since ${newsSince}, sized by deaths and placed at district level. They show only crashes the news covered, mostly large ones.` : showNews ? "News-reported crashes are shown with the 2023–2025 view only: the news log starts in December 2025." : ""}</p>

</div>
<div class="card panel">

```js
const sel = region ? byName.get(region) : null;
display(sel ? regionPanel(sel) : html`<p class="muted">Click a region on the map, or choose one above, to see its deaths by year and the crashes reported in the news there.</p><p class="muted">Highest ${label.toLowerCase()} in ${periodLabel}:</p><ol>${ranked.slice(0, 5).map((d) => html`<li>${d.region}: ${show(valueOf(d.region))}</li>`)}</ol>`);

function regionPanel(s) {
  const years = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"];
  const bars = years.map((y) => ({year: y, deaths: s.years[y]?.deaths ?? null}));
  const local = crashes.filter((c) => c.region === s.region).slice(0, 5);
  const avg = s.avg[period] ?? {};
  return html`
    <h2>${s.region}</h2>
    <div class="zone">${s.zone === "Zanzibar" ? "Zanzibar" : "Tanzania Mainland"} · rank ${rankOf(s.region)} of ${ranked.length} (${periodLabel})</div>
    <div class="stats">
      <div class="stat"><b>${avg.rate?.toFixed(1) ?? "–"}</b><span>deaths per 100,000 people a year</span></div>
      <div class="stat"><b>${avg.deaths == null ? "–" : fmt(Math.round(avg.deaths))}</b><span>deaths a year on average</span></div>
    </div>
    <div id="region-chart">${Plot.plot({
      width: 300, height: 150, marginLeft: 36,
      x: {label: null, domain: years, tickFormat: (y) => `'${y.slice(2)}`},
      y: {label: "Deaths", grid: true, nice: true, ticks: 4},
      marks: [
        Plot.barY(bars.filter((d) => d.deaths != null), {x: "year", y: "deaths", fill: dark ? "#3987e5" : "#2a78d6", rx: 2, tip: true}),
        Plot.text(bars.filter((d) => d.deaths == null), {x: "year", y: 0, text: () => "n/a", dy: -8, fill: "currentColor", fillOpacity: 0.6, fontSize: 9}),
        Plot.ruleY([0])
      ]
    })}</div>
    <p class="muted">Police-recorded deaths per year. No regional figures were published for 2021 or 2022.</p>
    ${shareButton("#region-chart", {title: `${s.region}: police-recorded road deaths per year`, source: "Tanzania Police Force / NBS annual reports (no regional figures published for 2021–2022)", filename: `ajali-tz-${s.region.toLowerCase().replace(/\s+/g, "-")}.png`})}
    <h3>In the news <span class="tag">reported in the media</span></h3>
    ${local.length
      ? html`<ul>${local.map((c) => html`<li>${c.crash_date}: ${c.deaths ?? "?"} dead, ${c.injuries ?? "?"} injured${c.place ? html`, ${c.place}` : ""} · <a href="${c.sources[0].url}" target="_blank" rel="noopener">${c.sources[0].outlet}</a></li>`)}</ul>`
      : html`<p class="muted">No crashes in ${s.region} in the news log yet.</p>`}
    <p><a href="./crashes">All news-reported crashes →</a></p>`;
}
```

</div>
</div>

<p class="source">Source: Tanzania Police Force / NBS annual reports, police regions merged into the 31 administrative regions (Ilala, Temeke and Kinondoni into Dar es Salaam; Rufiji into Pwani; Tarime–Rorya into Mara). Rates use the 2022 census population for every year, so compare regions within a period rather than one region across periods. High rates in Zanzibar may partly reflect more complete recording there. Boundaries: NBS / UN OCHA, 2018.</p>

<details>
<summary>Show all regions as a table</summary>

```js
display(Inputs.table(stats.map((d) => ({
  region: d.region, zone: d.zone,
  rate_2023_2025: d.avg["2023_2025"]?.rate, deaths_2023_2025: d.avg["2023_2025"]?.deaths,
  rate_2018_2020: d.avg["2018_2020"]?.rate, deaths_2018_2020: d.avg["2018_2020"]?.deaths
})), {
  sort: "rate_2023_2025", reverse: true, rows: 12,
  header: {region: "Region", zone: "Zone", rate_2023_2025: "Per 100k, 2023–25", deaths_2023_2025: "Deaths/yr, 2023–25", rate_2018_2020: "Per 100k, 2018–20", deaths_2018_2020: "Deaths/yr, 2018–20"},
  format: {deaths_2023_2025: (v) => v == null ? "" : Math.round(v), deaths_2018_2020: (v) => v == null ? "" : Math.round(v)}
}));
```

</details>
