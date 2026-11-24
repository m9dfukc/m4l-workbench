// Pure display logic for aliasing_display (v8ui): geometry, colours, decimation, gestures.
// No Max globals here, so it runs and is tested in Node (js/test/display_model.test.ts).
// Spec: devices/aliasing/docs/gui.md section 4.

export const CELLS = 1024;
export const VOICES = 5;
export const COLUMNS_2D = 100;
export const SIZE_MIN = 0.001;

export type RGBA = [number, number, number, number];

export function hexToRgba(hex: string, alpha = 1): RGBA {
	const h = hex.replace(/^#/, "");
	if (!/^[0-9a-fA-F]{6}$/.test(h)) throw new Error(`bad colour ${hex}`);
	const n = parseInt(h, 16);
	return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, alpha];
}

export function withAlpha(c: RGBA, alpha: number): RGBA {
	return [c[0], c[1], c[2], alpha];
}

/** Write and read accents (gui.md section 2). */
export const WRITE_COLOR = hexToRgba("#ff5c8a");
export const READ_COLOR = hexToRgba("#3cc6f0");
/** Voice lines / cells: monochrome grey ramp, voice 1 brightest (user, 2026-11-24). */
export const VOICE_COLORS: RGBA[] = ["#f2f2f2", "#cfcfcf", "#aaaaaa", "#868686", "#666666"].map((h) =>
	hexToRgba(h),
);
/** Display background (dark theme default; the patch may send another one). */
export const DEFAULT_BG = hexToRgba("#181818");

export function clamp(x: number, lo: number, hi: number): number {
	return x < lo ? lo : x > hi ? hi : x;
}

export interface Rect {
	x: number;
	y: number;
	w: number;
	h: number;
}

/** Header band for label and legend at the top; the curves use the rest. */
export const HEADER = 14;
export const FOOTER = 5;

export function plotRect(w: number, h: number): Rect {
	return { x: 0, y: HEADER, w, h: Math.max(1, h - HEADER - FOOTER) };
}

/** Table value 0..1 -> y in the plot (1 at the top). */
export function valueToY(v: number, plot: Rect): number {
	return plot.y + (1 - clamp(v, 0, 1)) * plot.h;
}

/** Head position 0..1 of the row -> x. */
export function posToX(pos: number, plot: Rect): number {
	return plot.x + clamp(pos, 0, 1) * plot.w;
}

/** Head position 0..1 -> table cell index. */
export function headCell(pos: number, cells = CELLS): number {
	return Math.min(cells - 1, Math.max(0, Math.floor(pos * cells)));
}

/**
 * Min/max envelope of a row per pixel column, so jagged table content stays visible when 1024
 * cells are drawn into ~300 px.
 */
export function decimateMinMax(row: ArrayLike<number>, cols: number): { min: number[]; max: number[] } {
	const n = row.length;
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

/** Value at the centre cell of each of `cols` columns (2D mode). */
export function sampleColumns(row: ArrayLike<number>, cols: number): number[] {
	const out: number[] = [];
	for (let c = 0; c < cols; c++) {
		const i = Math.min(row.length - 1, Math.floor(((c + 0.5) * row.length) / cols));
		out.push(i >= 0 ? row[i] : 0);
	}
	return out;
}

/** 2D cell opacity: 0.06 + 0.94 * value (gui.md section 4). */
export function cellAlpha(v: number): number {
	return 0.06 + 0.94 * clamp(v, 0, 1);
}

export function sizeEdgeX(size: number, w: number): number {
	return clamp(size, SIZE_MIN, 1) * w;
}

export function sizeFromX(x: number, w: number): number {
	return clamp(x / Math.max(1, w), SIZE_MIN, 1);
}

export const HANDLE_TOLERANCE = 6;
export const CLICK_SLOP = 3;

/**
 * Mouse gesture on the display. A press near the Size edge drags Size; a press elsewhere that
 * is released without moving more than CLICK_SLOP px toggles Line/2D.
 */
export class Gesture {
	private x0 = 0;
	private y0 = 0;
	private dragging = false;
	private moved = false;
	private active = false;

	/** Press. Returns true when it grabbed the Size edge. */
	down(x: number, y: number, size: number, w: number): boolean {
		this.x0 = x;
		this.y0 = y;
		this.active = true;
		this.moved = false;
		this.dragging = Math.abs(x - sizeEdgeX(size, w)) <= HANDLE_TOLERANCE;
		return this.dragging;
	}

	/** Move with the button held. Returns the new Size while dragging the edge, else null. */
	move(x: number, y: number, w: number): number | null {
		if (!this.active) return null;
		if (Math.abs(x - this.x0) > CLICK_SLOP || Math.abs(y - this.y0) > CLICK_SLOP) this.moved = true;
		return this.dragging ? sizeFromX(x, w) : null;
	}

	/** Release. Returns "toggle" for a click that should switch the display mode. */
	up(): "toggle" | null {
		const wasClick = this.active && !this.dragging && !this.moved;
		this.active = false;
		this.dragging = false;
		return wasClick ? "toggle" : null;
	}
}

/** Parse `bgcolor r g b [a]` arguments (0..1 floats) into a colour, or null when invalid. */
export function parseRgba(args: number[]): RGBA | null {
	if (args.length < 3 || args.slice(0, 4).some((v) => typeof v !== "number" || !Number.isFinite(v))) return null;
	return [clamp(args[0], 0, 1), clamp(args[1], 0, 1), clamp(args[2], 0, 1), clamp(args.length > 3 ? args[3] : 1, 0, 1)];
}

/** Bring a peeked buffer channel to exactly `n` finite values (missing buffer -> zeros). */
export function normalizeRow(values: ArrayLike<number> | null | undefined, n: number): number[] {
	const out = new Array<number>(n).fill(0);
	if (!values) return out;
	for (let i = 0; i < n && i < values.length; i++) {
		const v = Number(values[i]);
		out[i] = Number.isFinite(v) ? v : 0;
	}
	return out;
}
