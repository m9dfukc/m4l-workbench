// GENERATED from devices/aliasing/js/src/aliasing_pages.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/pages_model.ts
var FACES = {
  hybrid: { pages: ["lfo", "mod", "tone", "out"], tonePages: [2], strip: false, resize: true },
  b: { pages: ["lfo1", "lfo2", "env", "band", "res", "lim", "out"], tonePages: [3, 4], strip: true, resize: false }
};
var PAGES = FACES.hybrid.pages;
var PAGE_TONE = 2;
var TARGETS = ["wp", "sy", "wa", "rp", "sp", "sz", "bc", "rf", "ou"];
function faceOf(name) {
  return String(name) === "b" ? "b" : "hybrid";
}
function initialState(face2 = "hybrid") {
  return { face: face2, page: 0, target: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1, wshape: 1 };
}
function symLabelOf(shape) {
  const k = Math.round(Number(shape)) || 0;
  if (k <= 0) return "curve";
  if (k === 1) return "skew";
  if (k === 2) return "duty";
  if (k === 3) return "width";
  return "smooth";
}
function clampPage(page2, face2 = "hybrid") {
  const n = FACES[face2].pages.length;
  if (!Number.isFinite(page2)) return 0;
  return Math.min(n - 1, Math.max(0, Math.round(page2)));
}
function clampTarget(t) {
  if (!Number.isFinite(t)) return 0;
  return Math.min(TARGETS.length - 1, Math.max(0, Math.round(t)));
}
function isTonePage(page2, face2 = "hybrid") {
  return FACES[face2].tonePages.indexOf(clampPage(page2, face2)) >= 0;
}
function condOk(area, cond, s, extra) {
  const sync = (m) => m > 0.5;
  switch (cond) {
    case "free":
      return area === "w" ? !sync(s.wmode) : area === "r" ? !sync(s.rmode) : true;
    case "sync":
      return area === "w" ? sync(s.wmode) : area === "r" ? sync(s.rmode) : true;
    case "hz1":
      return !sync(s.l1mode);
    case "sy1":
      return sync(s.l1mode);
    case "hz2":
      return !sync(s.l2mode);
    case "sy2":
      return sync(s.l2mode);
    case "symlbl":
      return area === "w" ? symLabelOf(s.wshape) === extra : true;
    default:
      return true;
  }
}
function visibilityFor(varname, s) {
  if (!varname) return null;
  const parts = String(varname).split("_");
  if (parts.length < 2) return null;
  const area = parts[0];
  const spec = FACES[s.face] || FACES.hybrid;
  const p = clampPage(s.page, s.face);
  if (spec.strip && area === "mod") {
    const t = TARGETS.indexOf(parts[2] || "");
    return t < 0 ? null : t === clampTarget(s.target);
  }
  let areaOk;
  const pageIndex = spec.pages.indexOf(area);
  if (pageIndex >= 0) areaOk = pageIndex === p;
  else if (area === "tbl") areaOk = !isTonePage(p, s.face);
  else if (area === "w" || area === "r") areaOk = true;
  else return null;
  const c = condOk(area, parts[1], s, parts[2] || "");
  if (c === null) return null;
  return areaOk && c;
}
function initialActive() {
  return { track: 1, wactive: 1, drvon: 1, bandon: 1, reson: 0, limon: 1, wmode: 0, rmode: 0 };
}
var CLEAN_IDLE = ["w_free_pitch", "w_sync_note", "w_fine", "w_sync_mult", "w_sync_div", "w_sym", "w_shape"];
function activeFor(varname, a) {
  if (!varname) return null;
  const n = String(varname);
  if (CLEAN_IDLE.indexOf(n) >= 0) return !(a.wactive > 1.5);
  if (n.slice(-3) === "_on") return null;
  if (n.indexOf("mod_") === 0) return null;
  const key = n.substring(n.indexOf("_") + 1);
  if (key === "transpose") return a.wmode < 0.5 || a.rmode < 0.5;
  if (key === "syncrate") return a.wmode > 0.5 || a.rmode > 0.5;
  if (key === "drive") return a.drvon > 0.5;
  if (key.indexOf("band_") === 0) return a.bandon > 0.5;
  if (key === "res_freq") return a.reson > 0.5 && !(a.track > 0.5);
  if (key.indexOf("res_") === 0) return a.reson > 0.5;
  if (key.indexOf("lim_") === 0) return a.limon > 0.5;
  return null;
}
function lumOf(r, g, b) {
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function panelColor(r, g, b) {
  const ok = [r, g, b].every((x) => Number.isFinite(x));
  if (!ok) return [0, 0, 0, 0.07];
  if (lumOf(r, g, b) > 0.5) return [r * 0.92, g * 0.92, b * 0.92, 1];
  return [r + (1 - r) * 0.06, g + (1 - g) * 0.06, b + (1 - b) * 0.06, 1];
}
function surfaceIsDark(r, g, b) {
  return !(lumOf(r, g, b) > 0.5);
}
var hex = (h) => {
  const n = parseInt(h.replace("#", ""), 16);
  return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, 1];
};
function markerColor(role, dark, panel) {
  if (role === "write") return hex(dark ? "#e4e4e4" : "#1c1c1c");
  if (role === "read") return hex(dark ? "#8fb0c4" : "#2f5873");
  const l = hex(dark ? "#b0b0b0" : "#262626");
  return [panel[0] + (l[0] - panel[0]) * 0.45, panel[1] + (l[1] - panel[1]) * 0.45, panel[2] + (l[2] - panel[2]) * 0.45, 1];
}
function targetRole(t) {
  if (t === "wp" || t === "sy" || t === "wa") return "write";
  if (t === "rp" || t === "sp") return "read";
  return "neutral";
}
function meterColors(dark) {
  return dark ? { fill: hex("#9a9a9a"), bg: hex("#262626"), over: hex("#d2d2d2") } : { fill: hex("#3c3c3c"), bg: hex("#dedede"), over: hex("#111111") };
}
var DISPLAY_RECT = [308, 6, 328, 136];
var DISPLAY_RECT_TONE = [308, 6, 328, 157];
function displayRectFor(page2, face2 = "hybrid") {
  if (!FACES[face2].resize) return null;
  return isTonePage(page2, face2) ? DISPLAY_RECT_TONE : DISPLAY_RECT;
}

// devices/aliasing/js/src/aliasing_pages.ts
inlets = 1;
outlets = 0;
var state = initialState(faceOf(typeof jsarguments !== "undefined" ? jsarguments[1] : "hybrid"));
var act = initialActive();
var announced = false;
function apply() {
  let obj = patcher.firstobject;
  let touched = 0;
  while (obj) {
    const name = obj.varname;
    const vis = visibilityFor(name, state);
    if (vis !== null && Boolean(obj.hidden) === vis) obj.hidden = !vis;
    if (vis !== null) touched++;
    const on = activeFor(name, act);
    if (on !== null) obj.message("active", on ? 1 : 0);
    if (name === "display") setDisplayRect(obj);
    obj = obj.nextobject;
  }
  if (!announced) {
    announced = true;
    post(`aliasing_pages: v0.3b ready, face ${state.face}, ${touched} paged objects
`);
  }
}
function setDisplayRect(obj) {
  const want = displayRectFor(state.page, state.face);
  if (!want) return;
  let cur = [];
  try {
    cur = obj.getboxattr("presentation_rect") || [];
  } catch (e) {
    cur = [];
  }
  const same = cur.length === 4 && want.every((x, i) => Math.abs(Number(cur[i]) - x) < 0.5);
  if (!same) obj.setboxattr("presentation_rect", want[0], want[1], want[2], want[3]);
}
function face(v) {
  state.face = faceOf(v);
  state.page = clampPage(state.page, state.face);
  apply();
}
function page(v) {
  state.page = clampPage(Number(v), state.face);
  apply();
}
function target(v) {
  state.target = clampTarget(Number(v));
  apply();
}
function wmode(v) {
  state.wmode = Number(v) || 0;
  act.wmode = state.wmode;
  apply();
}
function rmode(v) {
  state.rmode = Number(v) || 0;
  act.rmode = state.rmode;
  apply();
}
function l1mode(v) {
  state.l1mode = Number(v) || 0;
  apply();
}
function l2mode(v) {
  state.l2mode = Number(v) || 0;
  apply();
}
function wshape(v) {
  state.wshape = Number(v) || 0;
  apply();
}
function track(v) {
  act.track = Number(v) || 0;
  apply();
}
function wactive(v) {
  act.wactive = Number(v) || 0;
  apply();
}
function drvon(v) {
  act.drvon = Number(v) || 0;
  apply();
}
function bandon(v) {
  act.bandon = Number(v) || 0;
  apply();
}
function reson(v) {
  act.reson = Number(v) || 0;
  apply();
}
function limon(v) {
  act.limon = Number(v) || 0;
  apply();
}
function bang() {
  apply();
}
function surface(_name, r, g, b, _a) {
  const c = panelColor(Number(r), Number(g), Number(b));
  const dark = surfaceIsDark(Number(r), Number(g), Number(b));
  const m = meterColors(dark);
  let obj = patcher.firstobject;
  while (obj) {
    const name = String(obj.varname || "");
    if (name.indexOf("panel_") === 0) obj.message("bgfillcolor", c[0], c[1], c[2], c[3]);
    else if (name.indexOf("mod_mark_") === 0) {
      const k = markerColor(targetRole(name.substring(9)), dark, c);
      obj.message("bgfillcolor", k[0], k[1], k[2], k[3]);
    } else if (obj.maxclass === "live.meter~") {
      for (const a of ["coldcolor", "warmcolor", "hotcolor"]) obj.message(a, m.fill[0], m.fill[1], m.fill[2], m.fill[3]);
      obj.message("overloadcolor", m.over[0], m.over[1], m.over[2], m.over[3]);
      obj.message("bgcolor", m.bg[0], m.bg[1], m.bg[2], m.bg[3]);
    }
    obj = obj.nextobject;
  }
}
