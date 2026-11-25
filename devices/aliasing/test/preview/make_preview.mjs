#!/usr/bin/env node
// Preview of the Aliasing face without Max: renders the real painter and display bundles
// (devices/aliasing/aliasing_paint_*.js, aliasing_display.js) into HTML canvases through a small
// mgraphics -> Canvas 2D adapter, with the boxes, ranges and initial values of Aliasing.amxd and
// the table / display data of a host render (test/host: drone.table.f32, drone.heads.f32).
// One canvas per page (LFO · Env, Mod, Tone, Global) plus variants, on Live's dark and light device
// backgrounds with the theme panels (D22, colours as the pages script computes them).
// Fonts differ from Live (no Ableton Sans in the browser); this is for layout review only.
//
//   node devices/aliasing/test/preview/make_preview.mjs OUT.html [SHELL.amxd] [variants]
// "variants": the section power switches (DRIVE, BAND, RESONATOR, LIMITER) in the current style and
// alternatives (A square switch, B power symbol left, C plain clickable title, D title + On/Off pill,
// E power symbol right of the title),
// Tone and Global pages, dark and light: a mock-up for the user's choice (2026-11-25).
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dev = join(here, "..", "..");
const root = join(dev, "..", "..");
const out = process.argv[2];
const MODE = process.argv[4] || "";
if (!out) {
	console.error("usage: node make_preview.mjs OUT.html");
	process.exit(2);
}

function readAmxd(path) {
	const buf = readFileSync(path);
	const i = buf.indexOf("ptch");
	const n = buf.readUInt32LE(i + 4);
	return JSON.parse(buf.subarray(i + 8, i + 8 + n).toString("utf8").replace(/\0+$/, ""));
}
const pat = readAmxd(process.argv[3] || join(dev, "Aliasing.amxd")).patcher;
const boxes = pat.boxes.map((b) => b.box).filter((b) => b.presentation && b.presentation_rect);
const painters = {};
for (const b of boxes) {
	const f = b.jspainterfile;
	if (f && !(f in painters)) painters[f] = readFileSync(join(dev, f), "utf8");
}
const display = readFileSync(join(dev, "aliasing_display.js"), "utf8");
function f32(p) {
	if (!existsSync(p)) return null;
	const b = readFileSync(p);
	return Array.from(new Float32Array(b.buffer, b.byteOffset, b.length / 4)).map((x) => Math.round(x * 1e5) / 1e5);
}
const table = f32(join(root, "build/aliasing/host/drone.table.f32"));
const heads = f32(join(root, "build/aliasing/host/drone.heads.f32"));

const html = `<!doctype html><html><head><meta charset="utf-8"><title>Aliasing face preview</title>
<style>body{background:#111;color:#bbb;font:12px -apple-system,Helvetica,sans-serif;margin:16px}
#root.grid{display:grid;grid-template-columns:repeat(2,max-content);gap:4px 28px}#root.grid canvas{zoom:1.5}
h2{font-size:12px;font-weight:600;margin:14px 0 4px}canvas{display:block;border-radius:2px;max-width:100%;height:auto!important}</style></head><body>
<div id="root"></div>
<script>
const BOXES = ${JSON.stringify(boxes)};
const MODE = ${JSON.stringify(MODE)};
const PAINTERS = ${JSON.stringify(painters)};
const DISPLAY = ${JSON.stringify(display)};
const TABLE = ${JSON.stringify(table)};
const HEADS = ${JSON.stringify(heads)};
const W = 968, H = 169;
function mgFor(ctx, w, h) {
  let fontSize = 9, fontName = "";
  const mg = {
    size: [w, h], relative_coords: 0, autofill: 0,
    init() {}, redraw() {},
    set_source_rgba(r, g, b, a) { if (Array.isArray(r)) [r, g, b, a] = r; const c = "rgba(" + [r*255|0, g*255|0, b*255|0, a ?? 1].join(",") + ")"; ctx.fillStyle = c; ctx.strokeStyle = c; },
    move_to(x, y) { ctx.moveTo(x, y); }, line_to(x, y) { ctx.lineTo(x, y); }, close_path() { ctx.closePath(); },
    curve_to(a, b, c, d, e, f) { ctx.bezierCurveTo(a, b, c, d, e, f); },
    rectangle(x, y, ww, hh) { ctx.rect(x, y, ww, hh); },
    rectangle_rounded(x, y, ww, hh, ow, oh) { ctx.roundRect(x, y, ww, hh, Math.min(ow / 2, ww / 2, hh / 2)); },
    arc(x, y, r, a1, a2) { ctx.moveTo(x + r * Math.cos(a1), y + r * Math.sin(a1)); ctx.arc(x, y, r, a1, a2, false); },
    ellipse(x, y, ww, hh) { ctx.moveTo(x + ww, y + hh / 2); ctx.ellipse(x + ww / 2, y + hh / 2, ww / 2, hh / 2, 0, 0, Math.PI * 2); },
    fill() { ctx.fill(); ctx.beginPath(); }, stroke() { ctx.stroke(); ctx.beginPath(); },
    set_line_width(lw) { ctx.lineWidth = lw; }, set_line_cap(c) { ctx.lineCap = c; }, set_line_join(j) { ctx.lineJoin = j; },
    select_font_face(n) { fontName = n; ctx.font = (n.includes("Bold") ? "600 " : "500 ") + fontSize + "px Inter, Helvetica, sans-serif"; },
    set_font_size(s) { fontSize = s; mg.select_font_face(fontName); },
    show_text(s) { const p = ctx.__p || [0, 0]; ctx.fillText(s, p[0], p[1]); },
    text_measure(s) { return [ctx.measureText(s).width, fontSize]; },
  };
  const mt = mg.move_to; mg.move_to = (x, y) => { ctx.__p = [x, y]; mt(x, y); };
  return mg;
}
function boxMock(b) {
  const vo = (b.saved_attribute_attributes || {}).valueof || {};
  const enumL = vo.parameter_enum;
  const attrs = {
    _parameter_type: vo.parameter_type ?? 0,
    _parameter_range: enumL ? enumL : [vo.parameter_mmin ?? 0, vo.parameter_mmax ?? 1],
    _parameter_exponent: vo.parameter_exponent ?? 1,
    _parameter_unitstyle: vo.parameter_unitstyle ?? 1,
    _parameter_units: vo.parameter_units ?? "",
    _parameter_shortname: vo.parameter_shortname ?? "",
    text: b.text ?? "", texton: b.texton ?? b.text ?? "", active: b.__active ?? 1,
    num_lines_presentation: b.num_lines_presentation ?? 1,
  };
  return { varname: b.varname, getattr: (n) => (n in attrs ? attrs[n] : null), setattr() {},
           getvalueof: () => (b.__value ?? (vo.parameter_initial ? vo.parameter_initial[0] : 0)) };
}
function symLabelOf(k) { return k <= 0 ? "curve" : k <= 3 ? "skew" : k === 5 ? "duty" : k === 7 ? "smooth" : "width"; }
function panelColor(bg) {
  const lum = 0.2126 * bg[0] + 0.7152 * bg[1] + 0.0722 * bg[2];
  const c = lum > 0.5 ? bg.map((x) => x * 0.92) : bg.map((x) => x + (1 - x) * 0.06);
  return "rgb(" + c.map((x) => Math.round(x * 255)).join(",") + ")";
}
const PAGES = ["lfo", "mod", "tone", "out"];
function visible(b, st) {
  const parts = String(b.varname || "").split("_");
  if (parts.length < 2) return !b.hidden;
  const [area, cond] = parts;
  let ok;
  if (PAGES.includes(area)) ok = PAGES.indexOf(area) === st.page;
  else if (area === "tbl") ok = st.page !== 2;
  else if (area === "w" || area === "r") ok = true;
  else return !b.hidden;
  let c = true;
  if ((cond === "free" || cond === "sync") && (area === "w" || area === "r")) { const m = area === "w" ? st.wmode : st.rmode; c = cond === "free" ? m === 0 : m === 1; }
  if (cond === "hz1" || cond === "sy1") c = (st.l1mode === 0) === (cond === "hz1");
  if (cond === "hz2" || cond === "sy2") c = (st.l2mode === 0) === (cond === "hz2");
  if (cond === "symlbl" && area === "w") c = symLabelOf(st.wshape ?? 1) === parts[2];
  return ok && c;
}
const BG = { dark: [0x36 / 255, 0x36 / 255, 0x36 / 255], light: [0xa5 / 255, 0xa5 / 255, 0xa5 / 255] }; // Live 12 Neutral Medium
// greying of switched-off sections (pages_model.ts activeFor, D17/D19)
function idle(b, values) {
  const n = String(b.varname || ""), v = (k, d) => (values && k in values ? values[k] : d);
  if (/_on$/.test(n)) return false;
  if (n === "tone_drive") return !v("tone_drive_on", 1);
  if (n.startsWith("tone_band_")) return !v("tone_band_on", 1);
  if (n.startsWith("tone_res_")) return !v("tone_res_on", 0);
  if (n.startsWith("out_lim_")) return !v("out_lim_on", 1);
  return false;
}
// section power switch styles for the variants mock-up
function drawSwitch(ctx, b, v, dark, on) {
  const C = dark ? { sel: "#d6d6d6", selFg: "#1b1b1b", track: "#5c5c5c", title: "#d2d2d2" }
                 : { sel: "#1f1f1f", selFg: "#efefef", track: "#6e6e6e", title: "#111111" };
  const [x, y, w, h] = b.presentation_rect;
  const t = b.text;
  ctx.save();
  ctx.font = "600 9px Inter, Helvetica, sans-serif";
  const title = (tx) => { ctx.globalAlpha = on ? 1 : 0.45; ctx.fillStyle = C.title; ctx.fillText(t, tx, y + 10); ctx.globalAlpha = 1; return ctx.measureText(t).width; };
  if (v === "A") {
    ctx.beginPath(); ctx.roundRect(x + 0.5, y + 1.5, 10, 10, 2);
    if (on) { ctx.fillStyle = C.sel; ctx.fill(); } else { ctx.strokeStyle = C.track; ctx.lineWidth = 1; ctx.stroke(); }
    title(x + 15);
  } else if (v === "B") {
    const cx = x + 6, cy = y + 6.5;
    ctx.beginPath(); ctx.arc(cx, cy, 5.5, 0, Math.PI * 2);
    if (on) { ctx.fillStyle = C.sel; ctx.fill(); } else { ctx.strokeStyle = C.track; ctx.lineWidth = 1; ctx.stroke(); }
    ctx.strokeStyle = on ? C.selFg : C.track; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(cx, cy, 2.8, -Math.PI / 2 + 0.75, Math.PI * 1.5 - 0.75); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy - 3.8); ctx.lineTo(cx, cy - 0.8); ctx.stroke();
    title(x + 15);
  } else if (v === "E") {
    const tw = title(x), cx = x + tw + 4 + 4.5, cy = y + 6.5;
    ctx.beginPath(); ctx.arc(cx, cy, 4.5, 0, Math.PI * 2);
    if (on) { ctx.fillStyle = C.sel; ctx.fill(); } else { ctx.strokeStyle = C.track; ctx.lineWidth = 1; ctx.stroke(); }
    ctx.strokeStyle = on ? C.selFg : C.track; ctx.lineWidth = 1.1; ctx.lineCap = "round";
    ctx.beginPath(); ctx.arc(cx, cy, 2.3, -Math.PI / 2 + 0.75, Math.PI * 1.5 - 0.75); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy - 3.1); ctx.lineTo(cx, cy - 0.7); ctx.stroke();
  } else if (v === "C") {
    title(x);
  } else if (v === "D") {
    const tw = title(x), px = x + tw + 5, pw = 24;
    ctx.beginPath(); ctx.roundRect(px + 0.5, y + 0.5, pw, h - 1, (h - 1) / 2);
    if (on) { ctx.fillStyle = C.sel; ctx.fill(); } else { ctx.strokeStyle = C.track; ctx.lineWidth = 1; ctx.stroke(); }
    ctx.font = "500 8px Inter, Helvetica, sans-serif"; ctx.textAlign = "center";
    ctx.fillStyle = on ? C.selFg : C.title; ctx.fillText(on ? "On" : "Off", px + pw / 2 + 0.5, y + 9.5);
  }
  ctx.restore();
}
function render(title, st, dark, opts) {
  if (only !== null && !title.toLowerCase().startsWith(only.toLowerCase())) return;
  opts = opts || {};
  const root = document.getElementById("root");
  const cell = document.createElement("div"); root.appendChild(cell);
  const h2 = document.createElement("h2"); h2.textContent = title; cell.appendChild(h2);
  const crop = opts.crop || [0, 0, W, H];
  const cv = document.createElement("canvas"); const S = 2;
  cv.width = crop[2] * S; cv.height = crop[3] * S; cv.style.width = crop[2] + "px"; cv.style.height = crop[3] + "px"; cell.appendChild(cv);
  const ctx = cv.getContext("2d"); ctx.scale(S, S); ctx.translate(-crop[0], -crop[1]);
  const switches = [];
  const bg = dark ? BG.dark : BG.light;
  ctx.fillStyle = "rgb(" + bg.map((x) => Math.round(x * 255)).join(",") + ")"; ctx.fillRect(0, 0, W, H);
  const getcolor = () => (dark ? [0.8, 0.8, 0.8, 1] : [0.12, 0.12, 0.12, 1]);
  const max = { getcolor };
  const rank = (b) => (b.maxclass === "panel" ? -2 : b.maxclass === "v8ui" ? -1 : 0);
  const order = [...BOXES].sort((a, b) => rank(a) - rank(b));
  for (const b0 of order) {
    let b = st.values && b0.varname in st.values ? { ...b0, __value: st.values[b0.varname] } : b0;
    if (opts.rects && b.varname in opts.rects) b = { ...b, presentation_rect: opts.rects[b.varname] };
    if (idle(b, st.values)) b = { ...b, __active: 0 };
    if (b.maxclass !== "panel" && !visible(b, st)) continue;
    if (opts.variant && opts.variant !== "P" && b.maxclass === "live.text" && /_on$/.test(String(b.varname))) {
      switches.push(b);
      continue;
    }
    const [x, y, w, h] = b.varname === "display" && st.page === 2 ? [308, 6, 328, 157] : b.presentation_rect; // D31
    ctx.save(); ctx.translate(x, y); ctx.beginPath();
    const mg = mgFor(ctx, w, h);
    try {
      if (b.maxclass === "panel") {
        ctx.fillStyle = panelColor(bg); ctx.beginPath(); ctx.roundRect(0, 0, w, h, 4); ctx.fill();
      } else if (b.maxclass === "v8ui") {
        const store = { atab: TABLE, aheads: HEADS };
        class Buffer { constructor(n) { this.d = store[n]; this.ch = n === "atab" ? 5 : 10; this.fr = n === "atab" ? 1024 : 5; }
          peek(c, f, k) { const o = []; for (let i = 0; i < k; i++) o.push(this.d ? this.d[(c - 1) * this.fr + f + i] : 0); return o; } poke() {} }
        class Dict { constructor(n) { this.name = n || "d"; } parse() {} get() { return null; } }
        class Task { constructor() { this.running = false; } repeat() {} cancel() {} }
        const api = new Function("mgraphics", "Buffer", "Dict", "Task", "outlet", "post", "max", "inlets", "outlets",
          DISPLAY + "\\n;return { paint, buffers, page, mode, pv };")(mg, Buffer, Dict, Task, () => {}, () => {}, max, 0, 0);
        api.buffers("atab", "aheads"); api.page(st.page); api.mode(st.view || 0);
        for (const [k, v] of Object.entries(st.pv || {})) api.pv(k, v);
        api.paint();
      } else if (b.jspainterfile && PAINTERS[b.jspainterfile]) {
        const paint = new Function("box", "mgraphics", "max", "post", "error", PAINTERS[b.jspainterfile] + "\\n;return paint;")(boxMock(b), mg, max, () => {}, () => {});
        paint();
      } else if (b.maxclass === "live.comment") {
        const fs = b.fontsize || 9; ctx.font = (String(b.fontname).includes("Bold") ? "600 " : "500 ") + fs + "px Inter, Helvetica, sans-serif";
        ctx.fillStyle = dark ? (String(b.fontname).includes("Bold") ? "#c9c9c9" : "#969696") : (String(b.fontname).includes("Bold") ? "#1e1e1e" : "#4d4d4d");
        ctx.textAlign = b.textjustification === 1 ? "center" : "left";
        ctx.fillText(b.text, b.textjustification === 1 ? w / 2 : 0, fs + 1);
        ctx.textAlign = "left";
      } else if (b.maxclass === "live.line") {
        ctx.strokeStyle = dark ? "#3a3a3a" : "#b5b5b5"; ctx.lineWidth = 1; ctx.beginPath();
        if (w >= h) { ctx.moveTo(0, Math.round(h / 2) + 0.5); ctx.lineTo(w, Math.round(h / 2) + 0.5); } else { ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); }
        ctx.stroke();
      } else if (b.maxclass === "live.meter~") {
        ctx.fillStyle = dark ? "#1b1b1b" : "#e6e6e6"; ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = dark ? "#9a9a9a" : "#555";
        if (w > h) ctx.fillRect(0, 0, w * 0.55, h); else ctx.fillRect(0, h * 0.45, w, h * 0.55);
      }
    } catch (e) { ctx.restore(); ctx.save(); ctx.translate(x, y); ctx.fillStyle = "red"; ctx.fillRect(0, 0, w, h); console.error(b.varname, e); }
    ctx.restore();
  }
  for (const b of switches) {
    const vo = (b.saved_attribute_attributes || {}).valueof || {};
    drawSwitch(ctx, b, opts.variant, dark, (b.__value ?? (vo.parameter_initial ? vo.parameter_initial[0] : 0)) > 0.5);
  }
}
const base = { page: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1, wshape: 1 };
const only = new URLSearchParams(location.search).get("only");
if (MODE === "variants") {
  document.getElementById("root").className = "grid";
  const V = [["E", "E: power symbol right of the title"], ["P", "Now: the title is the switch (pill)"],
             ["A", "A: square switch left of the title"],
             ["B", "B: power symbol left of the title"], ["C", "C: plain title, clickable (dim = off)"],
             ["D", "D: title + On/Off pill"]];
  const crop = [640, 0, 328, 169];
  for (const [name, dark] of [["dark", true], ["light", false]]) {
    for (const [v, t] of V) {
      const rects = v === "E" ? { tone_res_track: [730, 98, 64, 13] } : {};
      render(t + " - Tone (" + name + ")", { ...base, page: 2 }, dark, { variant: v, crop, rects });
      render(t + " - Global, Limiter off (" + name + ")", { ...base, page: 3, values: { out_lim_on: 0 } }, dark, { variant: v, crop });
    }
  }
} else {
const mx = { mod_l1_wp: 35, mod_l2_rp: 20, mod_vo_rp: -60, mod_nb_wa: -100, mod_en_ou: -100, mod_ro_sz: 45, mod_dr_bc: 70 };
for (const [name, dark] of [["dark", true], ["light", false]]) {
  render("LFO · Env page (" + name + ")", base, dark);
  render("Mod page, some matrix cells set (" + name + ")", { ...base, page: 1, values: mx }, dark);
  render("Tone page, resonator on (" + name + ")", { ...base, page: 2, pv: { reson: 1 }, values: { tone_res_on: 1 } }, dark);
  render("Global page (" + name + ")", { ...base, page: 3 }, dark);
}
render("Write + Read in Sync mode, Pulsar (Duty), LFO 1 synced, 2D view (dark)", { ...base, wmode: 1, rmode: 1, l1mode: 1, view: 1, wshape: 5, values: { w_shape: 5, w_active: 2 } }, true);
render("Tone page, Reject, 12 dB, band off (light)", { ...base, page: 2, pv: { center: 900, bwidth: 1, bres: 30, bmode: 1, bslope: 0, bandon: 0 }, values: { tone_band_on: 0 } }, false);
}
</script></body></html>`;
writeFileSync(out, html);
console.log(`wrote ${out}`);
