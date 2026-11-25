// aliasing_display: the display of the Aliasing device (v8ui, mgraphics), v0.2.
// Bundled by tools/js-build.mjs into devices/aliasing/aliasing_display.js (never edit that file).
// Spec: docs/redesign-t1.md R9-R11, R19, the approved mock-up, docs/v0.2-build.md section 4.
// Pure logic lives in display_model.ts (geometry, curve, gestures) and paint_kit.ts (palette).
//
// Table pages (LFO, Mod, Out): 5 stacked lanes, each zoomed to its voice's active span (effective
// Size from gen~), Line or 2D view (icons top right), write head (dot) and read head (ring), a thin
// overview of the span above the Size slider (a painted live.slider overlaid on the display).
// Mouse: drag in a lane draws that voice's row, Shift = all voices, Alt = straight line from the
// press point, double-click = identity ramp (Shift: all). The table is stored after each gesture.
// Tone page: the Band + Resonator curve with handles (drag the band = Center x / Res y, drag an
// edge = Width, double-click the band = Pass/Reject, R handle = Res Freq x / Feedback y).
//
// Messages in (inlet 0):
//   buffers <table> <heads>   names of buffer~ ---atab and ---aheads (the patch resolves ---)
//   page <0..3>               LFO, Mod, Tone, Out (from the Page live.tab)
//   mode <0|1>                Line, 2D (from the stored Display Mode live.tab)
//   pv <name> <value>         parameter values the display needs: size center bwidth bres bslope
//                             bmode rsfreq rsfb rsmix rstrack
//   dictionary <name>         the stored table (dict Blob parameter "Table"): recall or echo
//   bang                      redraw once
// Outlets:
//   0  <name> <value> for the patch's route: mode center bwidth bres bmode rsfreq rsfb rsmix rstrack
//   1  dictionary <name> -> dict ---atable (stores the table with the Live Set)
//
// Max calls handlers by message name: they stay top-level function declarations (js-build checks).

import {
	CELLS,
	COLUMNS_2D,
	CURVE_H,
	CURVE_TOP,
	HEADER_Y,
	OVERVIEW_Y,
	PAD,
	VOICES,
	bandEdges,
	cellAlpha,
	clamp,
	decimateMinMax,
	fOfX,
	fbOfY,
	hitCurve,
	headCell,
	headX,
	iconRects,
	identityRow,
	inRect,
	laneHit,
	laneRect,
	laneY,
	normalizeRow,
	resOfY,
	rowsFromStored,
	sampleColumns,
	segmentCells,
	spanCells,
	tableInfo,
	toneDb,
	widthFromEdge,
	xOfF,
	yOfDb,
	yOfFb,
	yOfRes,
	type CurveHit,
	type Rect,
	type Tone,
} from "./display_model.ts";
import { palette, themeIsDark, withAlpha, type Palette, type RGBA } from "./paint_kit.ts";

inlets = 1;
outlets = 2;

mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

const FPS_INTERVAL_MS = 33; // <= 30 fps (port-decisions Q13)
const NCH = 10; // aheads channels (gen/aliasing.genexpr header)
const PAGE_TONE = 2;
const FONT = "Ableton Sans Medium";
const FONT_BOLD = "Ableton Sans Bold";

let tableBuf: Buffer | null = null;
let headsBuf: Buffer | null = null;
let rows: number[][] = Array.from({ length: VOICES }, () => identityRow());
let heads: number[][] = Array.from({ length: NCH }, () => new Array<number>(VOICES).fill(0));
let pageValue = 0;
let modeValue = 0;
const params: Record<string, number> = {
	size: 10,
	center: 632,
	bwidth: 10,
	bres: 0,
	bslope: 1,
	bmode: 0,
	rsfreq: 140,
	rsfb: 50,
	rsmix: 0,
	rstrack: 1,
};

// mouse state
type Gesture =
	| { kind: "draw"; voices: number[]; x0: number; v0: number; lx: number; lv: number; line: boolean; voice: number; snap: number[][] }
	| { kind: "curve"; what: CurveHit; x0: number; c0: number }
	| null;
let gesture: Gesture = null;

// table storage (R10): unnamed scratch dict, cloned by the parameter-mode dict in the patch
const storeDict = new Dict();
let expectEcho = false;
let pendingRestore: number[][] | null = null;

const timer = new Task(tick);
timer.interval = FPS_INTERVAL_MS;

// ---- data ---------------------------------------------------------------------------------------

function readData(): void {
	if (tableBuf && !gesture) {
		for (let v = 0; v < VOICES; v++) rows[v] = normalizeRow(tableBuf.peek(v + 1, 0, CELLS), CELLS);
	}
	if (headsBuf) {
		for (let c = 0; c < NCH; c++) heads[c] = normalizeRow(headsBuf.peek(c + 1, 0, VOICES), VOICES);
	}
}

function tick(): void {
	readData();
	mgraphics.redraw();
}

function startTimer(): void {
	if (!timer.running) timer.repeat();
}

function effSize(v: number): number {
	const s = heads[3][v];
	return s > 0 ? s : clamp(params.size / 100, 0.001, 1);
}

function fs(): number {
	return heads[9][0] > 0 ? heads[9][0] : 48000;
}

function tone(): Tone {
	return {
		center: params.center,
		width: params.bwidth,
		res: params.bres,
		slope24: params.bslope > 0.5,
		reject: params.bmode > 0.5,
		rsFreq: params.rstrack > 0.5 ? clamp(heads[8][2] || params.rsfreq, 20, 5000) : params.rsfreq,
		rsFb: params.rsfb,
		rsMix: params.rsmix,
	};
}

function curveRect(w: number): Rect {
	return { x: PAD, y: CURVE_TOP, w: w - 2 * PAD, h: CURVE_H };
}

// ---- storage ------------------------------------------------------------------------------------

function storeTable(): void {
	if (!tableBuf) return;
	const flat: number[] = [];
	for (let v = 0; v < VOICES; v++) {
		const row = normalizeRow(tableBuf.peek(v + 1, 0, CELLS), CELLS);
		for (let i = 0; i < CELLS; i++) flat.push(Math.round(row[i] * 1e6) / 1e6);
	}
	storeDict.parse(JSON.stringify({ table: flat }));
	expectEcho = true;
	outlet(1, "dictionary", storeDict.name);
	expectEcho = false;
}

function applyRows(r: number[][]): void {
	if (!tableBuf) {
		pendingRestore = r;
		return;
	}
	for (let v = 0; v < VOICES; v++) tableBuf.poke(v + 1, 0, r[v]);
	rows = r.map((row) => row.slice());
	pendingRestore = null;
	// tell gen~ that the table is valid (it skips its identity init when it starts after this)
	if (headsBuf) headsBuf.poke(NCH, 1, 1);
	mgraphics.redraw();
}

// ---- message handlers ---------------------------------------------------------------------------

function buffers(table: string, headsName: string): void {
	tableBuf = table ? new Buffer(String(table)) : null;
	headsBuf = headsName ? new Buffer(String(headsName)) : null;
	if (pendingRestore) applyRows(pendingRestore);
	readData();
	startTimer();
	mgraphics.redraw();
}

function page(v: number): void {
	pageValue = Math.round(Number(v)) || 0;
	gesture = null;
	mgraphics.redraw();
}

function mode(v: number): void {
	modeValue = Number(v) ? 1 : 0;
	mgraphics.redraw();
}

function pv(name: string, v: number): void {
	const n = Number(v);
	if (Number.isFinite(n) && String(name) in params) params[String(name)] = n;
	mgraphics.redraw();
}

function dictionary(name: string): void {
	if (expectEcho) {
		expectEcho = false;
		return;
	}
	try {
		const d = new Dict(String(name));
		const r = rowsFromStored(d.get("table"));
		if (r) applyRows(r);
	} catch (e) {
		post(`aliasing_display: stored table not readable: ${e}\n`);
	}
}

function bang(): void {
	readData();
	mgraphics.redraw();
}

function notifydeleted(): void {
	timer.cancel();
}

// ---- mouse --------------------------------------------------------------------------------------

function send(name: string, value: number): void {
	outlet(0, name, value);
}

function onclick(x: number, y: number, _but: number, _cmd: number, shift: number, _caps: number, option: number): void {
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
		const what = hitCurve(x, y, t, curveRect(w), fs());
		gesture = what ? { kind: "curve", what, x0: x, c0: params.center } : null;
		return;
	}
	const hit = laneHit(x, y, w);
	if (!hit) {
		gesture = null;
		return;
	}
	const voices = shift ? [0, 1, 2, 3, 4] : [hit.voice];
	const snap = voices.map((v) => rows[v].slice());
	gesture = { kind: "draw", voices, x0: hit.xn, v0: hit.value, lx: hit.xn, lv: hit.value, line: Boolean(option), voice: hit.voice, snap };
	drawSegment(hit.xn, hit.value, hit.xn, hit.value, voices);
}

function ondrag(x: number, y: number, but: number): void {
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
		const lane = laneRect(gesture.voice, w);
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
	const rect = curveRect(w);
	if (gesture.what === "body") {
		// the centre follows the horizontal mouse movement from the press, Res the vertical position
		const center = fOfX(xOfF(gesture.c0, rect) + (x - gesture.x0), rect);
		send("center", clamp(center, 20, 20000));
		send("bres", resOfY(y, rect));
	} else if (gesture.what === "edge") {
		send("bwidth", widthFromEdge(x, params.center, rect));
	} else if (gesture.what === "rs") {
		if (params.rstrack > 0.5) send("rstrack", 0);
		send("rsfreq", clamp(fOfX(x, rect), 20, 5000));
		send("rsfb", fbOfY(y, rect));
		if (params.rsmix <= 0) send("rsmix", 50);
	}
}

function ondblclick(x: number, y: number, _but: number, _cmd: number, shift: number): void {
	const w = mgraphics.size[0];
	gesture = null;
	if (pageValue === PAGE_TONE) {
		const e = bandEdges(tone(), fs());
		const rect = curveRect(w);
		if (x > xOfF(e.lo, rect) && x < xOfF(e.hi, rect)) send("bmode", params.bmode > 0.5 ? 0 : 1);
		return;
	}
	const hit = laneHit(x, y, w);
	if (!hit || !tableBuf) return;
	const ident = identityRow();
	for (const v of shift ? [0, 1, 2, 3, 4] : [hit.voice]) {
		tableBuf.poke(v + 1, 0, ident);
		rows[v] = ident.slice();
	}
	storeTable();
	mgraphics.redraw();
}

/** Straight-line mode redraws from the press point on each move: back to the rows at the press. */
function restoreSnapshot(voices: number[], snap: number[][]): void {
	voices.forEach((v, k) => {
		rows[v] = snap[k].slice();
		if (tableBuf) tableBuf.poke(v + 1, 0, rows[v]);
	});
}

function drawSegment(x0: number, v0: number, x1: number, v1: number, voices: number[]): void {
	for (const v of voices) {
		const span = spanCells(effSize(v));
		const seg = segmentCells(x0, v0, x1, v1, span);
		for (let k = 0; k < seg.values.length; k++) rows[v][seg.start + k] = seg.values[k];
		if (tableBuf) tableBuf.poke(v + 1, seg.start, seg.values);
	}
	mgraphics.redraw();
}

// ---- drawing ------------------------------------------------------------------------------------

function rgba(c: RGBA): void {
	mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
}

function label(s: string, x: number, y: number, c: RGBA, size = 8, bold = false): number {
	mgraphics.select_font_face(bold ? FONT_BOLD : FONT);
	mgraphics.set_font_size(size);
	rgba(c);
	mgraphics.move_to(x, y);
	mgraphics.show_text(s);
	return mgraphics.text_measure(s)[0];
}

function fitted(s: string, maxw: number): string {
	if (mgraphics.text_measure(s)[0] <= maxw) return s;
	let t = s;
	while (t.length > 1 && mgraphics.text_measure(`${t}…`)[0] > maxw) t = t.slice(0, -1);
	return `${t}…`;
}

function drawHeader(w: number, p: Palette): void {
	const tonePage = pageValue === PAGE_TONE;
	const tw = label(tonePage ? "TONE" : "TABLE", PAD, HEADER_Y + 9, p.label, 8, true);
	const icons = iconRects(w);
	const infoX = PAD + tw + 6;
	const maxw = (tonePage ? w - PAD : icons.line.x - 4) - infoX;
	const info = tonePage
		? "drag band · edges = width · dbl-click = Pass/Reject · R"
		: tableInfo(spanCells(effSize(0)), heads[4][0], heads[5][2], fs());
	mgraphics.select_font_face(FONT);
	mgraphics.set_font_size(8);
	label(fitted(info, maxw), infoX, HEADER_Y + 9, p.label, 8);
	if (tonePage) return;
	// Line / 2D icons
	const sel = (r: Rect, on: boolean): void => {
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

function drawLanes(w: number, p: Palette, lw: number): void {
	for (let v = 0; v < VOICES; v++) {
		const lane = laneRect(v, w);
		const size = effSize(v);
		const span = spanCells(size);
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
			const cols = Math.max(1, Math.floor(lane.w));
			const env = decimateMinMax(rows[v], span, cols);
			const path = (): void => {
				for (let c = 0; c < cols; c++) {
					const x = lane.x + c + 0.5;
					const yh = laneY(env.max[c], lane);
					const yl = laneY(env.min[c], lane);
					if (c === 0) mgraphics.move_to(x, yh);
					else mgraphics.line_to(x, yh);
					if (yl - yh > 0.5) mgraphics.line_to(x, yl);
				}
			};
			mgraphics.set_line_join("round");
			rgba(withAlpha(p.voice, 0.14));
			mgraphics.set_line_width(lw * 4);
			path();
			mgraphics.stroke();
			rgba(p.voice);
			mgraphics.set_line_width(lw);
			path();
			mgraphics.stroke();
		}
		// heads: write = line + dot, read = line + ring
		const wOn = heads[2][v] > 0.5;
		const wc = wOn ? p.write : p.track;
		const xw = headX(heads[0][v], size, lane);
		const xr = headX(heads[1][v], size, lane);
		const midY = lane.y + lane.h / 2;
		const yw = modeValue ? midY : laneY(rows[v][headCell(heads[0][v], size)], lane);
		const yr = modeValue ? midY : laneY(rows[v][headCell(heads[1][v], size)], lane);
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
	// overview of the span in the whole row (above the Size slider)
	const ow = w - 2 * PAD;
	rgba(p.rule);
	mgraphics.rectangle_rounded(PAD, OVERVIEW_Y, ow, 3, 2, 2);
	mgraphics.fill();
	rgba(p.label);
	mgraphics.rectangle_rounded(PAD, OVERVIEW_Y, Math.max(2, ow * clamp(params.size / 100, 0.001, 1)), 3, 2, 2);
	mgraphics.fill();
}

function drawCurve(w: number, p: Palette, lw: number): void {
	const rect = curveRect(w);
	const t = tone();
	const sr = fs();
	const e = bandEdges(t, sr);
	const xl = xOfF(e.lo, rect);
	const xh = xOfF(e.hi, rect);
	const bandCol = t.reject ? p.read : p.write;
	// band shading
	rgba(withAlpha(bandCol, 0.09));
	mgraphics.rectangle(xl, rect.y, Math.max(0, xh - xl), rect.h);
	mgraphics.fill();
	// grid
	mgraphics.set_line_width(1);
	rgba(p.rule);
	for (const f of [100, 1000, 10000]) {
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
	// per-voice curves (spread, modulation) from gen~'s display data
	rgba(withAlpha(p.voice, 0.28));
	for (let v = 0; v < VOICES; v++) {
		const tv: Tone = {
			...t,
			center: heads[6][v] > 0 ? heads[6][v] : t.center,
			width: heads[7][v] > 0 ? heads[7][v] : t.width,
			rsFreq: heads[8][v] > 0 ? heads[8][v] : t.rsFreq,
		};
		for (let x = 0; x <= rect.w; x += 4) {
			const y = yOfDb(toneDb(fOfX(rect.x + x, rect), tv, sr), rect);
			if (x === 0) mgraphics.move_to(rect.x + x, y);
			else mgraphics.line_to(rect.x + x, y);
		}
		mgraphics.stroke();
	}
	// main curve with fill and glow
	const pts: number[] = [];
	for (let x = 0; x <= rect.w; x += 1) pts.push(yOfDb(toneDb(fOfX(rect.x + x, rect), t, sr), rect));
	const trace = (): void => {
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
	// edges, grips, centre handle, resonator handle
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
	rgba(t.rsMix > 0 ? p.read : withAlpha(p.read, 0.45));
	mgraphics.set_line_width(1.4);
	mgraphics.rectangle_rounded(xr - 4.5, yr - 4.5, 9, 9, 2, 2);
	mgraphics.stroke();
	label("R", xr + 7, yr + 3, p.label, 8);
	const bandLabel = t.reject ? "REJECT" : t.width >= 9.95 ? "OPEN" : "PASS";
	label(bandLabel, clamp(xl + 4, rect.x + 2, rect.x + rect.w - 40), rect.y + 22, p.label, 8);
	// axis
	for (const [f, s] of [[20, "20"], [200, "200"], [2000, "2k"], [20000, "20k"]] as [number, string][]) {
		const x = clamp(xOfF(f, rect) - (f === 20000 ? 14 : f === 20 ? 0 : 6), rect.x, rect.x + rect.w - 14);
		label(s, x, rect.y + rect.h + 10, p.label, 7);
	}
}

let announced = false;

function paint(): void {
	const w = mgraphics.size[0];
	const h = mgraphics.size[1];
	if (!announced) {
		announced = true;
		post(`aliasing_display: v0.2 ready, ${w}x${h}, table ${tableBuf ? "bound" : "not bound yet"}\n`);
	}
	let getcolor: ((id: string) => any) | null = null;
	try {
		if (typeof max !== "undefined" && typeof max.getcolor === "function") getcolor = (id: string) => max.getcolor(id);
	} catch (e) {
		getcolor = null;
	}
	const p = palette(themeIsDark(getcolor));
	const lw = 1;
	rgba(p.disp);
	mgraphics.rectangle_rounded(0, 0, w, h, 8, 8);
	mgraphics.fill();
	drawHeader(w, p);
	if (pageValue === PAGE_TONE) drawCurve(w, p, lw);
	else drawLanes(w, p, lw);
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
