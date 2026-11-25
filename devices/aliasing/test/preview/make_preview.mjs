#!/usr/bin/env node
// Preview of an Aliasing face without Max (v0.3b: Aliasing.amxd = hybrid, Aliasing B.amxd = face b):
// renders the real painter and display bundles (devices/aliasing/aliasing_paint_*.js,
// aliasing_display.js) into HTML canvases through a small mgraphics -> Canvas 2D adapter, with the
// boxes, ranges and initial values of the shell and the table / display data of a host render
// (test/host: drone.table.f32, drone.heads.f32). One canvas per page and a few states, on Live's dark
// and light device backgrounds with the theme panels (D22, colours as the pages script computes them).
// Dials are drawn at the height Live gives them (48 with showname 1, 36 with showname 0 [measured:
// dial probe 2026-11-25]), not at the saved rect. Text uses Ableton Sans from the local Max install,
// embedded in the HTML (the output stays local, in build/); the browser's rasteriser still differs
// from Live's, so this is for layout review.
//
//   node devices/aliasing/test/preview/make_preview.mjs OUT.html [SHELL.amxd ...] [--only TEXT]
// Several shells: one block per shell, titles prefixed with the file name (compare variants side by
// side). --only TEXT keeps the canvases whose title contains TEXT (also ?only=TEXT in the browser).
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dev = join(here, "..", "..");
const root = join(dev, "..", "..");
const args = process.argv.slice(2);
const oi = args.indexOf("--only");
const ONLY = oi >= 0 ? args.splice(oi, 2)[1] : null;
const out = args[0];
if (!out) {
	console.error("usage: node make_preview.mjs OUT.html [SHELL.amxd ...] [--only TEXT]");
	process.exit(2);
}

function readAmxd(path) {
	const buf = readFileSync(path);
	const i = buf.indexOf("ptch");
	const n = buf.readUInt32LE(i + 4);
	return JSON.parse(buf.subarray(i + 8, i + 8 + n).toString("utf8").replace(/\0+$/, ""));
}
const painters = {};
const shells = (args.length > 1 ? args.slice(1) : [join(dev, "Aliasing.amxd")]).map((path) => {
	const pat = readAmxd(path).patcher;
	const all = pat.boxes.map((b) => b.box);
	const pagesBox = all.find((b) => String(b.text || "").startsWith("v8 aliasing_pages.js"));
	const face = pagesBox && String(pagesBox.text).split(/\s+/)[2] === "b" ? "b" : "hybrid";
	// only what the preview draws (keeps a multi-shell file small): no annotations, no patching rects
	const boxes = all.filter((b) => b.presentation && b.presentation_rect).map((b) => {
		const { annotation, patching_rect, ...rest } = b;
		const vo = rest.saved_attribute_attributes && rest.saved_attribute_attributes.valueof;
		if (vo) {
			const { parameter_info, ...v } = vo;
			rest.saved_attribute_attributes = { valueof: v };
		}
		return rest;
	});
	for (const b of boxes) {
		const f = b.jspainterfile;
		if (f && !(f in painters)) painters[f] = readFileSync(join(dev, f), "utf8");
	}
	return { label: path.split("/").pop().replace(/\.amxd$/, ""), face, boxes, w: Number(pat.devicewidth) || 968 };
});
const FACE = shells[0].face;
const display = readFileSync(join(dev, "aliasing_display.js"), "utf8");
function f32(p) {
	if (!existsSync(p)) return null;
	const b = readFileSync(p);
	return Array.from(new Float32Array(b.buffer, b.byteOffset, b.length / 4)).map((x) => Math.round(x * 1e5) / 1e5);
}
const table = f32(join(root, "build/aliasing/host/drone.table.f32"));
const heads = f32(join(root, "build/aliasing/host/drone.heads.f32"));
const FONTS = "/Applications/Max.app/Contents/Resources/C74/fonts/";
const font = (f) => (existsSync(FONTS + f) ? `url(data:font/otf;base64,${readFileSync(FONTS + f).toString("base64")})` : "local(Helvetica)");

const html = `<!doctype html><html><head><meta charset="utf-8"><title>Aliasing ${FACE} preview</title>
<style>@font-face{font-family:"AbletonSansMedium";src:${font("AbletonSans-Medium.otf")}}
@font-face{font-family:"AbletonSansBold";src:${font("AbletonSans-Bold.otf")}}
body{background:#111;color:#bbb;font:12px -apple-system,Helvetica,sans-serif;margin:16px}
h2{font-size:12px;font-weight:600;margin:14px 0 4px}canvas{display:block;border-radius:2px;image-rendering:pixelated}</style></head><body>
<div id="root"></div>
<script>
const SHELLS = ${JSON.stringify(shells)};
let FACE = SHELLS[0].face, BOXES = SHELLS[0].boxes, W = SHELLS[0].w, PREFIX = "";
const PAINTERS = ${JSON.stringify(painters)};
const DISPLAY = ${JSON.stringify(display)};
const TABLE = ${JSON.stringify(table)};
const HEADS = ${JSON.stringify(heads)};
const H = 169;
const S = Number(new URLSearchParams(location.search).get("scale") || 1);
const fam = (n) => (String(n).includes("Bold") ? "AbletonSansBold" : "AbletonSansMedium");
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
    select_font_face(n) { fontName = n; ctx.font = fontSize + "px " + fam(n); },
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
    _parameter_range: b.__range ? b.__range : enumL ? enumL : [vo.parameter_mmin ?? 0, vo.parameter_mmax ?? 1],
    _parameter_exponent: vo.parameter_exponent ?? 1,
    _parameter_unitstyle: vo.parameter_unitstyle ?? 1,
    _parameter_units: vo.parameter_units ?? "",
    _parameter_shortname: vo.parameter_shortname ?? "",
    text: b.text ?? "", texton: b.texton ?? b.text ?? "", active: b.__active ?? 1,
    num_lines_presentation: b.num_lines_presentation ?? 1, multiline: b.multiline ?? 1,
  };
  return { varname: b.varname, getattr: (n) => (n in attrs ? attrs[n] : null), setattr() {},
           getvalueof: () => (b.__value ?? (vo.parameter_initial ? vo.parameter_initial[0] : 0)) };
}
// ---- mirror of pages_model.ts (faces, strip, Sym groups, greying, theme colours) ----
const FACES = { hybrid: { pages: ["lfo", "mod", "tone", "out"], tone: [2] }, b: { pages: ["lfo1", "lfo2", "env", "band", "res", "lim", "out"], tone: [3, 4] } };
const TARGETS = ["wp", "sy", "wa", "rp", "sp", "sz", "bc", "rf", "ou"];
const SYM = ["curve", "skew", "duty", "width", "smooth"];
function lum(c) { return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
function panelColor(bg) { return lum(bg) > 0.5 ? bg.map((x) => x * 0.92) : bg.map((x) => x + (1 - x) * 0.06); }
const rgb = (c) => "rgb(" + c.map((x) => Math.round(x * 255)).join(",") + ")";
function visible(b, st) {
  const parts = String(b.varname || "").split("_");
  if (parts.length < 2) return !b.hidden;
  const [area, cond] = parts;
  const F = FACES[FACE];
  if (FACE === "b" && area === "mod") { const t = TARGETS.indexOf(parts[2] || ""); return t < 0 ? !b.hidden : t === (st.target || 0); }
  let ok;
  if (F.pages.includes(area)) ok = F.pages.indexOf(area) === st.page;
  else if (area === "tbl") ok = !F.tone.includes(st.page);
  else if (area === "w" || area === "r") ok = true;
  else return !b.hidden;
  let c = true;
  if ((cond === "free" || cond === "sync") && (area === "w" || area === "r")) { const m = area === "w" ? st.wmode : st.rmode; c = cond === "free" ? m === 0 : m === 1; }
  if (cond === "hz1" || cond === "sy1") c = (st.l1mode === 0) === (cond === "hz1");
  if (cond === "hz2" || cond === "sy2") c = (st.l2mode === 0) === (cond === "hz2");
  if (cond === "symlbl" && area === "w") c = SYM[st.wshape ?? 1] === parts[2];
  return ok && c;
}
function idle(b, st) {
  const n = String(b.varname || ""), v = (k, d) => (st.values && k in st.values ? st.values[k] : d);
  const on = (suffix, d) => { const hit = Object.keys(st.values || {}).find((k) => k.endsWith(suffix)); return hit ? st.values[hit] : d; };
  if (["w_free_pitch", "w_sync_note", "w_fine", "w_sync_mult", "w_sync_div", "w_sym", "w_shape"].includes(n)) return v("w_active", 1) === 2;
  if (/_on$/.test(n) || n.startsWith("mod_")) return false;
  const key = n.substring(n.indexOf("_") + 1);
  if (key === "transpose") return st.wmode === 1 && st.rmode === 1;
  if (key === "syncrate") return st.wmode === 0 && st.rmode === 0;
  if (key === "drive") return !on("_drive_on", 1);
  if (key.startsWith("band_")) return !on("_band_on", 1);
  if (key === "res_freq") return !on("_res_on", 0) || !!on("_res_track", 1);
  if (key.startsWith("res_")) return !on("_res_on", 0);
  if (key.startsWith("lim_")) return !on("_lim_on", 1);
  return false;
}
function markerCol(t, dark, panel) {
  const role = ["wp", "sy", "wa"].includes(t) ? "write" : ["rp", "sp"].includes(t) ? "read" : "neutral";
  if (role === "write") return dark ? "#e4e4e4" : "#1c1c1c";
  if (role === "read") return dark ? "#8fb0c4" : "#2f5873";
  const l = dark ? [0.69, 0.69, 0.69] : [0.149, 0.149, 0.149];
  return rgb(panel.map((x, i) => x + (l[i] - x) * 0.45));
}
const NAMES = ["Write Pitch", "Write Sym", "Write Gate", "Read Pitch", "Read Spread", "Size", "Band Center", "Res Freq", "Output"];
function menuLabels(st) {
  const v = st.values || {};
  return TARGETS.map((t, k) => NAMES[k] + (Object.keys(v).some((n) => n.startsWith("mod_") && n.endsWith("_" + t) && Math.abs(v[n]) >= 0.5) ? " \u2022" : ""));
}
const BG = { dark: [0x36 / 255, 0x36 / 255, 0x36 / 255], light: [0xa5 / 255, 0xa5 / 255, 0xa5 / 255] }; // Live 12 Neutral Medium
function dialH(b, h) {
  if (b.maxclass !== "live.dial") return h;
  const sn = b.showname ?? 1, nb = b.shownumber ?? 1;
  return sn && nb ? 48 : nb ? 36 : 28;
}
function render(title, st, dark) {
  if (only !== null && !(PREFIX + title).toLowerCase().includes(only.toLowerCase())) return;
  const rootEl = document.getElementById("root");
  const cell = document.createElement("div"); rootEl.appendChild(cell);
  const h2 = document.createElement("h2"); h2.textContent = PREFIX + title; cell.appendChild(h2);
  const cv = document.createElement("canvas"); const R = 2;
  cv.width = W * R; cv.height = H * R; cv.style.width = W * S + "px"; cv.style.height = H * S + "px"; cell.appendChild(cv);
  const ctx = cv.getContext("2d"); ctx.scale(R, R);
  const bg = dark ? BG.dark : BG.light;
  const panel = panelColor(bg);
  ctx.fillStyle = rgb(bg); ctx.fillRect(0, 0, W, H);
  const max = { getcolor: () => (dark ? [0.8, 0.8, 0.8, 1] : [0.12, 0.12, 0.12, 1]) };
  for (const b0 of BOXES) {
    let b = st.values && b0.varname in st.values ? { ...b0, __value: st.values[b0.varname] } : b0;
    if (idle(b, st)) b = { ...b, __active: 0 };
    if (b.varname === "mod_target") b = { ...b, __range: menuLabels(st) }; // D48, as the pages script sets it
    if (!visible(b, st)) continue;
    let [x, y, w, h] = b.presentation_rect;
    if (b.varname === "display" && FACE === "hybrid" && st.page === 2) h = 157; // D31: x, y, width stay
    h = dialH(b, h);
    ctx.save(); ctx.translate(x, y); ctx.beginPath();
    const mg = mgFor(ctx, w, h);
    try {
      if (b.maxclass === "panel") {
        const name = String(b.varname || "");
        ctx.fillStyle = name.startsWith("mod_mark_") ? markerCol(name.substring(9), dark, panel) : rgb(panel);
        ctx.beginPath(); ctx.roundRect(0, 0, w, h, name.startsWith("panel_") ? 4 : 0); ctx.fill();
      } else if (b.maxclass === "v8ui") {
        const store = { atab: TABLE, aheads: HEADS };
        class Buffer { constructor(n) { this.d = store[n]; this.ch = n === "atab" ? 5 : 10; this.fr = n === "atab" ? 1024 : 5; }
          peek(c, f, k) { const o = []; for (let i = 0; i < k; i++) o.push(this.d ? this.d[(c - 1) * this.fr + f + i] : 0); return o; } poke() {} }
        class Dict { constructor(n) { this.name = n || "d"; } parse() {} get() { return null; } }
        class Task { constructor() { this.running = false; } repeat() {} cancel() {} }
        const api = new Function("mgraphics", "Buffer", "Dict", "Task", "outlet", "post", "max", "inlets", "outlets",
          DISPLAY + "\\n;return { paint, buffers, page, mode, pv, tonepages };")(mg, Buffer, Dict, Task, () => {}, () => {}, max, 0, 0);
        api.buffers("atab", "aheads"); api.tonepages(...FACES[FACE].tone); api.page(st.page); api.mode(st.view || 0);
        for (const [k, v] of Object.entries(st.pv || {})) api.pv(k, v);
        api.paint();
      } else if (b.jspainterfile && PAINTERS[b.jspainterfile]) {
        const paint = new Function("box", "mgraphics", "max", "post", "error", PAINTERS[b.jspainterfile] + "\\n;return paint;")(boxMock(b), mg, max, () => {}, () => {});
        paint();
      } else if (b.maxclass === "live.comment") {
        const fs = b.fontsize || 9.5; ctx.font = fs + "px " + fam(b.fontname);
        ctx.fillStyle = dark ? (String(b.fontname).includes("Bold") ? "#d2d2d2" : "#b0b0b0") : (String(b.fontname).includes("Bold") ? "#111111" : "#262626");
        const j = b.textjustification || 0;
        ctx.textAlign = j === 1 ? "center" : j === 2 ? "right" : "left";
        ctx.fillText(b.text, j === 1 ? w / 2 : j === 2 ? w - 4 : 4, 11); // text 4 px in, baseline y+11 (face review §0)
        ctx.textAlign = "left";
      } else if (b.maxclass === "live.line") {
        ctx.strokeStyle = rgb(panel.map((x, i) => x + ((dark ? 0x5c : 0x6e) / 255 - x) * 0.7)); ctx.lineWidth = 1; ctx.beginPath();
        if (w >= h) { ctx.moveTo(0, Math.round(h / 2) + 0.5); ctx.lineTo(w, Math.round(h / 2) + 0.5); } else { ctx.moveTo(Math.floor(w / 2) + 0.5, 0); ctx.lineTo(Math.floor(w / 2) + 0.5, h); }
        ctx.stroke();
      } else if (b.maxclass === "live.meter~") {
        ctx.fillStyle = dark ? "#262626" : "#dedede"; ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = dark ? "#9a9a9a" : "#3c3c3c";
        if (w > h) ctx.fillRect(0, 0, w * 0.55, h); else ctx.fillRect(0, h * 0.45, w, h * 0.55);
      }
    } catch (e) { ctx.restore(); ctx.save(); ctx.translate(x, y); ctx.fillStyle = "red"; ctx.fillRect(0, 0, w, h); console.error(b.varname, e); }
    ctx.restore();
  }
}
const base = { page: 0, target: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1, wshape: 1 };
const only = new URLSearchParams(location.search).get("only") ?? ${JSON.stringify(ONLY)};
const mx = { mod_l1_wp: 35, mod_l2_rp: 20, mod_vo_rp: -60, mod_nb_wa: -100, mod_en_ou: -100, mod_ro_sz: 45, mod_l1_bc: 70, mod_l2_wa: 100, mod_ve_ou: 60 };
// document.fonts.ready resolves before canvas-only fonts load: load them explicitly
Promise.all([document.fonts.load("10px AbletonSansMedium"), document.fonts.load("10px AbletonSansBold")]).catch(() => null).then(() => {
 for (const sh of SHELLS) {
  FACE = sh.face; BOXES = sh.boxes; W = sh.w; PREFIX = SHELLS.length > 1 ? sh.label + " - " : "";
  for (const [name, dark] of [["dark", true], ["light", false]]) {
    const pages = FACES[FACE].pages;
    const label = FACE === "b" ? ["LFO 1", "LFO 2", "Env", "Band", "Res", "Limit", "Global"] : ["LFO · Env", "Mod", "Tone", "Global"];
    pages.forEach((_, k) => render(label[k] + " page (" + name + ")", { ...base, page: k, values: { ...mx, page: k } }, dark));
  }
  render("Write + Read in Sync, Pulsar (Duty), LFO 1 synced, 2D view (dark)", { ...base, wmode: 1, rmode: 1, l1mode: 1, view: 1, wshape: 2, values: { w_shape: 2 } }, true);
  render("Clean (light): write controls greyed, Spike", { ...base, wshape: 3, values: { w_shape: 3, w_active: 2 } }, false);
  if (FACE === "b") {
    render("Strip on Output, Band page, Reject, band off (dark)", { ...base, page: 3, target: 8, values: { ...mx, mod_target: 8, band_band_on: 0 }, pv: { center: 900, bwidth: 1, bmode: 1, bandon: 0 } }, true);
    render("Strip on Size, Res page, resonator on (light)", { ...base, page: 4, target: 5, values: { ...mx, mod_target: 5, res_res_on: 1 }, pv: { reson: 1 } }, false);
  } else {
    render("Tone page, Reject, 12 dB, band off (light)", { ...base, page: 2, pv: { center: 900, bwidth: 1, bres: 30, bmode: 1, bslope: 0, bandon: 0 }, values: { tone_band_on: 0 } }, false);
  }
 }
});
</script></body></html>`;
writeFileSync(out, html);
console.log(`wrote ${out} (${shells.map((x) => x.label + ": " + x.face).join(", ")})`);
