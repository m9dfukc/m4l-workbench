#!/usr/bin/env node
// Preview of the Aliasing face without Max: renders the real painter and display bundles
// (devices/aliasing/aliasing_paint_*.js, aliasing_display.js) into HTML canvases through a small
// mgraphics -> Canvas 2D adapter, with the boxes, ranges and initial values of Aliasing.amxd and
// the table / display data of a host render (test/host: drone.table.f32, drone.heads.f32).
// One canvas per page (LFO, Mod, Tone, Out) plus a Sync-mode variant, dark and light theme.
// Fonts differ from Live (no Ableton Sans in the browser); this is for layout review only.
//
//   node devices/aliasing/test/preview/make_preview.mjs OUT.html
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dev = join(here, "..", "..");
const root = join(dev, "..", "..");
const out = process.argv[2];
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
const pat = readAmxd(join(dev, "Aliasing.amxd")).patcher;
const boxes = pat.boxes.map((b) => b.box).filter((b) => b.presentation && b.presentation_rect);
const painters = {};
for (const cls of ["dial", "tab", "toggle", "slider", "menu", "number"]) {
	painters[cls] = readFileSync(join(dev, `aliasing_paint_${cls}.js`), "utf8");
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
h2{font-size:12px;font-weight:600;margin:14px 0 4px}canvas{display:block;border-radius:2px;max-width:100%;height:auto!important}</style></head><body>
<div id="root"></div>
<script>
const BOXES = ${JSON.stringify(boxes)};
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
  };
  return { varname: b.varname, getattr: (n) => (n in attrs ? attrs[n] : null), setattr() {},
           getvalueof: () => (b.__value ?? (vo.parameter_initial ? vo.parameter_initial[0] : 0)) };
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
  return ok && c;
}
const CLS = { "live.dial": "dial", "live.tab": "tab", "live.text": "toggle", "live.slider": "slider", "live.menu": "menu", "live.numbox": "number" };
function render(title, st, dark) {
  if (only !== null && !title.toLowerCase().startsWith(only.toLowerCase())) return;
  const root = document.getElementById("root");
  const h2 = document.createElement("h2"); h2.textContent = title; root.appendChild(h2);
  const cv = document.createElement("canvas"); const S = 2;
  cv.width = W * S; cv.height = H * S; cv.style.width = W + "px"; cv.style.height = H + "px"; root.appendChild(cv);
  const ctx = cv.getContext("2d"); ctx.scale(S, S);
  ctx.fillStyle = dark ? "#262626" : "#d4d4d4"; ctx.fillRect(0, 0, W, H);
  const getcolor = () => (dark ? [0.8, 0.8, 0.8, 1] : [0.12, 0.12, 0.12, 1]);
  const max = { getcolor };
  const order = [...BOXES].sort((a, b) => (a.maxclass === "v8ui" ? -1 : 0) - (b.maxclass === "v8ui" ? -1 : 0));
  for (const b of order) {
    if (!visible(b, st)) continue;
    const [x, y, w, h] = b.presentation_rect;
    ctx.save(); ctx.translate(x, y); ctx.beginPath();
    const mg = mgFor(ctx, w, h);
    try {
      if (b.maxclass === "v8ui") {
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
      } else if (CLS[b.maxclass]) {
        const paint = new Function("box", "mgraphics", "max", "post", "error", PAINTERS[CLS[b.maxclass]] + "\\n;return paint;")(boxMock(b), mg, max, () => {}, () => {});
        paint();
      } else if (b.maxclass === "live.comment") {
        const fs = b.fontsize || 9; ctx.font = (String(b.fontname).includes("Bold") ? "600 " : "500 ") + fs + "px Inter, Helvetica, sans-serif";
        ctx.fillStyle = dark ? (String(b.fontname).includes("Bold") ? "#c9c9c9" : "#969696") : (String(b.fontname).includes("Bold") ? "#1e1e1e" : "#4d4d4d");
        ctx.textAlign = b.textjustification === 1 ? "center" : "left";
        ctx.fillText(b.text, b.textjustification === 1 ? w / 2 : 0, fs + 1);
      } else if (b.maxclass === "live.line") {
        ctx.strokeStyle = dark ? "#3a3a3a" : "#b5b5b5"; ctx.lineWidth = 1; ctx.beginPath();
        if (w >= h) { ctx.moveTo(0, Math.round(h / 2) + 0.5); ctx.lineTo(w, Math.round(h / 2) + 0.5); } else { ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); }
        ctx.stroke();
      } else if (b.maxclass === "live.meter~") {
        ctx.fillStyle = dark ? "#1b1b1b" : "#e6e6e6"; ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = dark ? "#9a9a9a" : "#555"; ctx.fillRect(0, h * 0.45, w, h * 0.55);
      }
    } catch (e) { ctx.restore(); ctx.save(); ctx.translate(x, y); ctx.fillStyle = "red"; ctx.fillRect(0, 0, w, h); console.error(b.varname, e); }
    ctx.restore();
  }
}
const base = { page: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1 };
const only = new URLSearchParams(location.search).get("only");
render("LFO page (dark)", base, true);
render("Mod page (dark)", { ...base, page: 1 }, true);
render("Tone page (dark)", { ...base, page: 2 }, true);
render("Out page (dark)", { ...base, page: 3 }, true);
render("Tone page with a resonant 2-octave band and the resonator (dark)", { ...base, page: 2, pv: { center: 1200, bwidth: 2, bres: 60, rsmix: 60, rsfb: 70, rstrack: 0, rsfreq: 300 } }, true);
render("Tone page, Reject, 12 dB (dark)", { ...base, page: 2, pv: { center: 900, bwidth: 1, bres: 30, bmode: 1, bslope: 0 } }, true);
render("Write + Read in Sync mode, LFO 1 synced, 2D view (dark)", { ...base, wmode: 1, rmode: 1, l1mode: 1, view: 1 }, true);
render("LFO page (light theme)", base, false);
</script></body></html>`;
writeFileSync(out, html);
console.log(`wrote ${out}`);
