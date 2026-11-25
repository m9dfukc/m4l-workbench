// GENERATED from devices/aliasing/js/src/aliasing_pages.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/pages_model.ts
var PAGES = ["lfo", "mod", "tone", "out"];
var PAGE_TONE = 2;
function initialState() {
  return { page: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1 };
}
function clampPage(page2) {
  if (!Number.isFinite(page2)) return 0;
  return Math.min(PAGES.length - 1, Math.max(0, Math.round(page2)));
}
function condOk(area, cond, s) {
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
  const c = condOk(area, parts[1], s);
  if (c === null) return null;
  return areaOk && c;
}
function activeFor(varname, track2) {
  if (varname === "tone_res_freq") return !(track2 > 0.5);
  return null;
}

// devices/aliasing/js/src/aliasing_pages.ts
inlets = 1;
outlets = 0;
var state = initialState();
var trackValue = 1;
var announced = false;
function apply() {
  let obj = patcher.firstobject;
  let touched = 0;
  while (obj) {
    const name = obj.varname;
    const vis = visibilityFor(name, state);
    if (vis !== null && Boolean(obj.hidden) === vis) obj.hidden = !vis;
    if (vis !== null) touched++;
    const act = activeFor(name, trackValue);
    if (act !== null) obj.message("active", act ? 1 : 0);
    obj = obj.nextobject;
  }
  if (!announced) {
    announced = true;
    post(`aliasing_pages: v0.2 ready, ${touched} paged objects
`);
  }
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
function track(v) {
  trackValue = Number(v) || 0;
  apply();
}
function bang() {
  apply();
}
