// GENERATED from devices/aliasing/js/src/aliasing_display.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/display_model.ts
var CELLS = 1024;
var VOICES = 5;
var COLUMNS_2D = 64;
var SIZE_MIN = 1e-3;
var W = 328;
var H = 136;
var PAD = 4;
var HEADER_Y = 3;
var HEADER_H = 12;
var LANE_TOP = 17;
var OVERVIEW_H = 5;
var CURVE_TOP = 17;
function clamp(x, lo, hi) {
  return x < lo ? lo : x > hi ? hi : x;
}
function overviewY(h = H) {
  return h - PAD - OVERVIEW_H + 1;
}
function laneHeight(h = H) {
  return (overviewY(h) - 2 - LANE_TOP) / VOICES;
}
function laneRect(v, w = W, h = H) {
  const lh = laneHeight(h);
  return { x: PAD, y: LANE_TOP + v * lh, w: w - 2 * PAD, h: lh };
}
function curveRect(w = W, h = H) {
  return { x: PAD, y: CURVE_TOP, w: w - 2 * PAD, h: h - CURVE_TOP - 14 };
}
function nextZoom(prev, base, spans, dt, tau = 0.35) {
  let target = clamp(base, SIZE_MIN, 1);
  for (let i = 0; i < spans.length; i++) {
    const s = spans[i];
    if (s > target) target = clamp(s, SIZE_MIN, 1);
  }
  if (!(prev > 0) || target >= prev) return target;
  const k = 1 - Math.exp(-dt / tau);
  const z = Math.exp(Math.log(prev) + (Math.log(target) - Math.log(prev)) * k);
  return z - target < 1e-6 ? target : z;
}
function laneOutline(row, span, lane) {
  const n = Math.max(1, Math.min(span, row.length));
  const pts = [];
  if (n * 2 <= lane.w) {
    for (let c = 0; c < n; c++) {
      const y = laneY(row[c], lane);
      pts.push(lane.x + c / n * lane.w, y, lane.x + (c + 1) / n * lane.w, y);
    }
    return { pts, filled: false };
  }
  const cols = Math.max(1, Math.floor(lane.w));
  const env = decimateMinMax(row, n, cols);
  const lo = [];
  for (let c = 0; c < cols; c++) {
    const x = lane.x + c + 0.5;
    const top = laneY(env.max[c], lane) - 0.5;
    const bot = Math.max(laneY(env.min[c], lane) + 0.5, top + 1);
    pts.push(x, top);
    lo.push(x, bot);
  }
  for (let k = lo.length - 2; k >= 0; k -= 2) pts.push(lo[k], lo[k + 1]);
  return { pts, filled: true };
}
function copyInto(out, values, n) {
  if (values === null || values === void 0) {
    for (let i = 0; i < n; i++) out[i] = 0;
    return;
  }
  if (typeof values === "number") {
    out[0] = Number.isFinite(values) ? values : 0;
    for (let i = 1; i < n; i++) out[i] = 0;
    return;
  }
  for (let i = 0; i < n; i++) {
    const v = i < values.length ? Number(values[i]) : 0;
    out[i] = Number.isFinite(v) ? v : 0;
  }
}
function iconRects(w = W) {
  return {
    line: { x: w - PAD - 30, y: HEADER_Y, w: 14, h: 11 },
    twoD: { x: w - PAD - 14, y: HEADER_Y, w: 14, h: 11 }
  };
}
function inRect(x, y, r) {
  return x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h;
}
function spanCells(size) {
  return Math.max(1, Math.round(clamp(size, SIZE_MIN, 1) * CELLS));
}
function laneY(value, lane) {
  return lane.y + 1.5 + (1 - clamp(value, 0, 1)) * (lane.h - 4);
}
function headX(head, size, lane) {
  return lane.x + clamp(head / clamp(size, SIZE_MIN, 1), 0, 1) * lane.w;
}
function headCell(head, size) {
  const span = spanCells(size);
  return clamp(Math.floor(clamp(head, 0, 1) * CELLS), 0, span - 1);
}
function decimateMinMax(row, span, cols) {
  const n = Math.min(span, row.length);
  const min = [];
  const max2 = [];
  for (let c = 0; c < cols; c++) {
    const i0 = Math.floor(c * n / cols);
    const i1 = Math.max(i0 + 1, Math.floor((c + 1) * n / cols));
    let lo = Infinity;
    let hi = -Infinity;
    for (let i = i0; i < i1 && i < n; i++) {
      const v = row[i];
      if (v < lo) lo = v;
      if (v > hi) hi = v;
    }
    if (lo === Infinity) lo = hi = 0;
    min.push(lo);
    max2.push(hi);
  }
  return { min, max: max2 };
}
function sampleColumns(row, span, cols) {
  const out = [];
  const n = Math.min(span, row.length);
  for (let c = 0; c < cols; c++) {
    const i = Math.min(n - 1, Math.floor((c + 0.5) * n / cols));
    out.push(i >= 0 ? row[i] : 0);
  }
  return out;
}
function cellAlpha(v) {
  return 0.06 + 0.8 * clamp(v, 0, 1);
}
function fmtHz(f) {
  if (!Number.isFinite(f)) return "-";
  if (f >= 1e3) return `${(f / 1e3).toFixed(2)} kHz`;
  if (f >= 100) return `${Math.round(f)} Hz`;
  if (f >= 10) return `${f.toFixed(1)} Hz`;
  return `${f.toFixed(2)} Hz`;
}
function fsFraction(f, fs2, maxBeat = 200) {
  if (!(fs2 > 0) || !(f >= fs2 / 16)) return null;
  const r = f / fs2;
  let best = null;
  for (let q = 1; q <= 8; q++) {
    const p = Math.round(r * q);
    if (p < 1) continue;
    const beat = f - fs2 * p / q;
    if (!best || Math.abs(beat) < Math.abs(best.beat) - 1e-9) best = { p, q, beat };
  }
  if (!best || Math.abs(best.beat) > maxBeat) return null;
  const g = gcd(best.p, best.q);
  return { p: best.p / g, q: best.q / g, beat: best.beat };
}
function gcd(a, b) {
  return b ? gcd(b, a % b) : a;
}
function fmtFraction(fr) {
  const head = fr.q === 1 ? fr.p === 1 ? "fs" : `${fr.p}fs` : fr.p === 1 ? `fs/${fr.q}` : `${fr.p}fs/${fr.q}`;
  const b = fr.beat;
  return `${head} ${b >= 0 ? "+" : "-"}${Math.abs(b) < 10 ? Math.abs(b).toFixed(1) : Math.round(Math.abs(b))} Hz`;
}
function tableInfo(spanOfVoice1, fw, fr, fs2) {
  const frac = fsFraction(fw, fs2);
  const w = `W ${fmtHz(fw)}${frac ? ` = ${fmtFraction(frac)}` : ""}`;
  return `${spanOfVoice1} cells \xB7 ${w} \xB7 R ${fmtHz(fr)}`;
}
var F_MIN = 20;
var F_MAX = 2e4;
function xOfF(f, rect) {
  return rect.x + Math.log(clamp(f, 1, 1e6) / F_MIN) / Math.log(F_MAX / F_MIN) * rect.w;
}
function fOfX(x, rect) {
  return F_MIN * Math.pow(F_MAX / F_MIN, clamp((x - rect.x) / rect.w, 0, 1));
}
function yOfDb(db, rect) {
  return rect.y + 4 + (18 - clamp(db, -36, 18)) / 54 * (rect.h - 4);
}
function dbOfY(y, rect) {
  return 18 - (y - rect.y - 4) / (rect.h - 4) * 54;
}
function yOfRes(res, rect) {
  return yOfDb(2 + clamp(res, 0, 100) * 0.14, rect);
}
function resOfY(y, rect) {
  return clamp((dbOfY(y, rect) - 2) / 0.14, 0, 100);
}
function yOfFb(fb, rect) {
  return rect.y + 8 + (1 - (clamp(fb, -95, 95) + 95) / 190) * (rect.h - 16);
}
function fbOfY(y, rect) {
  return clamp(95 - (y - rect.y - 8) / (rect.h - 16) * 190, -95, 95);
}
var cmul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
var cdiv = (a, b) => {
  const d = b[0] * b[0] + b[1] * b[1] || 1e-30;
  return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
};
var cadd = (a, b) => [a[0] + b[0], a[1] + b[1]];
function sec(f, fc, q, high) {
  const s = [0, f / fc];
  const den = [1 - f / fc * (f / fc), f / fc / q];
  return cdiv(high ? cmul(s, s) : [1, 0], den);
}
function resQ(res, slope24) {
  const r = clamp(res, 0, 100) / 100;
  return slope24 ? 1.3066 * Math.pow(18 / 1.3066, r) : 0.7071 * Math.pow(18 / 0.7071, r);
}
function toneDb(f, t, fs2 = 48e3) {
  const nyq = 0.45 * fs2;
  const lo = clamp(t.center * Math.pow(2, -0.5 * t.width), 10, nyq);
  const hi = clamp(t.center * Math.pow(2, 0.5 * t.width), 10, nyq);
  const qr = resQ(t.res, t.slope24);
  const edge = (fc, high) => t.slope24 ? cmul(sec(f, fc, 0.5412, high), sec(f, fc, qr, high)) : sec(f, fc, qr, high);
  let h = t.bandOn === false ? [1, 0] : t.reject ? cadd(edge(lo, false), edge(hi, true)) : cmul(edge(lo, true), edge(hi, false));
  if (t.resOn !== false && t.rsMix > 0) {
    const g = clamp(t.rsFb, -95, 95) / 100;
    const d = 1 / clamp(t.rsFreq, 20, 5e3);
    const ph = -2 * Math.PI * f * d;
    const comb = cdiv([Math.sqrt(1 - g * g), 0], [1 - g * Math.cos(ph), -g * Math.sin(ph)]);
    const m = t.rsMix / 100;
    h = cmul(h, cadd([1 - m, 0], [m * comb[0], m * comb[1]]));
  }
  return 20 * Math.log10(Math.max(1e-5, Math.hypot(h[0], h[1])));
}
function bandEdges(t, fs2 = 48e3) {
  const nyq = 0.45 * fs2;
  return {
    lo: clamp(t.center * Math.pow(2, -0.5 * t.width), 10, nyq),
    hi: clamp(t.center * Math.pow(2, 0.5 * t.width), 10, nyq)
  };
}
function hitCurve(x, y, t, rect, fs2 = 48e3) {
  const e = bandEdges(t, fs2);
  const xl = xOfF(e.lo, rect);
  const xh = xOfF(e.hi, rect);
  const xr = xOfF(t.rsFreq, rect);
  const yr = yOfFb(t.rsFb, rect);
  const xc = xOfF(t.center, rect);
  const yc = yOfRes(t.res, rect);
  if (Math.hypot(xr - x, yr - y) < 10) return "rs";
  if (Math.hypot(xc - x, yc - y) < 10) return "body";
  if (Math.abs(x - xl) < 6 && xl > rect.x + 1) return "edge";
  if (Math.abs(x - xh) < 6 && xh < rect.x + rect.w - 1) return "edge";
  if (x > xl && x < xh) return "body";
  return null;
}
function widthFromEdge(x, center, rect) {
  return clamp(2 * Math.abs(Math.log2(fOfX(x, rect) / center)), 0.2, 10);
}
function laneHit(x, y, w = W, h = H) {
  const lh = laneHeight(h);
  if (y < LANE_TOP || y >= LANE_TOP + VOICES * lh) return null;
  const voice = clamp(Math.floor((y - LANE_TOP) / lh), 0, VOICES - 1);
  const lane = laneRect(voice, w, h);
  if (x < lane.x - 2 || x > lane.x + lane.w + 2) return null;
  return {
    voice,
    xn: clamp((x - lane.x) / lane.w, 0, 0.99999),
    value: clamp(1 - (y - lane.y - 1.5) / (lane.h - 4), 0, 1)
  };
}
function segmentCells(x0, v0, x1, v1, span) {
  const c0 = clamp(Math.floor(x0 * span), 0, span - 1);
  const c1 = clamp(Math.floor(x1 * span), 0, span - 1);
  const start = Math.min(c0, c1);
  const end = Math.max(c0, c1);
  const values = [];
  for (let c = start; c <= end; c++) {
    const t = c1 === c0 ? 1 : (c - c0) / (c1 - c0);
    values.push(clamp(v0 + (v1 - v0) * t, 0, 1));
  }
  return { start, values };
}
function identityRow() {
  const r = [];
  for (let i = 0; i < CELLS; i++) r.push(i / CELLS);
  return r;
}
function rowsFromStored(table) {
  if (!Array.isArray(table) || table.length !== VOICES * CELLS) return null;
  const rows2 = [];
  for (let v = 0; v < VOICES; v++) {
    const row = [];
    for (let i = 0; i < CELLS; i++) {
      const x = Number(table[v * CELLS + i]);
      if (!Number.isFinite(x)) return null;
      row.push(clamp(x, 0, 1));
    }
    rows2.push(row);
  }
  return rows2;
}
function normalizeRow(values, n) {
  const out = new Array(n).fill(0);
  if (values === null || values === void 0) return out;
  if (typeof values === "number") {
    out[0] = Number.isFinite(values) ? values : 0;
    return out;
  }
  for (let i = 0; i < n && i < values.length; i++) {
    const v = Number(values[i]);
    out[i] = Number.isFinite(v) ? v : 0;
  }
  return out;
}

// devices/aliasing/js/src/paint_kit.ts
function hex(h, a) {
  var n = parseInt(h.replace("#", ""), 16);
  return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, a === void 0 ? 1 : a];
}
function withAlpha(c, a) {
  return [c[0], c[1], c[2], a];
}
function mixColor(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t];
}
function luminance(c) {
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function palette(dark) {
  if (dark) {
    return {
      dark: true,
      text: hex("#d2d2d2"),
      label: hex("#b0b0b0"),
      track: hex("#5c5c5c"),
      rule: hex("#2a2a2a"),
      field: hex("#262626"),
      sel: hex("#d6d6d6"),
      selFg: hex("#1b1b1b"),
      sizeFill: hex("#4c4c4c"),
      write: hex("#e4e4e4"),
      read: hex("#8fb0c4"),
      disp: hex("#161616"),
      voice: hex("#a6a6a6"),
      meter: hex("#9a9a9a")
    };
  }
  return {
    dark: false,
    text: hex("#111111"),
    label: hex("#262626"),
    track: hex("#6e6e6e"),
    rule: hex("#d0d0d0"),
    field: hex("#dedede"),
    sel: hex("#1f1f1f"),
    selFg: hex("#efefef"),
    sizeFill: hex("#bdbdbd"),
    write: hex("#1c1c1c"),
    read: hex("#2f5873"),
    disp: hex("#ececec"),
    voice: hex("#4a4a4a"),
    meter: hex("#3c3c3c")
  };
}
function themeIsDark(getcolor) {
  if (!getcolor) return true;
  try {
    var c = getcolor("live_control_fg");
    if (c && c.length >= 3) return luminance([Number(c[0]), Number(c[1]), Number(c[2]), 1]) > 0.45;
  } catch (e) {
  }
  return true;
}
function roleOf(varname) {
  var v = String(varname || "");
  if (v.indexOf("mod_") === 0) {
    var t = v.substring(v.lastIndexOf("_") + 1);
    if (t === "wp" || t === "sy" || t === "wa") return "write";
    if (t === "rp" || t === "sp") return "read";
    return "neutral";
  }
  if (v.indexOf("w_") === 0 || v.indexOf("tone_band") === 0) return "write";
  if (v.indexOf("r_") === 0 || v.indexOf("tone_res") === 0) return "read";
  return "neutral";
}
function accentFor(role, p) {
  if (role === "write") return p.write;
  if (role === "read") return p.read;
  return p.text;
}
function clamp2(x, lo, hi) {
  return x < lo ? lo : x > hi ? hi : x;
}
function firstNumber(v) {
  if (v === null || v === void 0) return NaN;
  if (typeof v === "object" && v.length !== void 0) return v.length ? parseFloat(v[0]) : NaN;
  return parseFloat(v);
}
function normOf(v, lo, hi, exponent) {
  if (!(hi > lo)) return 0;
  var n = clamp2((v - lo) / (hi - lo), 0, 1);
  var e = exponent > 0 ? exponent : 1;
  return Math.pow(n, 1 / e);
}
function sprintf1(fmt, v) {
  var out = "";
  var i = 0;
  while (i < fmt.length) {
    var ch = fmt.charAt(i);
    if (ch !== "%") {
      out += ch;
      i++;
      continue;
    }
    var j = i + 1;
    var spec = "";
    while (j < fmt.length && "0123456789.-+ ".indexOf(fmt.charAt(j)) >= 0) {
      spec += fmt.charAt(j);
      j++;
    }
    var conv = fmt.charAt(j);
    if (conv === "%") {
      out += "%";
    } else if (conv === "d" || conv === "i") {
      out += String(Math.round(v));
    } else if (conv === "f") {
      var dot = spec.indexOf(".");
      var prec = dot >= 0 ? parseInt(spec.substring(dot + 1), 10) : 6;
      if (isNaN(prec)) prec = 6;
      out += v.toFixed(prec);
    } else if (conv === "s") {
      out += String(v);
    } else {
      out += "%" + spec + conv;
    }
    i = j + 1;
  }
  return out;
}
function formatHz(f) {
  if (f >= 1e4) return (f / 1e3).toFixed(1) + " kHz";
  if (f >= 1e3) return (f / 1e3).toFixed(2) + " kHz";
  if (f >= 100) return String(Math.round(f)) + " Hz";
  if (f >= 10) return f.toFixed(1) + " Hz";
  return f.toFixed(2) + " Hz";
}
function formatValue(v, unitstyle, units, enumLabels) {
  if (isNaN(v)) return "";
  if (enumLabels && enumLabels.length) {
    var k = clamp2(Math.round(v), 0, enumLabels.length - 1);
    return String(enumLabels[k]);
  }
  switch (unitstyle) {
    case 0:
      return String(Math.round(v));
    case 2:
      return v >= 1e3 ? (v / 1e3).toFixed(2) + " s" : v.toFixed(v < 10 ? 2 : 0) + " ms";
    case 3:
      return formatHz(v);
    case 4:
      return (v <= -69.95 ? "-inf" : v.toFixed(1)) + " dB";
    case 5:
      return v.toFixed(Math.abs(v) < 10 ? 1 : 0) + " %";
    case 6:
      return v === 0 ? "C" : Math.abs(Math.round(v)) + (v < 0 ? "L" : "R");
    case 7:
      return (v > 0 ? "+" : "") + Math.round(v) + " st";
    case 9:
      return units ? sprintf1(units, v) : v.toFixed(2);
    default:
      return Math.abs(v) >= 100 ? String(Math.round(v)) : v.toFixed(2);
  }
}
function enumLabelsFrom(range, type) {
  if (type !== 2 || !range || typeof range !== "object" || range.length === void 0) return null;
  var out = [];
  for (var i = 0; i < range.length; i++) out.push(String(range[i]));
  return out.length ? out : null;
}
function writeIcon(label2) {
  switch (label2) {
    case "Ramp":
      return [[1, 11], [21, 1], [21, 11]];
    case "Tri":
      return [[1, 11], [11, 1], [21, 11]];
    case "Tri \xB1":
      return [[1, 11], [6, 11], [11, 1], [16, 11], [21, 11]];
    case "Sine": {
      var pts = [];
      for (var i = 0; i <= 20; i++) pts.push([1 + i, 11 - 10 * (0.5 - 0.5 * Math.cos(i / 20 * 2 * Math.PI))]);
      return pts;
    }
    case "Pulse":
      return [[1, 11], [11, 11], [11, 1], [21, 1]];
    case "Pulsar":
      return [[1, 11], [9, 1], [9, 11], [21, 11]];
    case "Spike":
      return [[1, 11], [5, 1], [9, 11], [21, 11]];
    case "Noise":
      return [[1, 7], [4, 7], [4, 2], [7, 2], [7, 9], [10, 9], [10, 4], [13, 4], [13, 10], [16, 10], [16, 3], [19, 3], [19, 6], [21, 6]];
    default:
      return null;
  }
}
function iconPath(label2, family) {
  if (family === "write") return writeIcon(label2);
  switch (label2) {
    case "Ramp":
    case "Saw":
      return [[1, 11], [21, 1], [21, 11]];
    case "Tri":
      return [[1, 11], [11, 1], [21, 11]];
    case "Tri \xB1":
      return [[1, 6], [6, 1], [16, 11], [21, 6]];
    case "Square":
      return [[1, 11], [1, 1], [11, 1], [11, 11], [21, 11], [21, 1]];
    case "S&H":
      return [[1, 8], [5, 8], [5, 3], [9, 3], [9, 10], [13, 10], [13, 5], [17, 5], [17, 9], [21, 9]];
    case "Sine": {
      var pts = [];
      for (var i = 0; i <= 20; i++) pts.push([1 + i, 6 - 5 * Math.sin(i / 20 * 2 * Math.PI)]);
      return pts;
    }
    case "Random": {
      var r = [6, 2.5, 4, 8, 10.5, 9, 4.5, 3, 6, 5];
      var q = [];
      for (var k = 0; k < r.length; k++) q.push([1 + k * 20 / (r.length - 1), r[k]]);
      return q;
    }
    default:
      return null;
  }
}
function fitText(s, maxw, measure) {
  if (measure(s) <= maxw) return s;
  var t = s;
  while (t.length > 1 && measure(t + ".") > maxw) t = t.substring(0, t.length - 1);
  return t + ".";
}

// devices/aliasing/js/src/aliasing_display.ts
inlets = 1;
outlets = 2;
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
var FPS_INTERVAL_MS = 33;
var NCH = 10;
var PAGE_TONE = 2;
var FONT = "Ableton Sans Medium";
var FONT_BOLD = "Ableton Sans Bold";
var tableBuf = null;
var headsBuf = null;
var rows = Array.from({ length: VOICES }, () => identityRow());
var heads = Array.from({ length: NCH }, () => new Array(VOICES).fill(0));
var pageValue = 0;
var modeValue = 0;
var params = {
  size: 10,
  center: 632,
  bwidth: 10,
  bres: 0,
  bslope: 1,
  bmode: 0,
  rsfreq: 140,
  rsfb: 50,
  rsmix: 50,
  rstrack: 1,
  bandon: 1,
  reson: 0
};
var zoom = 0.1;
var gesture = null;
var storeDict = new Dict();
var expectEcho = false;
var pendingRestore = null;
var timer = new Task(tick);
timer.interval = FPS_INTERVAL_MS;
function readData() {
  if (headsBuf) {
    for (let c = 0; c < NCH; c++) copyInto(heads[c], headsBuf.peek(c + 1, 0, VOICES), VOICES);
  }
  zoom = nextZoom(zoom, params.size / 100, heads[3], FPS_INTERVAL_MS / 1e3);
  if (tableBuf && !gesture) {
    const n = Math.min(CELLS, spanCells(zoom) + 1);
    for (let v = 0; v < VOICES; v++) copyInto(rows[v], tableBuf.peek(v + 1, 0, n), n);
  }
}
function tick() {
  readData();
  mgraphics.redraw();
}
function startTimer() {
  if (!timer.running) timer.repeat();
}
function effSize(v) {
  const s = heads[3][v];
  return s > 0 ? s : clamp(params.size / 100, 1e-3, 1);
}
function fs() {
  return heads[9][0] > 0 ? heads[9][0] : 48e3;
}
function tone() {
  return {
    bandOn: params.bandon > 0.5,
    resOn: params.reson > 0.5,
    center: params.center,
    width: params.bwidth,
    res: params.bres,
    slope24: params.bslope > 0.5,
    reject: params.bmode > 0.5,
    rsFreq: params.rstrack > 0.5 ? clamp(heads[8][2] || params.rsfreq, 20, 5e3) : params.rsfreq,
    rsFb: params.rsfb,
    rsMix: params.rsmix
  };
}
function storeTable() {
  if (!tableBuf) return;
  const flat = [];
  for (let v = 0; v < VOICES; v++) {
    const row = normalizeRow(tableBuf.peek(v + 1, 0, CELLS), CELLS);
    for (let i = 0; i < CELLS; i++) flat.push(Math.round(row[i] * 1e6) / 1e6);
  }
  storeDict.parse(JSON.stringify({ table: flat }));
  expectEcho = true;
  outlet(1, "dictionary", storeDict.name);
  expectEcho = false;
}
function applyRows(r) {
  if (!tableBuf) {
    pendingRestore = r;
    return;
  }
  for (let v = 0; v < VOICES; v++) tableBuf.poke(v + 1, 0, r[v]);
  rows = r.map((row) => row.slice());
  pendingRestore = null;
  if (headsBuf) headsBuf.poke(NCH, 1, 1);
  mgraphics.redraw();
}
function buffers(table, headsName, dictName) {
  tableBuf = table ? new Buffer(String(table)) : null;
  headsBuf = headsName ? new Buffer(String(headsName)) : null;
  if (!pendingRestore && dictName) {
    try {
      const r = rowsFromStored(new Dict(String(dictName)).get("table"));
      if (r) pendingRestore = r;
    } catch (e) {
      pendingRestore = null;
    }
  }
  if (pendingRestore) applyRows(pendingRestore);
  readData();
  startTimer();
  mgraphics.redraw();
}
function page(v) {
  pageValue = Math.round(Number(v)) || 0;
  gesture = null;
  mgraphics.redraw();
}
function mode(v) {
  modeValue = Number(v) ? 1 : 0;
  mgraphics.redraw();
}
function pv(name, v) {
  const n = Number(v);
  if (Number.isFinite(n) && String(name) in params) params[String(name)] = n;
  mgraphics.redraw();
}
function dictionary(name) {
  if (expectEcho) {
    expectEcho = false;
    return;
  }
  try {
    const d = new Dict(String(name));
    const r = rowsFromStored(d.get("table"));
    if (r) applyRows(r);
  } catch (e) {
    post(`aliasing_display: stored table not readable: ${e}
`);
  }
}
function bang() {
  readData();
  mgraphics.redraw();
}
function onresize(_w, _h) {
  mgraphics.redraw();
}
function notifydeleted() {
  timer.cancel();
}
function send(name, value) {
  outlet(0, name, value);
}
function onclick(x, y, _but, _cmd, shift, _caps, option) {
  const w = mgraphics.size[0];
  const icons = iconRects(w);
  if (pageValue !== PAGE_TONE && y < icons.line.y + icons.line.h + 2) {
    if (inRect(x, y, icons.line) && modeValue !== 0) {
      modeValue = 0;
      send("mode", 0);
    } else if (inRect(x, y, icons.twoD) && modeValue !== 1) {
      modeValue = 1;
      send("mode", 1);
    }
    mgraphics.redraw();
    return;
  }
  if (pageValue === PAGE_TONE) {
    const t = tone();
    const what = hitCurve(x, y, t, curveRect(w, mgraphics.size[1]), fs());
    gesture = what ? { kind: "curve", what, x0: x, c0: params.center } : null;
    return;
  }
  const hit = laneHit(x, y, w, mgraphics.size[1]);
  if (!hit) {
    gesture = null;
    return;
  }
  const voices = shift ? [0, 1, 2, 3, 4] : [hit.voice];
  const snap = voices.map((v) => rows[v].slice());
  gesture = { kind: "draw", voices, x0: hit.xn, v0: hit.value, lx: hit.xn, lv: hit.value, line: Boolean(option), voice: hit.voice, snap };
  drawSegment(hit.xn, hit.value, hit.xn, hit.value, voices);
}
function ondrag(x, y, but) {
  const w = mgraphics.size[0];
  if (!gesture) return;
  if (!but) {
    const g = gesture;
    gesture = null;
    if (g.kind === "draw") storeTable();
    mgraphics.redraw();
    return;
  }
  if (gesture.kind === "draw") {
    const lane = laneRect(gesture.voice, w, mgraphics.size[1]);
    const xn = clamp((x - lane.x) / lane.w, 0, 0.99999);
    const value = clamp(1 - (y - lane.y - 1.5) / (lane.h - 4), 0, 1);
    if (gesture.line) {
      restoreSnapshot(gesture.voices, gesture.snap);
      drawSegment(gesture.x0, gesture.v0, xn, value, gesture.voices);
    } else {
      drawSegment(gesture.lx, gesture.lv, xn, value, gesture.voices);
    }
    gesture.lx = xn;
    gesture.lv = value;
    return;
  }
  const rect = curveRect(w, mgraphics.size[1]);
  if (gesture.what === "body") {
    const center = fOfX(xOfF(gesture.c0, rect) + (x - gesture.x0), rect);
    send("center", clamp(center, 20, 2e4));
    send("bres", resOfY(y, rect));
  } else if (gesture.what === "edge") {
    send("bwidth", widthFromEdge(x, params.center, rect));
  } else if (gesture.what === "rs") {
    if (params.rstrack > 0.5) send("rstrack", 0);
    send("rsfreq", clamp(fOfX(x, rect), 20, 5e3));
    send("rsfb", fbOfY(y, rect));
    if (params.reson < 0.5) send("reson", 1);
    if (params.rsmix <= 0) send("rsmix", 50);
  }
}
function ondblclick(x, y, _but, _cmd, shift) {
  const w = mgraphics.size[0];
  gesture = null;
  if (pageValue === PAGE_TONE) {
    const e = bandEdges(tone(), fs());
    const rect = curveRect(w, mgraphics.size[1]);
    if (x > xOfF(e.lo, rect) && x < xOfF(e.hi, rect)) send("bmode", params.bmode > 0.5 ? 0 : 1);
    return;
  }
  const hit = laneHit(x, y, w, mgraphics.size[1]);
  if (!hit || !tableBuf) return;
  const ident = identityRow();
  for (const v of shift ? [0, 1, 2, 3, 4] : [hit.voice]) {
    tableBuf.poke(v + 1, 0, ident);
    rows[v] = ident.slice();
  }
  storeTable();
  mgraphics.redraw();
}
function restoreSnapshot(voices, snap) {
  voices.forEach((v, k) => {
    rows[v] = snap[k].slice();
    if (tableBuf) tableBuf.poke(v + 1, 0, rows[v]);
  });
}
function drawSegment(x0, v0, x1, v1, voices) {
  const span = spanCells(zoom);
  for (const v of voices) {
    const seg = segmentCells(x0, v0, x1, v1, span);
    for (let k = 0; k < seg.values.length; k++) rows[v][seg.start + k] = seg.values[k];
    if (tableBuf) tableBuf.poke(v + 1, seg.start, seg.values);
  }
  mgraphics.redraw();
}
function rgba(c) {
  mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
}
function label(s, x, y, c, size = 8, bold = false) {
  mgraphics.select_font_face(bold ? FONT_BOLD : FONT);
  mgraphics.set_font_size(size);
  rgba(c);
  mgraphics.move_to(x, y);
  mgraphics.show_text(s);
  return mgraphics.text_measure(s)[0];
}
function fitted(s, maxw) {
  if (mgraphics.text_measure(s)[0] <= maxw) return s;
  let t = s;
  while (t.length > 1 && mgraphics.text_measure(`${t}\u2026`)[0] > maxw) t = t.slice(0, -1);
  return `${t}\u2026`;
}
function drawHeader(w, p) {
  const tonePage = pageValue === PAGE_TONE;
  const tw = label(tonePage ? "TONE" : "TABLE", PAD, HEADER_Y + 9, p.label, 8, true);
  const icons = iconRects(w);
  const infoX = PAD + tw + 6;
  const maxw = (tonePage ? w - PAD : icons.line.x - 4) - infoX;
  const info = tonePage ? "drag band \xB7 edges = width \xB7 dbl-click = Pass/Reject \xB7 R" : tableInfo(spanCells(params.size / 100), heads[4][0], heads[5][2], fs());
  mgraphics.select_font_face(FONT);
  mgraphics.set_font_size(8);
  label(fitted(info, maxw), infoX, HEADER_Y + 9, p.label, 8);
  if (tonePage) return;
  const sel = (r, on) => {
    if (on) {
      rgba(p.sel);
      mgraphics.rectangle_rounded(r.x, r.y, r.w, r.h, 4, 4);
      mgraphics.fill();
    }
  };
  sel(icons.line, modeValue === 0);
  sel(icons.twoD, modeValue === 1);
  rgba(modeValue === 0 ? p.selFg : p.label);
  mgraphics.set_line_width(1);
  for (const dy of [2.5, 5, 7.5]) {
    mgraphics.move_to(icons.line.x + 2, icons.line.y + dy + 0.5);
    mgraphics.line_to(icons.line.x + 12, icons.line.y + dy + 0.5);
  }
  mgraphics.stroke();
  rgba(modeValue === 1 ? p.selFg : p.label);
  const bx = icons.twoD.x + 2;
  const by = icons.twoD.y + 1.5;
  for (const [x, y, ww] of [[0, 0, 3], [4, 0, 2], [7, 0, 3], [0, 5, 2], [3, 5, 4], [8, 5, 2]]) {
    mgraphics.rectangle(bx + x, by + y, ww, 3);
  }
  mgraphics.fill();
}
function drawLanes(w, h, p, lw) {
  const span = spanCells(zoom);
  for (let v = 0; v < VOICES; v++) {
    const lane = laneRect(v, w, h);
    if (v > 0) {
      rgba(p.rule);
      mgraphics.rectangle(lane.x, lane.y, lane.w, 1);
      mgraphics.fill();
    }
    if (modeValue === 1) {
      const vals = sampleColumns(rows[v], span, COLUMNS_2D);
      const cw = lane.w / COLUMNS_2D;
      for (let c = 0; c < COLUMNS_2D; c++) {
        rgba(withAlpha(p.voice, cellAlpha(vals[c])));
        mgraphics.rectangle(lane.x + c * cw, lane.y + 1, cw + 0.3, lane.h - 1);
        mgraphics.fill();
      }
    } else {
      const o = laneOutline(rows[v], span, lane);
      const path = () => {
        mgraphics.move_to(o.pts[0], o.pts[1]);
        for (let k = 2; k < o.pts.length; k += 2) mgraphics.line_to(o.pts[k], o.pts[k + 1]);
      };
      if (o.filled) {
        rgba(p.voice);
        path();
        mgraphics.close_path();
        mgraphics.fill();
      } else {
        mgraphics.set_line_join("miter");
        if (span <= 64) {
          rgba(withAlpha(p.voice, 0.14));
          mgraphics.set_line_width(lw * 3);
          path();
          mgraphics.stroke();
        }
        rgba(p.voice);
        mgraphics.set_line_width(lw);
        path();
        mgraphics.stroke();
      }
    }
    const xe = headX(effSize(v), zoom, lane);
    if (xe < lane.x + lane.w - 0.5) {
      rgba(withAlpha(p.disp, 0.6));
      mgraphics.rectangle(xe, lane.y + 1, lane.x + lane.w - xe, lane.h - 1);
      mgraphics.fill();
      rgba(withAlpha(p.label, 0.8));
      mgraphics.rectangle(Math.round(xe) - 0.5, lane.y + 1, 1, lane.h - 1);
      mgraphics.fill();
    }
    const wOn = heads[2][v] > 0.5;
    const wc = wOn ? p.write : p.track;
    const xw = headX(heads[0][v], zoom, lane);
    const xr = headX(heads[1][v], zoom, lane);
    const midY = lane.y + lane.h / 2;
    const yw = modeValue ? midY : laneY(rows[v][headCell(heads[0][v], zoom)], lane);
    const yr = modeValue ? midY : laneY(rows[v][headCell(heads[1][v], zoom)], lane);
    mgraphics.set_line_width(1);
    rgba(withAlpha(wc, 0.35));
    mgraphics.move_to(xw, lane.y + 1);
    mgraphics.line_to(xw, lane.y + lane.h);
    mgraphics.stroke();
    rgba(withAlpha(p.read, 0.35));
    mgraphics.move_to(xr, lane.y + 1);
    mgraphics.line_to(xr, lane.y + lane.h);
    mgraphics.stroke();
    rgba(wc);
    mgraphics.ellipse(xw - 2.6, yw - 2.6, 5.2, 5.2);
    mgraphics.fill();
    rgba(p.read);
    mgraphics.set_line_width(1.3);
    mgraphics.ellipse(xr - 3, yr - 3, 6, 6);
    mgraphics.stroke();
  }
  const ow = w - 2 * PAD;
  const oy = overviewY(h);
  rgba(p.rule);
  mgraphics.rectangle_rounded(PAD, oy + 1, ow, 3, 2, 2);
  mgraphics.fill();
  rgba(p.label);
  mgraphics.rectangle_rounded(PAD, oy + 1, Math.max(2, ow * clamp(params.size / 100, 1e-3, 1)), 3, 2, 2);
  mgraphics.fill();
  rgba(withAlpha(p.label, 0.45));
  mgraphics.rectangle(PAD + Math.min(ow - 1, ow * zoom), oy, 1, OVERVIEW_H);
  mgraphics.fill();
  rgba(p.voice);
  for (let v = 0; v < VOICES; v++) mgraphics.rectangle(PAD + Math.min(ow - 1, ow * effSize(v)), oy, 1, OVERVIEW_H);
  mgraphics.fill();
}
function drawCurve(w, h, p, lw) {
  const rect = curveRect(w, h);
  const t = tone();
  const sr = fs();
  const e = bandEdges(t, sr);
  const xl = xOfF(e.lo, rect);
  const xh = xOfF(e.hi, rect);
  const bandOn = t.bandOn !== false;
  const resOn = t.resOn !== false;
  const bandCol = withAlpha(t.reject ? p.read : p.write, bandOn ? 1 : 0.4);
  rgba(withAlpha(bandCol, bandOn ? 0.09 : 0.04));
  mgraphics.rectangle(xl, rect.y, Math.max(0, xh - xl), rect.h);
  mgraphics.fill();
  mgraphics.set_line_width(1);
  rgba(p.rule);
  for (const f of [100, 1e3, 1e4]) {
    const x = Math.round(xOfF(f, rect)) + 0.5;
    mgraphics.move_to(x, rect.y);
    mgraphics.line_to(x, rect.y + rect.h);
  }
  for (const db of [-24, -12, 12]) {
    const y = Math.round(yOfDb(db, rect)) + 0.5;
    mgraphics.move_to(rect.x, y);
    mgraphics.line_to(rect.x + rect.w, y);
  }
  mgraphics.stroke();
  rgba(p.track);
  const y0 = Math.round(yOfDb(0, rect)) + 0.5;
  mgraphics.move_to(rect.x, y0);
  mgraphics.line_to(rect.x + rect.w, y0);
  mgraphics.stroke();
  rgba(withAlpha(p.voice, 0.28));
  for (let v = 0; v < VOICES; v++) {
    const tv = {
      ...t,
      center: heads[6][v] > 0 ? heads[6][v] : t.center,
      width: heads[7][v] > 0 ? heads[7][v] : t.width,
      rsFreq: heads[8][v] > 0 ? heads[8][v] : t.rsFreq
    };
    for (let x = 0; x <= rect.w; x += 4) {
      const y = yOfDb(toneDb(fOfX(rect.x + x, rect), tv, sr), rect);
      if (x === 0) mgraphics.move_to(rect.x + x, y);
      else mgraphics.line_to(rect.x + x, y);
    }
    mgraphics.stroke();
  }
  const pts = [];
  for (let x = 0; x <= rect.w; x += 1) pts.push(yOfDb(toneDb(fOfX(rect.x + x, rect), t, sr), rect));
  const trace = () => {
    for (let i = 0; i < pts.length; i++) {
      if (i === 0) mgraphics.move_to(rect.x + i, pts[i]);
      else mgraphics.line_to(rect.x + i, pts[i]);
    }
  };
  rgba(withAlpha(p.write, 0.07));
  trace();
  mgraphics.line_to(rect.x + rect.w, rect.y + rect.h);
  mgraphics.line_to(rect.x, rect.y + rect.h);
  mgraphics.close_path();
  mgraphics.fill();
  rgba(withAlpha(p.write, 0.14));
  mgraphics.set_line_width(lw * 4);
  trace();
  mgraphics.stroke();
  rgba(p.write);
  mgraphics.set_line_width(lw);
  trace();
  mgraphics.stroke();
  mgraphics.set_line_width(1);
  rgba(withAlpha(bandCol, 0.6));
  for (const x of [xl, xh]) {
    mgraphics.move_to(x, rect.y);
    mgraphics.line_to(x, rect.y + rect.h);
  }
  mgraphics.stroke();
  mgraphics.set_line_width(1.2);
  for (const x of [xl, xh]) {
    rgba(p.disp);
    mgraphics.rectangle_rounded(x - 3, rect.y + 2, 6, 12, 4, 4);
    mgraphics.fill();
    rgba(bandCol);
    mgraphics.rectangle_rounded(x - 3, rect.y + 2, 6, 12, 4, 4);
    mgraphics.stroke();
  }
  const xc = xOfF(t.center, rect);
  const yc = yOfRes(t.res, rect);
  rgba(p.disp);
  mgraphics.ellipse(xc - 5, yc - 5, 10, 10);
  mgraphics.fill();
  rgba(p.write);
  mgraphics.set_line_width(1.5);
  mgraphics.ellipse(xc - 5, yc - 5, 10, 10);
  mgraphics.stroke();
  const xr = xOfF(t.rsFreq, rect);
  const yr = yOfFb(t.rsFb, rect);
  rgba(p.disp);
  mgraphics.rectangle_rounded(xr - 4.5, yr - 4.5, 9, 9, 2, 2);
  mgraphics.fill();
  rgba(resOn && t.rsMix > 0 ? p.read : withAlpha(p.read, 0.45));
  mgraphics.set_line_width(1.4);
  mgraphics.rectangle_rounded(xr - 4.5, yr - 4.5, 9, 9, 2, 2);
  mgraphics.stroke();
  label("R", xr + 7, yr + 3, p.label, 8);
  const bandLabel = !bandOn ? "BAND OFF" : t.reject ? "REJECT" : t.width >= 9.95 ? "OPEN" : "PASS";
  label(bandLabel, clamp(xl + 4, rect.x + 2, rect.x + rect.w - 40), rect.y + 22, p.label, 8);
  for (const [f, s] of [[20, "20"], [200, "200"], [2e3, "2k"], [2e4, "20k"]]) {
    const x = clamp(xOfF(f, rect) - (f === 2e4 ? 14 : f === 20 ? 0 : 6), rect.x, rect.x + rect.w - 14);
    label(s, x, rect.y + rect.h + 10, p.label, 7);
  }
}
var announced = false;
function paint() {
  const w = mgraphics.size[0];
  const h = mgraphics.size[1];
  if (!announced) {
    announced = true;
    post(`aliasing_display: v0.3 ready, ${w}x${h}, table ${tableBuf ? "bound" : "not bound yet"}
`);
  }
  let getcolor = null;
  try {
    if (typeof max !== "undefined" && typeof max.getcolor === "function") getcolor = (id) => max.getcolor(id);
  } catch (e) {
    getcolor = null;
  }
  const p = palette(themeIsDark(getcolor));
  const lw = 1;
  rgba(p.disp);
  mgraphics.rectangle_rounded(0, 0, w, h, 8, 8);
  mgraphics.fill();
  drawHeader(w, p);
  if (pageValue === PAGE_TONE) drawCurve(w, h, p, lw);
  else drawLanes(w, h, p, lw);
  if (!tableBuf) {
    rgba([0, 0, 0, 0.5]);
    mgraphics.rectangle_rounded(0, 0, w, h, 8, 8);
    mgraphics.fill();
    mgraphics.select_font_face(FONT);
    mgraphics.set_font_size(9);
    const s = "NO TABLE";
    label(s, (w - mgraphics.text_measure(s)[0]) / 2, h / 2 + 3, [1, 1, 1, 0.7], 9);
  }
}
