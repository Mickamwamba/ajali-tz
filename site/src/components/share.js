// Share button: turns a chart into a PNG with its title, source line and the site name,
// then opens the phone's share sheet where available, or downloads the image.
import {html} from "npm:htl";

const SITE = "Ajali TZ · Tanzania road deaths";
const FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
const WIDTH = 1200; // output image width in pixels

// Copy each element's computed colours and font onto a clone, so the SVG keeps the
// theme's colours (CSS variables, currentColor) when it is drawn outside the page.
function inlineStyles(original, clone) {
  const src = [original, ...original.querySelectorAll("*")];
  const dst = [clone, ...clone.querySelectorAll("*")];
  src.forEach((el, i) => {
    const out = dst[i];
    if (!out || !out.setAttribute) return;
    const cs = getComputedStyle(el);
    for (const prop of ["fill", "stroke", "stroke-width", "stroke-dasharray", "fill-opacity", "stroke-opacity", "opacity", "font-size", "font-weight", "text-anchor"]) {
      const v = cs.getPropertyValue(prop);
      if (v && v !== "normal") out.setAttribute(prop, v);
    }
    if (el.tagName === "text" || el.tagName === "tspan") out.setAttribute("font-family", FONT);
  });
  // Pointer tips and hover rules are not part of the picture.
  clone.querySelectorAll('[aria-label="tip"], [aria-label="rule"]').forEach((n) => n.remove());
}

function svgToImage(svg) {
  const clone = svg.cloneNode(true);
  inlineStyles(svg, clone);
  const {width, height} = svg.getBoundingClientRect();
  clone.setAttribute("width", width);
  clone.setAttribute("height", height);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], {type: "image/svg+xml"}));
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve({img, width, height}); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Could not draw the chart")); };
    img.src = url;
  });
}

function wrap(ctx, text, maxWidth) {
  const lines = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = word; } else line = test;
  }
  if (line) lines.push(line);
  return lines;
}

// Draw title, the chart's SVGs (e.g. a legend and the plot) stacked, the source and the site name.
export async function renderShareImage(target, {title, source}) {
  const root = typeof target === "string" ? document.querySelector(target) : target;
  const svgs = [...(root?.querySelectorAll("svg") ?? [])].filter((s) => s.getBoundingClientRect().width > 40);
  if (!svgs.length) throw new Error("No chart found to share");
  const parts = await Promise.all(svgs.map(svgToImage));
  // The theme's own background and text colours (the background is set on a parent, not body).
  const probe = document.createElement("div");
  probe.style.cssText = "position:absolute;visibility:hidden;background:var(--theme-background);color:var(--theme-foreground)";
  document.body.append(probe);
  const ps = getComputedStyle(probe);
  const bg = ps.backgroundColor && ps.backgroundColor !== "rgba(0, 0, 0, 0)" ? ps.backgroundColor : "#ffffff";
  const fg = ps.color || "#111111";
  probe.remove();

  const pad = 48;
  const inner = WIDTH - 2 * pad;
  const measure = document.createElement("canvas").getContext("2d");
  measure.font = `600 40px ${FONT}`;
  const titleLines = wrap(measure, title, inner);
  measure.font = `400 22px ${FONT}`;
  const sourceLines = wrap(measure, `Source: ${source}`, inner);
  // One scale for every part, set by the widest (the plot), so a legend keeps its size relative to the chart.
  const k = inner / Math.max(...parts.map((p) => p.width));
  const scaled = parts.map((p) => ({...p, w: p.width * k, h: p.height * k}));
  const height = pad + titleLines.length * 50 + 16 + d3sum(scaled.map((p) => p.h + 12)) + 12 + sourceLines.length * 30 + 20 + 30 + pad;

  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = Math.ceil(height);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = fg;
  ctx.textBaseline = "top";
  let y = pad;
  ctx.font = `600 40px ${FONT}`;
  for (const line of titleLines) { ctx.fillText(line, pad, y); y += 50; }
  y += 16;
  for (const p of scaled) { ctx.drawImage(p.img, pad, y, p.w, p.h); y += p.h + 12; }
  y += 12;
  ctx.globalAlpha = 0.75;
  ctx.font = `400 22px ${FONT}`;
  for (const line of sourceLines) { ctx.fillText(line, pad, y); y += 30; }
  y += 20;
  ctx.globalAlpha = 1;
  ctx.font = `600 22px ${FONT}`;
  ctx.fillText(SITE, pad, y);
  return canvas;
}

function d3sum(values) { return values.reduce((a, b) => a + b, 0); }

export function shareButton(target, {title, source, filename = "ajali-tz-chart.png"}) {
  const button = html`<button type="button" class="share-button" aria-label="Share this chart as an image: ${title}">Share chart</button>`;
  button.addEventListener("click", async () => {
    const label = button.textContent;
    button.disabled = true;
    button.textContent = "Preparing…";
    try {
      const canvas = await renderShareImage(target, {title, source});
      const blob = await new Promise((r) => canvas.toBlob(r, "image/png"));
      const file = new File([blob], filename, {type: "image/png"});
      if (navigator.canShare?.({files: [file]})) {
        await navigator.share({files: [file], title, text: `${title} (${source})`}).catch(() => {});
      } else {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.append(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      }
      button.textContent = "Done";
    } catch (e) {
      console.error(e);
      button.textContent = "Couldn't make the image";
    }
    setTimeout(() => { button.textContent = label; button.disabled = false; }, 2000);
  });
  return button;
}
