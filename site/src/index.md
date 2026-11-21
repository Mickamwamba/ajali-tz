---
title: Tanzania road deaths
toc: false
---

<style>
/* Chart colours: reference palette slots 1 (blue) and 2 (orange), validated as an adjacent pair
   for colour-blind readers in light and dark mode. Dark steps are their own values, not a flip. */
:root {
  --series-police: #2a78d6;
  --series-who: #eb6834;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) { --series-police: #3987e5; --series-who: #d95926; }
}
:root[data-theme="dark"] { --series-police: #3987e5; --series-who: #d95926; }

.lede { font-size: 1.35rem; line-height: 1.45; max-width: 46rem; margin: 0.5rem 0 1.5rem; text-wrap: pretty; }
.lede strong { font-variant-numeric: tabular-nums; }
.card h2 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--theme-foreground-muted); font-weight: 500; }
.big { font-size: 2.4rem; font-weight: 600; line-height: 1.1; font-variant-numeric: tabular-nums; margin: 0.25rem 0; }
.sub { color: var(--theme-foreground-muted); font-size: 0.85rem; font-variant-numeric: tabular-nums; }
.source { color: var(--theme-foreground-muted); font-size: 0.8rem; margin-top: 0.25rem; }
.tag { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 1px 6px; border-radius: 4px; border: 1px solid var(--theme-foreground-faintest); color: var(--theme-foreground-muted); }
.next { display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem; margin-top: 1rem; }
</style>

```js
const summary = FileAttachment("data/official_national_summary.csv").csv({typed: true});
const crashes = FileAttachment("data/news_crashes.json").json();
```

```js
const fmt = d3.format(",");
const police = summary.filter((d) => d.police_deaths != null);
const latest = police.at(-1);
const previous = police.find((d) => d.year === latest.year - 1);
const change = previous ? (latest.police_deaths - previous.police_deaths) / previous.police_deaths : null;
// WHO's own published count (the other years are derived from WHO's published rate).
const whoPublished = summary.find((d) => d.who_estimated_deaths != null && !/derived/.test(d.notes ?? ""));
const ratios = summary.filter((d) => d.who_to_police_ratio != null).map((d) => d.who_to_police_ratio);

// News: crashes reported in the media in the 30 days up to today.
const today = new Date();
const since = d3.utcDay.offset(today, -30);
const recent = crashes.filter((c) => c.crash_date && new Date(c.crash_date) >= since);
const recentDeaths = d3.sum(recent, (c) => c.deaths ?? 0);
```

# Tanzania road deaths

<p class="lede">Police recorded <strong>${fmt(latest.police_deaths)}</strong> road deaths in Tanzania in ${latest.year}. The World Health Organization estimates the real toll is far higher: <strong>${fmt(whoPublished.who_estimated_deaths)}</strong> deaths in ${whoPublished.year}, about <strong>${whoPublished.who_to_police_ratio} times</strong> the ${fmt(whoPublished.police_deaths)} police recorded that year.</p>

<div class="grid grid-cols-3">
  <div class="card">
    <h2>Police-recorded deaths, ${latest.year}</h2>
    <div class="big">${fmt(latest.police_deaths)}</div>
    <div class="sub">${change == null ? "" : `${change < 0 ? "Down" : "Up"} ${Math.abs(change * 100).toFixed(0)}% from ${fmt(previous.police_deaths)} in ${previous.year}`}</div>
    <div class="source">Tanzania Police Force / NBS</div>
  </div>
  <div class="card">
    <h2>WHO-estimated deaths, ${whoPublished.year}</h2>
    <div class="big">${fmt(whoPublished.who_estimated_deaths)}</div>
    <div class="sub">95% range ${fmt(whoPublished.who_estimated_deaths_low)}–${fmt(whoPublished.who_estimated_deaths_high)}. Between ${d3.min(ratios)} and ${d3.max(ratios)} times the police count in 2018–2023.</div>
    <div class="source">WHO Global status report on road safety 2023</div>
  </div>
  <div class="card">
    <h2>Crashes in the news, last 30 days</h2>
    <div class="big">${recent.length}</div>
    <div class="sub">${fmt(recentDeaths)} deaths in those reports · <a href="./crashes">See the list</a></div>
    <div class="source"><span class="tag">Reported in the media</span> Not a full count</div>
  </div>
</div>

## Official count against the WHO estimate

<p class="source">Road deaths per year. Shaded: WHO's 95% range. After 2021 the WHO line is dashed: those years are projections with wider uncertainty, and WHO has not yet published estimates for 2024–2025.</p>

```js
function trendChart(width) {
  const who = summary.filter((d) => d.who_estimated_deaths != null);
  const whoMeasured = who.filter((d) => d.year <= 2021);
  const whoProjected = who.filter((d) => d.year >= 2021);
  return Plot.plot({
    width,
    height: 340,
    marginLeft: 52,
    marginRight: width < 520 ? 96 : 110, // room for the end labels
    // On phones, label every other year so the labels don't collide.
    x: {label: null, tickFormat: "d", ticks: police.map((d) => d.year).filter((y, i) => width >= 520 || i % 2 === 0)},
    y: {label: "Deaths", grid: true, nice: true, zero: true, tickFormat: (d) => fmt(d)},
    marks: [
      Plot.areaY(who, {x: "year", y1: "who_estimated_deaths_low", y2: "who_estimated_deaths_high", fill: "var(--series-who)", fillOpacity: 0.14, curve: "linear"}),
      Plot.lineY(whoMeasured, {x: "year", y: "who_estimated_deaths", stroke: "var(--series-who)", strokeWidth: 2}),
      Plot.lineY(whoProjected, {x: "year", y: "who_estimated_deaths", stroke: "var(--series-who)", strokeWidth: 2, strokeDasharray: "5,4"}),
      Plot.dot(who, {x: "year", y: "who_estimated_deaths", r: 4, fill: "var(--series-who)", stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.lineY(police, {x: "year", y: "police_deaths", stroke: "var(--series-police)", strokeWidth: 2}),
      Plot.dot(police, {x: "year", y: "police_deaths", r: 4, fill: "var(--series-police)", stroke: "var(--theme-background)", strokeWidth: 2}),
      // Direct labels at each line's last point, in text colour (the line beside them carries the identity).
      Plot.text([who.at(-1)], {x: "year", y: "who_estimated_deaths", text: () => "WHO estimate", dx: 10, textAnchor: "start", fill: "currentColor", fontWeight: 600}),
      Plot.text([police.at(-1)], {x: "year", y: "police_deaths", text: () => "Police-recorded", dx: 10, textAnchor: "start", fill: "currentColor", fontWeight: 600}),
      Plot.ruleX(summary, Plot.pointerX({x: "year", stroke: "var(--theme-foreground-faint)"})),
      Plot.tip(summary, Plot.pointerX({
        x: "year",
        y: (d) => d.who_estimated_deaths ?? d.police_deaths,
        title: (d) => [
          `${d.year}`,
          `Police-recorded: ${fmt(d.police_deaths)}`,
          d.who_estimated_deaths != null
            ? `WHO estimate: ${fmt(d.who_estimated_deaths)} (${fmt(d.who_estimated_deaths_low)}–${fmt(d.who_estimated_deaths_high)})`
            : "WHO estimate: not yet published",
          d.who_to_police_ratio != null ? `WHO is ${d.who_to_police_ratio}× the police count` : null,
          d.year > 2021 && d.who_estimated_deaths != null ? "WHO projection" : null
        ].filter(Boolean).join("\n")
      }))
    ]
  });
}
```

<div class="card">${resize((width) => trendChart(width))}</div>

<p class="source">Sources: Tanzania Police Force / National Bureau of Statistics, Crime and Traffic Incidents Statistics reports 2018–2025 (2021 from the NBS Statistical Abstract 2022); WHO Global Health Observatory and Global status report on road safety 2023. WHO figures other than 2021 are WHO's published rate per 100,000 people multiplied by the population.</p>

<details>
<summary>Show the numbers as a table</summary>

```js
display(Inputs.table(summary, {
  columns: ["year", "police_crashes", "police_deaths", "police_injuries", "who_estimated_deaths", "who_estimated_deaths_low", "who_estimated_deaths_high", "who_to_police_ratio", "notes"],
  header: {
    year: "Year", police_crashes: "Crashes (police)", police_deaths: "Deaths (police)", police_injuries: "Injured (police)",
    who_estimated_deaths: "Deaths (WHO est.)", who_estimated_deaths_low: "WHO low", who_estimated_deaths_high: "WHO high",
    who_to_police_ratio: "WHO ÷ police", notes: "Notes"
  },
  format: {year: (y) => String(y)},
  rows: 10
}));
```

</details>

<div class="next">
  <a href="./map">Where crashes happen: the map →</a>
  <a href="./crashes">Recent crashes reported in the news →</a>
  <a href="./about">Where these numbers come from →</a>
</div>
