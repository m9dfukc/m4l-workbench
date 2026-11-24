// aliasing_display: the table display of the Aliasing device (v8ui, mgraphics).
// Bundled by tools/js-build.mjs into devices/aliasing/aliasing_display.js (never edit that file).
// Spec: devices/aliasing/docs/gui.md section 4. Pure logic lives in display_model.ts.
//
// Messages in (inlet 0):
//   buffers <table> <heads>  names of buffer~ ---atab and ---aheads (the patch resolves ---)
//   span <0.001..1>          Size parameter (from the live.slider), no output
//   mode <0|1>               0 Line, 1 2D (from the Display Mode tab), no output
//   display <0|1>            Display on/off: off stops reading and redrawing
//   bgcolor <r g b [a]>      display background (0..1)
//   bang                     redraw once
// Outlets:
//   0  Size from dragging the edge in the display (to the Size live.slider)
//   1  display mode after a click toggled it (to the Display Mode live.tab)
//
// Max calls handlers by message name: they must stay top-level function declarations
// (tools/js-build.mjs checks the bundle for each of them, and rejects names that v8/v8ui
// handle themselves, such as size, open or hidden).

import {
	CELLS,
	COLUMNS_2D,
	DEFAULT_BG,
	Gesture,
	READ_COLOR,
	VOICES,
	VOICE_COLORS,
	WRITE_COLOR,
	cellAlpha,
	clamp,
	decimateMinMax,
	headCell,
	normalizeRow,
	parseRgba,
	plotRect,
	posToX,
	sampleColumns,
	sizeEdgeX,
	valueToY,
	withAlpha,
	type RGBA,
	type Rect,
} from "./display_model.ts";

inlets = 1;
outlets = 2;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

const FPS_INTERVAL_MS = 33; // <= 30 fps (port-decisions Q13)

let tableBuf: Buffer | null = null;
let headsBuf: Buffer | null = null;
let rows: number[][] = Array.from({ length: VOICES }, () => new Array<number>(CELLS).fill(0));
let writeHeads: number[] = new Array<number>(VOICES).fill(0);
let readHeads: number[] = new Array<number>(VOICES).fill(0);
let writeOn: number[] = new Array<number>(VOICES).fill(0);
let sizeValue = 1;
let modeValue = 0;
let displayOn = 1;
let bg: RGBA = DEFAULT_BG;
const gesture = new Gesture();

const timer = new Task(tick);
timer.interval = FPS_INTERVAL_MS;

function setRgba(c: RGBA): void {
	mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
}

function readData(): void {
	if (tableBuf) {
		for (let v = 0; v < VOICES; v++) rows[v] = normalizeRow(tableBuf.peek(v + 1, 0, CELLS), CELLS);
	}
	if (headsBuf) {
		writeHeads = normalizeRow(headsBuf.peek(1, 0, VOICES), VOICES);
		readHeads = normalizeRow(headsBuf.peek(2, 0, VOICES), VOICES);
		writeOn = normalizeRow(headsBuf.peek(3, 0, VOICES), VOICES);
	}
}

function tick(): void {
	readData();
	mgraphics.redraw();
}

function startStop(): void {
	if (displayOn && tableBuf) {
		if (!timer.running) timer.repeat();
	} else {
		timer.cancel();
	}
	mgraphics.redraw();
}

// --- message handlers ------------------------------------------------------------

function buffers(table: string, heads: string): void {
	tableBuf = table ? new Buffer(String(table)) : null;
	headsBuf = heads ? new Buffer(String(heads)) : null;
	readData();
	startStop();
}

// Not "size": v8ui intercepts `size <w> <h>` (box size) before JS sees it (bug B1, t1).
function span(v: number): void {
	sizeValue = clamp(Number(v), 0.001, 1);
	mgraphics.redraw();
}

function mode(v: number): void {
	modeValue = Number(v) ? 1 : 0;
	mgraphics.redraw();
}

function display(v: number): void {
	displayOn = Number(v) ? 1 : 0;
	startStop();
}

function bgcolor(...args: number[]): void {
	const c = parseRgba(args.map(Number));
	if (c) {
		bg = c;
		mgraphics.redraw();
	}
}

function bang(): void {
	readData();
	mgraphics.redraw();
}

function notifydeleted(): void {
	timer.cancel();
}

// --- mouse ------------------------------------------------------------------------

function onclick(x: number, y: number): void {
	gesture.down(x, y, sizeValue, mgraphics.size[0]);
}

function ondrag(x: number, y: number, button: number): void {
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

// --- drawing ----------------------------------------------------------------------

function drawGrid(plot: Rect): void {
	mgraphics.set_line_width(1);
	setRgba([1, 1, 1, 0.07]);
	for (let k = 1; k < 4; k++) {
		const y = Math.round(plot.y + (k * plot.h) / 4) + 0.5;
		mgraphics.move_to(plot.x, y);
		mgraphics.line_to(plot.x + plot.w, y);
		const x = Math.round(plot.x + (k * plot.w) / 4) + 0.5;
		mgraphics.move_to(x, plot.y);
		mgraphics.line_to(x, plot.y + plot.h);
	}
	mgraphics.stroke();
}

function drawLines(plot: Rect): void {
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
	// Heads: write = filled dot + tick at the bottom edge, read = ring + tick at the top edge.
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

function draw2D(plot: Rect): void {
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

function drawSize(plot: Rect, h: number): void {
	const ex = Math.round(sizeEdgeX(sizeValue, plot.w)) + 0.5;
	if (ex < plot.x + plot.w) {
		setRgba([0, 0, 0, 0.5]);
		mgraphics.rectangle(ex, plot.y, plot.x + plot.w - ex, plot.h);
		mgraphics.fill();
	}
	// dashed edge (drawn by hand: no dash API relied on) and a small handle at the bottom
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

function drawHeader(w: number): void {
	mgraphics.select_font_face("Ableton Sans Medium");
	mgraphics.set_font_size(9);
	setRgba([1, 1, 1, 0.5]);
	mgraphics.move_to(4, 10);
	mgraphics.show_text(modeValue ? "2D" : "LINE");
	// legend "● write  ○ read", right-aligned
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

function paint(): void {
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
