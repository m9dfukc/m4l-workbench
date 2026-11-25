// GENERATED from devices/aliasing/js/src/aliasing_pages.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/pages_model.ts
var PAGES = ["lfo", "mod", "tone", "out"];
var PAGE_TONE = 2;
function initialState() {
  return { page: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1, wshape: 1 };
}
function symLabelOf(shape) {
  const k = Math.round(Number(shape)) || 0;
  if (k <= 0) return "curve";
  if (k <= 3) return "skew";
  if (k === 5) return "duty";
  if (k === 7) return "smooth";
  return "width";
}
function clampPage(page2) {
  if (!Number.isFinite(page2)) return 0;
  return Math.min(PAGES.length - 1, Math.max(0, Math.round(page2)));
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
  const p = clampPage(s.page);
  let areaOk;
  const pageIndex = PAGES.indexOf(area);
  if (pageIndex >= 0) areaOk = pageIndex === p;
  else if (area === "tbl") areaOk = p !== PAGE_TONE;
  else if (area === "w" || area === "r") areaOk = true;
  else return null;
  const c = condOk(area, parts[1], s, parts[2] || "");
  if (c === null) return null;
  return areaOk && c;
}
function initialActive() {
  return { track: 1, wactive: 1, drvon: 1, bandon: 1, reson: 0, limon: 1 };
}
var CLEAN_IDLE = ["w_free_pitch", "w_sync_note", "w_fine", "w_sync_mult", "w_sync_div", "w_sym", "w_shape"];
function activeFor(varname, a) {
  if (!varname) return null;
  const n = String(varname);
  if (CLEAN_IDLE.indexOf(n) >= 0) return !(a.wactive > 1.5);
  if (n.slice(-3) === "_on") return null;
  if (n === "tone_drive") return a.drvon > 0.5;
  if (n.indexOf("tone_band_") === 0) return a.bandon > 0.5;
  if (n === "tone_res_freq") return a.reson > 0.5 && !(a.track > 0.5);
  if (n.indexOf("tone_res_") === 0) return a.reson > 0.5;
  if (n.indexOf("out_lim_") === 0) return a.limon > 0.5;
  return null;
}
function panelColor(r, g, b) {
  const ok = [r, g, b].every((x) => Number.isFinite(x));
  if (!ok) return [0, 0, 0, 0.07];
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  if (lum > 0.5) return [r * 0.92, g * 0.92, b * 0.92, 1];
  return [r + (1 - r) * 0.06, g + (1 - g) * 0.06, b + (1 - b) * 0.06, 1];
}
var DISPLAY_RECT = [308, 6, 328, 136];
var DISPLAY_RECT_TONE = [308, 6, 328, 157];
function displayRectFor(page2) {
  return clampPage(page2) === PAGE_TONE ? DISPLAY_RECT_TONE : DISPLAY_RECT;
}

// devices/aliasing/js/src/aliasing_pages.ts
inlets = 1;
outlets = 0;
var state = initialState();
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
    post(`aliasing_pages: v0.3 ready, ${touched} paged objects
`);
  }
}
function setDisplayRect(obj) {
  const want = displayRectFor(state.page);
  let cur = [];
  try {
    cur = obj.getboxattr("presentation_rect") || [];
  } catch (e) {
    cur = [];
  }
  const same = cur.length === 4 && want.every((x, i) => Math.abs(Number(cur[i]) - x) < 0.5);
  if (!same) obj.setboxattr("presentation_rect", want[0], want[1], want[2], want[3]);
}
function page(v) {
  state.page = clampPage(Number(v));
  apply();
}
function wmode(v) {
  state.wmode = Number(v) || 0;
  apply();
}
function rmode(v) {
  state.rmode = Number(v) || 0;
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
  let obj = patcher.firstobject;
  while (obj) {
    const name = String(obj.varname || "");
    if (name.indexOf("panel_") === 0) obj.message("bgfillcolor", c[0], c[1], c[2], c[3]);
    obj = obj.nextobject;
  }
}
