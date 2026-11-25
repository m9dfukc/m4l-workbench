// Pure display logic for aliasing_display (v8ui): geometry, decimation, the fs fraction hint,
// the tone curve and the mouse gestures. No Max globals here, so it runs and is tested in Node
// (js/test/display_model.test.ts). Spec: docs/redesign-t1.md R9-R11, R19; docs/v0.2-build.md
// section 4; docs/v0.3-design.md D7-D9 (zoom to the Size control, fast line view, slider below).

export const CELLS = 1024;
export const VOICES = 5;
export const COLUMNS_2D = 64;
export const SIZE_MIN = 0.001;

/** Display box 328 x 136 (hybrid face, v0.3): the Size live.slider sits below it, never overlapping
 *  (D9). Lane and curve geometry follow the box height, so the shell may change it. Below COMPACT_H
 *  (option (b): 496 x 85, D33) the lanes take a fixed share and the overview shrinks to 3 px, so the
 *  five lanes stay 13 px high (face review b.4). */
export const W = 328;
export const H = 136;
export const PAD = 4;
export const HEADER_Y = 3;
export const HEADER_H = 12;
export const LANE_TOP = 17;
export const OVERVIEW_H = 5;
export const CURVE_TOP = 17;
export const COMPACT_H = 100;

export interface Rect {
	x: number;
	y: number;
	w: number;
	h: number;
}

export function clamp(x: number, lo: number, hi: number): number {
	return x < lo ? lo : x > hi ? hi : x;
}

/** Height of the span overview strip: 5 px, 3 px in the compact layout. */
export function overviewHeight(h = H): number {
	return h < COMPACT_H ? 3 : OVERVIEW_H;
}

/** Top of the span overview (the 5 voices' spans over the whole row) at the bottom of the display. */
export function overviewY(h = H): number {
	return h < COMPACT_H ? h - overviewHeight(h) : h - PAD - OVERVIEW_H + 1;
}

export function laneHeight(h = H): number {
	return (overviewY(h) - (h < COMPACT_H ? 0 : 2) - LANE_TOP) / VOICES;
}

export function laneRect(v: number, w = W, h = H): Rect {
	const lh = laneHeight(h);
	return { x: PAD, y: LANE_TOP + v * lh, w: w - 2 * PAD, h: lh };
}

/** The tone curve area (frequency labels below it). */
export function curveRect(w = W, h = H): Rect {
	return { x: PAD, y: CURVE_TOP, w: w - 2 * PAD, h: h - CURVE_TOP - 14 };
}

/** Display zoom (D7): the Size control, opened at once to a larger modulated voice span, closed again
 *  slowly (in the log domain, time constant tau seconds, so about 1 s for tau 0.35). */
export function nextZoom(prev: number, base: number, spans: ArrayLike<number>, dt: number, tau = 0.35): number {
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

/** Line view outline of a lane (D8), as x/y pairs.
 *  - span <= half the lane width: cell-exact steps (2 points per cell), to be stroked thinly;
 *  - wider spans: a closed per-pixel min/max band (upper edge forward, lower edge back, at least
 *    1 px thick), to be filled. Filling one polygon is far cheaper in Max than stroking a dense
 *    zigzag with round joins (the v0.2 slowdown at large Size, t3). */
export function laneOutline(row: ArrayLike<number>, span: number, lane: Rect): { pts: number[]; filled: boolean } {
	const n = Math.max(1, Math.min(span, row.length));
	const pts: number[] = [];
	if (n * 2 <= lane.w) {
		for (let c = 0; c < n; c++) {
			const y = laneY(row[c], lane);
			pts.push(lane.x + (c / n) * lane.w, y, lane.x + ((c + 1) / n) * lane.w, y);
		}
		return { pts, filled: false };
	}
	const cols = Math.max(1, Math.floor(lane.w));
	const env = decimateMinMax(row, n, cols);
	const lo: number[] = [];
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

/** Copy finite numbers into an existing row (no allocation per frame); missing values become 0. */
export function copyInto(out: number[], values: ArrayLike<number> | number | null | undefined, n: number): void {
	if (values === null || values === undefined) {
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

/** The Line / 2D icons in the header, right-aligned. */
export function iconRects(w = W): { line: Rect; twoD: Rect } {
	return {
		line: { x: w - PAD - 30, y: HEADER_Y, w: 14, h: 11 },
		twoD: { x: w - PAD - 14, y: HEADER_Y, w: 14, h: 11 },
	};
}

/** The sample drop's Fit / 1:1 pills (D54), left of the Line / 2D icons. */
export function fitRects(w = W): { fit: Rect; one: Rect } {
	const line = iconRects(w).line;
	const one = { x: line.x - 6 - 18, y: HEADER_Y, w: 18, h: 11 };
	return { fit: { x: one.x - 19, y: HEADER_Y, w: 19, h: 11 }, one };
}

export function inRect(x: number, y: number, r: Rect): boolean {
	return x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h;
}

/** Active cells of a voice for an effective Size (0.001..1). */
export function spanCells(size: number): number {
	return Math.max(1, Math.round(clamp(size, SIZE_MIN, 1) * CELLS));
}

/** Table value 0..1 -> y in a lane (1 at the top, 1.5 px margins). */
export function laneY(value: number, lane: Rect): number {
	return lane.y + 1.5 + (1 - clamp(value, 0, 1)) * (lane.h - 4);
}

/** Head position (0..1 of the whole row) -> x in a lane zoomed to the span. */
export function headX(head: number, size: number, lane: Rect): number {
	return lane.x + clamp(head / clamp(size, SIZE_MIN, 1), 0, 1) * lane.w;
}

/** Cell under a head position, inside the span. */
export function headCell(head: number, size: number): number {
	const span = spanCells(size);
	return clamp(Math.floor(clamp(head, 0, 1) * CELLS), 0, span - 1);
}

/** Min/max envelope of the first `span` cells of a row per pixel column. */
export function decimateMinMax(row: ArrayLike<number>, span: number, cols: number): { min: number[]; max: number[] } {
	const n = Math.min(span, row.length);
	const min: number[] = [];
	const max: number[] = [];
	for (let c = 0; c < cols; c++) {
		const i0 = Math.floor((c * n) / cols);
		const i1 = Math.max(i0 + 1, Math.floor(((c + 1) * n) / cols));
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

/** Value at the centre cell of each of `cols` columns over the span (2D view). */
export function sampleColumns(row: ArrayLike<number>, span: number, cols: number): number[] {
	const out: number[] = [];
	const n = Math.min(span, row.length);
	for (let c = 0; c < cols; c++) {
		const i = Math.min(n - 1, Math.floor(((c + 0.5) * n) / cols));
		out.push(i >= 0 ? row[i] : 0);
	}
	return out;
}

/** 2D cell opacity (mock-up: 0.06 + 0.8 * value). */
export function cellAlpha(v: number): number {
	return 0.06 + 0.8 * clamp(v, 0, 1);
}

// ---- frequency texts -------------------------------------------------------------------------

export function fmtHz(f: number): string {
	if (!Number.isFinite(f)) return "-";
	if (f >= 1000) return `${(f / 1000).toFixed(2)} kHz`;
	if (f >= 100) return `${Math.round(f)} Hz`;
	if (f >= 10) return `${f.toFixed(1)} Hz`;
	return `${f.toFixed(2)} Hz`;
}

/**
 * The write pattern depends on how close f / fs is to a simple fraction (table-behaviour.md §6).
 * Returns the nearest P/Q (Q <= 8) and the drift f - fs * P/Q, or null below fs/16 or when the
 * drift is larger than maxBeat.
 */
export function fsFraction(f: number, fs: number, maxBeat = 200): { p: number; q: number; beat: number } | null {
	if (!(fs > 0) || !(f >= fs / 16)) return null;
	const r = f / fs;
	let best: { p: number; q: number; beat: number } | null = null;
	for (let q = 1; q <= 8; q++) {
		const p = Math.round(r * q);
		if (p < 1) continue;
		const beat = f - (fs * p) / q;
		if (!best || Math.abs(beat) < Math.abs(best.beat) - 1e-9) best = { p, q, beat };
	}
	if (!best || Math.abs(best.beat) > maxBeat) return null;
	const g = gcd(best.p, best.q);
	return { p: best.p / g, q: best.q / g, beat: best.beat };
}

function gcd(a: number, b: number): number {
	return b ? gcd(b, a % b) : a;
}

export function fmtFraction(fr: { p: number; q: number; beat: number }): string {
	const head = fr.q === 1 ? (fr.p === 1 ? "fs" : `${fr.p}fs`) : fr.p === 1 ? `fs/${fr.q}` : `${fr.p}fs/${fr.q}`;
	const b = fr.beat;
	return `${head} ${b >= 0 ? "+" : "-"}${Math.abs(b) < 10 ? Math.abs(b).toFixed(1) : Math.round(Math.abs(b))} Hz`;
}

/** Header info of the table pages. */
export function tableInfo(spanOfVoice1: number, fw: number, fr: number, fs: number): string {
	const frac = fsFraction(fw, fs);
	const w = `W ${fmtHz(fw)}${frac ? ` = ${fmtFraction(frac)}` : ""}`;
	return `${spanOfVoice1} cells · ${w} · R ${fmtHz(fr)}`;
}

// ---- tone curve (R19) -------------------------------------------------------------------------

export const F_MIN = 20;
export const F_MAX = 20000;

export function xOfF(f: number, rect: Rect): number {
	return rect.x + (Math.log(clamp(f, 1, 1e6) / F_MIN) / Math.log(F_MAX / F_MIN)) * rect.w;
}

export function fOfX(x: number, rect: Rect): number {
	return F_MIN * Math.pow(F_MAX / F_MIN, clamp((x - rect.x) / rect.w, 0, 1));
}

/** dB range of the curve: +18 at the top, -36 at the bottom. */
export function yOfDb(db: number, rect: Rect): number {
	return rect.y + 4 + ((18 - clamp(db, -36, 18)) / 54) * (rect.h - 4);
}

export function dbOfY(y: number, rect: Rect): number {
	return 18 - ((y - rect.y - 4) / (rect.h - 4)) * 54;
}

/** Res 0..100 % <-> the y of the centre handle (2 dB .. 16 dB, as in the mock-up). */
export function yOfRes(res: number, rect: Rect): number {
	return yOfDb(2 + clamp(res, 0, 100) * 0.14, rect);
}

export function resOfY(y: number, rect: Rect): number {
	return clamp((dbOfY(y, rect) - 2) / 0.14, 0, 100);
}

/** Feedback -95..95 % <-> y of the resonator handle (up = peaks). */
export function yOfFb(fb: number, rect: Rect): number {
	return rect.y + 8 + (1 - (clamp(fb, -95, 95) + 95) / 190) * (rect.h - 16);
}

export function fbOfY(y: number, rect: Rect): number {
	return clamp(95 - ((y - rect.y - 8) / (rect.h - 16)) * 190, -95, 95);
}

export interface Tone {
	center: number; // Hz
	width: number; // octaves 0.2..10
	res: number; // %
	slope24: boolean;
	reject: boolean;
	rsFreq: number; // Hz (effective)
	rsFb: number; // %
	rsMix: number; // %
	bandOn?: boolean; // section switches (D17); undefined = on for the band, on for the resonator
	resOn?: boolean;
}

type C = [number, number];
const cmul = (a: C, b: C): C => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const cdiv = (a: C, b: C): C => {
	const d = b[0] * b[0] + b[1] * b[1] || 1e-30;
	return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
};
const cadd = (a: C, b: C): C => [a[0] + b[0], a[1] + b[1]];

/** Analog 2-pole low/high-pass at fc with quality q, evaluated at f. */
function sec(f: number, fc: number, q: number, high: boolean): C {
	const s: C = [0, f / fc];
	const den: C = [1 - (f / fc) * (f / fc), f / fc / q];
	return cdiv(high ? cmul(s, s) : [1, 0], den);
}

/** SVF damping as in the GenExpr: resonant stage Q from Res. */
export function resQ(res: number, slope24: boolean): number {
	const r = clamp(res, 0, 100) / 100;
	return slope24 ? 1.3066 * Math.pow(18 / 1.3066, r) : 0.7071 * Math.pow(18 / 0.7071, r);
}

/** Magnitude in dB of Band (+ Resonator) at f, following the GenExpr's structure. */
export function toneDb(f: number, t: Tone, fs = 48000): number {
	const nyq = 0.45 * fs;
	const lo = clamp(t.center * Math.pow(2, -0.5 * t.width), 10, nyq);
	const hi = clamp(t.center * Math.pow(2, 0.5 * t.width), 10, nyq);
	const qr = resQ(t.res, t.slope24);
	const edge = (fc: number, high: boolean): C =>
		t.slope24 ? cmul(sec(f, fc, 0.5412, high), sec(f, fc, qr, high)) : sec(f, fc, qr, high);
	let h: C = t.bandOn === false ? [1, 0] : t.reject ? cadd(edge(lo, false), edge(hi, true)) : cmul(edge(lo, true), edge(hi, false));
	if (t.resOn !== false && t.rsMix > 0) {
		const g = clamp(t.rsFb, -95, 95) / 100;
		const d = 1 / clamp(t.rsFreq, 20, 5000); // seconds
		const ph = -2 * Math.PI * f * d;
		const comb = cdiv([Math.sqrt(1 - g * g), 0], [1 - g * Math.cos(ph), -g * Math.sin(ph)]);
		const m = t.rsMix / 100;
		h = cmul(h, cadd([1 - m, 0], [m * comb[0], m * comb[1]]));
	}
	return 20 * Math.log10(Math.max(1e-5, Math.hypot(h[0], h[1])));
}

/** Band edges in Hz (clamped like the DSP). */
export function bandEdges(t: Tone, fs = 48000): { lo: number; hi: number } {
	const nyq = 0.45 * fs;
	return {
		lo: clamp(t.center * Math.pow(2, -0.5 * t.width), 10, nyq),
		hi: clamp(t.center * Math.pow(2, 0.5 * t.width), 10, nyq),
	};
}

export type CurveHit = "rs" | "body" | "edge" | null;

/** What a press at (x, y) grabs on the tone curve. */
export function hitCurve(x: number, y: number, t: Tone, rect: Rect, fs = 48000): CurveHit {
	const e = bandEdges(t, fs);
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

/** Band width (octaves) from dragging an edge to x. */
export function widthFromEdge(x: number, center: number, rect: Rect): number {
	return clamp(2 * Math.abs(Math.log2(fOfX(x, rect) / center)), 0.2, 10);
}

// ---- drawing into the table (R10) ----------------------------------------------------------------

/** Lane and value under (x, y), or null outside the lanes. */
export function laneHit(x: number, y: number, w = W, h = H): { voice: number; xn: number; value: number } | null {
	const lh = laneHeight(h);
	if (y < LANE_TOP || y >= LANE_TOP + VOICES * lh) return null;
	const voice = clamp(Math.floor((y - LANE_TOP) / lh), 0, VOICES - 1);
	const lane = laneRect(voice, w, h);
	if (x < lane.x - 2 || x > lane.x + lane.w + 2) return null;
	return {
		voice,
		xn: clamp((x - lane.x) / lane.w, 0, 0.99999),
		value: clamp(1 - (y - lane.y - 1.5) / (lane.h - 4), 0, 1),
	};
}

/** Cell values of a straight segment from (x0, v0) to (x1, v1) (x normalised to the span). */
export function segmentCells(x0: number, v0: number, x1: number, v1: number, span: number): { start: number; values: number[] } {
	const c0 = clamp(Math.floor(x0 * span), 0, span - 1);
	const c1 = clamp(Math.floor(x1 * span), 0, span - 1);
	const start = Math.min(c0, c1);
	const end = Math.max(c0, c1);
	const values: number[] = [];
	for (let c = start; c <= end; c++) {
		const t = c1 === c0 ? 1 : (c - c0) / (c1 - c0);
		values.push(clamp(v0 + (v1 - v0) * t, 0, 1));
	}
	return { start, values };
}

export function identityRow(): number[] {
	const r: number[] = [];
	for (let i = 0; i < CELLS; i++) r.push(i / CELLS);
	return r;
}

/** Table rows from a stored blob ({table: 5120 floats}); null when it does not hold a full table. */
export function rowsFromStored(table: unknown): number[][] | null {
	if (!Array.isArray(table) || table.length !== VOICES * CELLS) return null;
	const rows: number[][] = [];
	for (let v = 0; v < VOICES; v++) {
		const row: number[] = [];
		for (let i = 0; i < CELLS; i++) {
			const x = Number(table[v * CELLS + i]);
			if (!Number.isFinite(x)) return null;
			row.push(clamp(x, 0, 1));
		}
		rows.push(row);
	}
	return rows;
}

/** Bring a peeked buffer channel to exactly `n` finite values (missing buffer -> zeros). */
export function normalizeRow(values: ArrayLike<number> | number | null | undefined, n: number): number[] {
	const out = new Array<number>(n).fill(0);
	if (values === null || values === undefined) return out;
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
