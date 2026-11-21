---
title: Recent crashes
toc: false
---

<style>
.tag { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--theme-foreground-faintest); color: var(--theme-foreground-muted); white-space: nowrap; }
.intro { max-width: 46rem; }
.summary { font-size: 1.15rem; margin: 0.5rem 0 1rem; font-variant-numeric: tabular-nums; }
.filters { display: flex; flex-wrap: wrap; gap: 0.25rem 1.5rem; align-items: flex-start; }
.list { display: flex; flex-direction: column; gap: 0.75rem; }
.crash { display: grid; grid-template-columns: 7.5rem minmax(0, 1fr); gap: 0.25rem 1.25rem; padding: 0.9rem 1rem; border: 1px solid var(--theme-foreground-faintest); border-radius: 8px; background: var(--theme-background-alt); }
.crash .toll b { display: block; font-size: 1.6rem; font-weight: 600; line-height: 1.1; font-variant-numeric: tabular-nums; }
.crash .toll span { font-size: 0.75rem; color: var(--theme-foreground-muted); display: block; }
.crash .when { font-size: 0.8rem; color: var(--theme-foreground-muted); font-variant-numeric: tabular-nums; }
.crash h3 { margin: 0.1rem 0 0.25rem; font-size: 1.02rem; text-wrap: pretty; }
.crash .facts { font-size: 0.85rem; color: var(--theme-foreground-muted); display: flex; flex-wrap: wrap; gap: 0.2rem 0.9rem; }
.crash .facts b { color: var(--theme-foreground); font-weight: 500; }
.crash .sources { font-size: 0.85rem; margin-top: 0.4rem; display: flex; flex-wrap: wrap; gap: 0.2rem 0.9rem; }
.empty { color: var(--theme-foreground-muted); padding: 1rem 0; }
.source { color: var(--theme-foreground-muted); font-size: 0.8rem; max-width: 46rem; }
@media (max-width: 520px) { .crash { grid-template-columns: 1fr; } .crash .toll { display: flex; gap: 1.25rem; } }
</style>

```js
import {shareButton} from "./components/share.js";
const crashes = FileAttachment("data/news_crashes.json").json();
```

# Crashes reported in the news

<p class="intro">Road crashes in Tanzania found in five news outlets (The Citizen, Mwananchi, Daily News, HabariLeo, The Chanzo) and turned into records by an automated process, then checked. <span class="tag">Reported in the media</span> These are only the crashes the news covered, mostly large ones. They are <b>not</b> the total: police record far more, and WHO estimates more still.</p>

```js
const fmt = d3.format(",");
const VEHICLES = {
  bus: "Bus", minibus: "Minibus / daladala", lorry: "Lorry / truck", fuel_tanker: "Fuel tanker", car: "Car",
  pickup_or_van: "Pickup / van", motorcycle: "Motorcycle / bodaboda", bajaji: "Bajaji", bicycle: "Bicycle",
  cart: "Cart", train: "Train", other: "Other vehicle"
};
const CAUSES = {
  overspeeding: "Overspeeding", dangerous_driving: "Dangerous driving", careless_overtaking: "Careless overtaking",
  drunk_driving: "Drunk driving", fatigue: "Driver fatigue", vehicle_defect: "Vehicle defect", brake_failure: "Brake failure",
  tyre_burst: "Tyre burst", poor_road: "Poor road", weather: "Weather", pedestrian_error: "Pedestrian error", other: "Other cause"
};
const VICTIMS = {driver: "drivers", passenger: "passengers", pedestrian: "pedestrians", motorcyclist: "motorcyclists", cyclist: "cyclists", other: "others"};
// Group vehicles into the families readers search by (a bus filter should also find minibuses).
const FAMILY = {bus: "bus", minibus: "bus", lorry: "lorry", fuel_tanker: "lorry", car: "car", pickup_or_van: "car", motorcycle: "motorcycle", bajaji: "bajaji", bicycle: "bicycle", cart: "other", train: "train", other: "other"};
const FAMILY_LABEL = new Map([["Bus or minibus", "bus"], ["Lorry, truck or tanker", "lorry"], ["Car, pickup or van", "car"], ["Motorcycle / bodaboda", "motorcycle"], ["Bajaji", "bajaji"], ["Bicycle", "bicycle"], ["Train (at a crossing)", "train"]]);

const regions = [...new Set(crashes.map((c) => c.region).filter(Boolean))].sort();
const dates = crashes.map((c) => c.crash_date).filter(Boolean).sort();
const vehicleList = (c) => {
  const counts = d3.rollup(c.vehicles, (v) => v.length, (v) => v);
  return [...counts].map(([v, n]) => (n > 1 ? `${n} × ${VEHICLES[v] ?? v}` : VEHICLES[v] ?? v)).join(", ");
};
```

<div class="filters">

```js
const query = view(Inputs.text({label: "Search", placeholder: "Place, district, road…", autocomplete: "off"}));
```

```js
const region = view(Inputs.select([null, ...regions], {label: "Region", format: (d) => d ?? "All regions"}));
```

```js
const family = view(Inputs.select(new Map([["All vehicles", null], ...FAMILY_LABEL]), {label: "Vehicle"}));
```

```js
const from = view(Inputs.date({label: "From", value: dates[0], min: dates[0], max: dates.at(-1)}));
```

```js
const to = view(Inputs.date({label: "To", value: dates.at(-1), min: dates[0], max: dates.at(-1)}));
```

</div>

```js
const q = (query ?? "").trim().toLowerCase();
const fromIso = from ? from.toISOString().slice(0, 10) : null;
const toIso = to ? to.toISOString().slice(0, 10) : null;
const filtered = crashes.filter((c) =>
  (!region || c.region === region) &&
  (!family || c.vehicles.some((v) => FAMILY[v] === family)) &&
  (!fromIso || (c.crash_date && c.crash_date >= fromIso)) &&
  (!toIso || (c.crash_date && c.crash_date <= toIso)) &&
  (!q || [c.place, c.district, c.region, ...c.sources.map((s) => s.title)].some((t) => (t ?? "").toLowerCase().includes(q)))
);
const deaths = d3.sum(filtered, (c) => c.deaths ?? 0);
const injured = d3.sum(filtered, (c) => c.injuries ?? 0);
```

<p class="summary"><b>${filtered.length}</b> ${filtered.length === 1 ? "crash" : "crashes"} reported in the news, with <b>${fmt(deaths)}</b> deaths and <b>${fmt(injured)}</b> injured${filtered.length < crashes.length ? html` <span class="tag">filtered</span>` : ""}.</p>

```js
function monthly(width) {
  const byMonth = d3.rollups(filtered.filter((c) => c.crash_date), (v) => d3.sum(v, (c) => c.deaths ?? 0), (c) => c.crash_date.slice(0, 7))
    .map(([month, deaths]) => ({month: new Date(`${month}-01T00:00:00Z`), deaths}));
  if (!byMonth.length) return html`<p class="empty">No crashes match these filters.</p>`;
  const months = d3.utcMonth.range(d3.utcMonth.floor(d3.min(byMonth, (d) => d.month)), d3.utcMonth.offset(d3.max(byMonth, (d) => d.month), 1));
  return Plot.plot({
    width, height: 160, marginLeft: 36,
    x: {type: "band", label: null, tickFormat: (d) => d3.utcFormat("%b %y")(d), domain: months,
        // On phones, label every third month so the labels don't collide.
        ticks: width < 520 ? months.filter((m, i) => i % 3 === 0) : months},
    y: {label: "Deaths", grid: true, nice: true, ticks: 4},
    marks: [
      Plot.barY(byMonth, {x: "month", y: "deaths", fill: dark ? "#3987e5" : "#2a78d6", rx: 2, tip: {format: {x: (d) => d3.utcFormat("%B %Y")(d), y: true}}}),
      Plot.ruleY([0])
    ]
  });
}
```

<div class="card">
<h2>Deaths in news-reported crashes, by month</h2>
<div id="monthly-chart">${resize((width) => monthly(width))}</div>
<p class="source">Months with no bar had no crash in the news log. More coverage in a month usually means more news reports, not necessarily more crashes.</p>
${shareButton("#monthly-chart", {title: `Deaths in road crashes reported in the news, Tanzania, by month${filtered.length < crashes.length ? " (filtered)" : ""}`, source: "The Citizen, Mwananchi, Daily News, HabariLeo, The Chanzo, compiled by Ajali TZ. Reported in the media: not a full count", filename: "ajali-tz-news-by-month.png"})}
</div>

```js
const showAll = view(Inputs.toggle({label: `Show all ${filtered.length}`, value: false}));
```

```js
const shown = showAll ? filtered : filtered.slice(0, 30);
display(shown.length ? html`<div class="list">${shown.map(crashCard)}</div>` : html`<p class="empty">No crashes match these filters. Try a wider date range or "All regions".</p>`);
if (!showAll && filtered.length > 30) display(html`<p class="source">Showing the 30 most recent. Switch on "Show all" above to see every crash.</p>`);

function causeText(c) {
  const cat = c.reported_cause && c.reported_cause !== "not_reported" ? c.reported_cause : null;
  if (!cat) return c.cause_detail ?? null;
  if (cat === "other") return c.cause_detail ?? null; // the detail says more than "other"
  return c.cause_detail ? `${CAUSES[cat] ?? cat} (${c.cause_detail})` : CAUSES[cat] ?? cat;
}

function crashCard(c) {
  const where = [c.place, c.district, c.region].filter(Boolean);
  // place often already names the district; drop exact repeats
  const uniqueWhere = where.filter((w, i) => where.findIndex((x) => x.toLowerCase() === w.toLowerCase()) === i);
  const victims = c.victim_types.map((v) => VICTIMS[v] ?? v).join(", ");
  return html`<article class="crash">
    <div class="toll">
      <div><b>${c.deaths ?? "?"}</b><span>${c.deaths === 1 ? "death" : "deaths"}</span></div>
      <div><b>${c.injuries ?? "?"}</b><span>injured</span></div>
    </div>
    <div>
      <div class="when">${c.crash_date ? d3.utcFormat("%-d %B %Y")(new Date(c.crash_date)) : "Date not reported"}</div>
      <h3>${uniqueWhere.join(", ") || "Location not reported"}</h3>
      <div class="facts">
        <span><b>Vehicles:</b> ${vehicleList(c) || "not reported"}</span>
        ${victims ? html`<span><b>Victims:</b> ${victims}</span>` : ""}
        ${causeText(c) ? html`<span><b>Reported cause:</b> ${causeText(c)}</span>` : ""}
      </div>
      <div class="sources">${c.sources.map((s) => html`<a href="${s.url}" target="_blank" rel="noopener">${s.outlet}: ${s.title}</a>`)}</div>
    </div>
  </article>`;
}
```

<p class="source">How these records are made: an automated process collects articles from the five outlets every three hours, uses AI to pick out reports of specific road crashes in Tanzania and extract the facts, merges reports of the same crash, and holds uncertain records for a person to check. Article text is not stored, and no names are recorded. "?" means the reports did not give that figure. In a hand check of 45 records, all 360 fields were correct. <a href="./about">More about the method</a> · <a href="./data/news_crashes.csv" download="ajali-tz-news-crashes.csv">Download all crashes (CSV)</a></p>
