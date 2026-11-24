// GENERATED from devices/aliasing/js/src/aliasing_pages.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/pages_model.ts
var PAGE_PREFIXES = ["mod_", "tone_", "out_"];
function visibilityFor(varname, page) {
  if (!varname) return null;
  const p = PAGE_PREFIXES.findIndex((prefix) => varname.startsWith(prefix));
  if (p < 0) return null;
  return p === clampPage(page);
}
function clampPage(page) {
  if (!Number.isFinite(page)) return 0;
  return Math.min(PAGE_PREFIXES.length - 1, Math.max(0, Math.round(page)));
}

// devices/aliasing/js/src/aliasing_pages.ts
inlets = 1;
outlets = 0;
var current = 0;
function apply(page) {
  current = clampPage(page);
  let obj = patcher.firstobject;
  while (obj) {
    const vis = visibilityFor(obj.varname, current);
    if (vis !== null && Boolean(obj.hidden) === vis) obj.hidden = !vis;
    obj = obj.nextobject;
  }
}
function msg_int(page) {
  apply(page);
}
function msg_float(page) {
  apply(page);
}
function bang() {
  apply(current);
}
