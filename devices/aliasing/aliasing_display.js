// GENERATED from devices/aliasing/js/src/aliasing_display.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/display_model.ts
var CELLS = 1024;
var VOICES = 5;
var COLUMNS_2D = 100;
var SIZE_MIN = 1e-3;
function hexToRgba(hex, alpha = 1) {
  const h = hex.replace(/^#/, "");
  if (!/^[0-9a-fA-F]{6}$/.test(h)) throw new Error(`bad colour ${hex}`);
  const n = parseInt(h, 16);
  return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, alpha];
}
function withAlpha(c, alpha) {
  return [c[0], c[1], c[2], alpha];
}
var WRITE_COLOR = hexToRgba("#ff5c8a");
var READ_COLOR = hexToRgba("#3cc6f0");
var VOICE_COLORS = ["#f2f2f2", "#cfcfcf", "#aaaaaa", "#868686", "#666666"].map(
  (h) => hexToRgba(h)
);
var DEFAULT_BG = hexToRgba("#181818");
function clamp(x, lo, hi) {
  return x < lo ? lo : x > hi ? hi : x;
}
var HEADER = 14;
var FOOTER = 5;
function plotRect(w, h) {
  return { x: 0, y: HEADER, w, h: Math.max(1, h - HEADER - FOOTER) };
}
function valueToY(v, plot) {
  return plot.y + (1 - clamp(v, 0, 1)) * plot.h;
}
function posToX(pos, plot) {
  return plot.x + clamp(pos, 0, 1) * plot.w;
}
function headCell(pos, cells = CELLS) {
  return Math.min(cells - 1, Math.max(0, Math.floor(pos * cells)));
}
function decimateMinMax(row, cols) {
  const n = row.length;
  const min = [];
  const max = [];
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
    max.push(hi);
  }
  return { min, max };
}
function sampleColumns(row, cols) {
  const out = [];
  for (let c = 0; c < cols; c++) {
    const i = Math.min(row.length - 1, Math.floor((c + 0.5) * row.length / cols));
    out.push(i >= 0 ? row[i] : 0);
  }
  return out;
}
function cellAlpha(v) {
  return 0.06 + 0.94 * clamp(v, 0, 1);
}
function sizeEdgeX(size, w) {
  return clamp(size, SIZE_MIN, 1) * w;
}
function sizeFromX(x, w) {
  return clamp(x / Math.max(1, w), SIZE_MIN, 1);
}
var HANDLE_TOLERANCE = 6;
var CLICK_SLOP = 3;
var Gesture = class {
  constructor() {
    this.x0 = 0;
    this.y0 = 0;
    this.dragging = false;
    this.moved = false;
    this.active = false;
  }
  /** Press. Returns true when it grabbed the Size edge. */
  down(x, y, size, w) {
    this.x0 = x;
    this.y0 = y;
    this.active = true;
    this.moved = false;
    this.dragging = Math.abs(x - sizeEdgeX(size, w)) <= HANDLE_TOLERANCE;
    return this.dragging;
  }
  /** Move with the button held. Returns the new Size while dragging the edge, else null. */
  move(x, y, w) {
    if (!this.active) return null;
    if (Math.abs(x - this.x0) > CLICK_SLOP || Math.abs(y - this.y0) > CLICK_SLOP) this.moved = true;
    return this.dragging ? sizeFromX(x, w) : null;
  }
  /** Release. Returns "toggle" for a click that should switch the display mode. */
  up() {
    const wasClick = this.active && !this.dragging && !this.moved;
    this.active = false;
    this.dragging = false;
    return wasClick ? "toggle" : null;
  }
};
function parseRgba(args) {
  if (args.length < 3 || args.slice(0, 4).some((v) => typeof v !== "number" || !Number.isFinite(v))) return null;
  return [clamp(args[0], 0, 1), clamp(args[1], 0, 1), clamp(args[2], 0, 1), clamp(args.length > 3 ? args[3] : 1, 0, 1)];
}
function normalizeRow(values, n) {
  const out = new Array(n).fill(0);
  if (!values) return out;
  for (let i = 0; i < n && i < values.length; i++) {
    const v = Number(values[i]);
    out[i] = Number.isFinite(v) ? v : 0;
  }
  return out;
}

// devices/aliasing/js/src/aliasing_display.ts
inlets = 1;
outlets = 2;
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;
var FPS_INTERVAL_MS = 33;
var tableBuf = null;
var headsBuf = null;
var rows = Array.from({ length: VOICES }, () => new Array(CELLS).fill(0));
var writeHeads = new Array(VOICES).fill(0);
var readHeads = new Array(VOICES).fill(0);
var writeOn = new Array(VOICES).fill(0);
var sizeValue = 1;
var modeValue = 0;
var displayOn = 1;
var bg = DEFAULT_BG;
var gesture = new Gesture();
var timer = new Task(tick);
timer.interval = FPS_INTERVAL_MS;
function setRgba(c) {
  mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
}
function readData() {
  if (tableBuf) {
    for (let v = 0; v < VOICES; v++) rows[v] = normalizeRow(tableBuf.peek(v + 1, 0, CELLS), CELLS);
  }
  if (headsBuf) {
    writeHeads = normalizeRow(headsBuf.peek(1, 0, VOICES), VOICES);
    readHeads = normalizeRow(headsBuf.peek(2, 0, VOICES), VOICES);
    writeOn = normalizeRow(headsBuf.peek(3, 0, VOICES), VOICES);
  }
}
function tick() {
  readData();
  mgraphics.redraw();
}
function startStop() {
  if (displayOn && tableBuf) {
    if (!timer.running) timer.repeat();
  } else {
    timer.cancel();
  }
  mgraphics.redraw();
}
function buffers(table, heads) {
  tableBuf = table ? new Buffer(String(table)) : null;
  headsBuf = heads ? new Buffer(String(heads)) : null;
  readData();
  startStop();
}
function span(v) {
  sizeValue = clamp(Number(v), 1e-3, 1);
  mgraphics.redraw();
}
function mode(v) {
  modeValue = Number(v) ? 1 : 0;
  mgraphics.redraw();
}
function display(v) {
  displayOn = Number(v) ? 1 : 0;
  startStop();
}
function bgcolor(...args) {
  const c = parseRgba(args.map(Number));
  if (c) {
    bg = c;
    mgraphics.redraw();
  }
}
function bang() {
  readData();
  mgraphics.redraw();
}
function notifydeleted() {
  timer.cancel();
}
function onclick(x, y) {
  gesture.down(x, y, sizeValue, mgraphics.size[0]);
}
function ondrag(x, y, button) {
  if (button) {
    const s = gesture.move(x, y, mgraphics.size[0]);
    if (s !== null) {
      sizeValue = s;
      outlet(0, s);
      mgraphics.redraw();
    }
    return;
  }
  if (gesture.up() === "toggle") {
    modeValue = modeValue ? 0 : 1;
    outlet(1, modeValue);
    mgraphics.redraw();
  }
}
function drawGrid(plot) {
  mgraphics.set_line_width(1);
  setRgba([1, 1, 1, 0.07]);
  for (let k = 1; k < 4; k++) {
    const y = Math.round(plot.y + k * plot.h / 4) + 0.5;
    mgraphics.move_to(plot.x, y);
    mgraphics.line_to(plot.x + plot.w, y);
    const x = Math.round(plot.x + k * plot.w / 4) + 0.5;
    mgraphics.move_to(x, plot.y);
    mgraphics.line_to(x, plot.y + plot.h);
  }
  mgraphics.stroke();
}
function drawLines(plot) {
  const cols = Math.max(1, Math.floor(plot.w));
  mgraphics.set_line_width(1);
  for (let v = VOICES - 1; v >= 0; v--) {
    const env = decimateMinMax(rows[v], cols);
    setRgba(VOICE_COLORS[v]);
    for (let c = 0; c < cols; c++) {
      const x = plot.x + c + 0.5;
      const yMax = valueToY(env.max[c], plot);
      const yMin = valueToY(env.min[c], plot);
      if (c === 0) mgraphics.move_to(x, yMax);
      else mgraphics.line_to(x, yMax);
      if (yMin - yMax > 0.5) mgraphics.line_to(x, yMin);
    }
    mgraphics.stroke();
  }
  for (let v = 0; v < VOICES; v++) {
    const xw = posToX(writeHeads[v], plot);
    const yw = valueToY(rows[v][headCell(writeHeads[v])], plot);
    const wc = writeOn[v] > 0.5 ? WRITE_COLOR : withAlpha(WRITE_COLOR, 0.35);
    setRgba(wc);
    mgraphics.ellipse(xw - 2.5, yw - 2.5, 5, 5);
    mgraphics.fill();
    mgraphics.rectangle(xw - 0.75, plot.y + plot.h, 1.5, 4);
    mgraphics.fill();
    const xr = posToX(readHeads[v], plot);
    const yr = valueToY(rows[v][headCell(readHeads[v])], plot);
    setRgba(READ_COLOR);
    mgraphics.set_line_width(1.25);
    mgraphics.ellipse(xr - 3, yr - 3, 6, 6);
    mgraphics.stroke();
    mgraphics.rectangle(xr - 0.75, plot.y - 4, 1.5, 4);
    mgraphics.fill();
  }
}
function draw2D(plot) {
  const rowH = plot.h / VOICES;
  const cellW = plot.w / COLUMNS_2D;
  for (let v = 0; v < VOICES; v++) {
    const vals = sampleColumns(rows[v], COLUMNS_2D);
    const y = plot.y + v * rowH;
    for (let c = 0; c < COLUMNS_2D; c++) {
      setRgba(withAlpha(VOICE_COLORS[v], cellAlpha(vals[c])));
      mgraphics.rectangle(plot.x + c * cellW, y + 0.5, cellW + 0.25, rowH - 1);
      mgraphics.fill();
    }
    mgraphics.set_line_width(1.5);
    const wc = writeOn[v] > 0.5 ? WRITE_COLOR : withAlpha(WRITE_COLOR, 0.35);
    setRgba(wc);
    const xw = posToX(writeHeads[v], plot);
    mgraphics.move_to(xw, y);
    mgraphics.line_to(xw, y + rowH);
    mgraphics.stroke();
    setRgba(READ_COLOR);
    const xr = posToX(readHeads[v], plot);
    mgraphics.move_to(xr, y);
    mgraphics.line_to(xr, y + rowH);
    mgraphics.stroke();
  }
}
function drawSize(plot, h) {
  const ex = Math.round(sizeEdgeX(sizeValue, plot.w)) + 0.5;
  if (ex < plot.x + plot.w) {
    setRgba([0, 0, 0, 0.5]);
    mgraphics.rectangle(ex, plot.y, plot.x + plot.w - ex, plot.h);
    mgraphics.fill();
  }
  setRgba([1, 1, 1, 0.55]);
  mgraphics.set_line_width(1);
  for (let y = plot.y; y < plot.y + plot.h; y += 6) {
    mgraphics.move_to(ex, y);
    mgraphics.line_to(ex, Math.min(y + 3, plot.y + plot.h));
  }
  mgraphics.stroke();
  mgraphics.rectangle(ex - 3, h - 12, 6, 10);
  mgraphics.fill();
}
function drawHeader(w) {
  mgraphics.select_font_face("Ableton Sans Medium");
  mgraphics.set_font_size(9);
  setRgba([1, 1, 1, 0.5]);
  mgraphics.move_to(4, 10);
  mgraphics.show_text(modeValue ? "2D" : "LINE");
  const readW = mgraphics.text_measure("read")[0];
  const writeW = mgraphics.text_measure("write")[0];
  let x = w - 4 - readW;
  mgraphics.move_to(x, 10);
  mgraphics.show_text("read");
  x -= 9;
  setRgba(READ_COLOR);
  mgraphics.set_line_width(1);
  mgraphics.ellipse(x, 4, 6, 6);
  mgraphics.stroke();
  x -= 8 + writeW;
  setRgba([1, 1, 1, 0.5]);
  mgraphics.move_to(x, 10);
  mgraphics.show_text("write");
  x -= 9;
  setRgba(WRITE_COLOR);
  mgraphics.ellipse(x, 4, 6, 6);
  mgraphics.fill();
}
function paint() {
  const w = mgraphics.size[0];
  const h = mgraphics.size[1];
  const plot = plotRect(w, h);
  setRgba(bg);
  mgraphics.rectangle(0, 0, w, h);
  mgraphics.fill();
  if (modeValue) {
    draw2D(plot);
  } else {
    drawGrid(plot);
    drawLines(plot);
  }
  drawSize(plot, h);
  drawHeader(w);
  if (!tableBuf || !displayOn) {
    setRgba([0, 0, 0, 0.55]);
    mgraphics.rectangle(0, 0, w, h);
    mgraphics.fill();
    const text = tableBuf ? "DISPLAY OFF" : "NO TABLE";
    mgraphics.set_font_size(9);
    const tw = mgraphics.text_measure(text)[0];
    setRgba([1, 1, 1, 0.7]);
    mgraphics.move_to((w - tw) / 2, h / 2 + 3);
    mgraphics.show_text(text);
  }
}
