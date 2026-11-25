// Pure logic of the sample drop (docs/v0.3-design.md D50-D54, section 4c): which dropped files count as
// audio, how many frames the display asks buffer~ to read, and how the read frames become the 1024 cells
// of a table row. No Max globals here, so it runs and is tested in Node (js/test/drop_model.test.ts).
//
// Fit (mode 0): the whole file (up to FIT_MAX_SECONDS) resampled to the row, band-limited (D52): block
// means over D frames (D = frames / 8192, when >= 2), then a Blackman-windowed sinc low-pass at the row's
// Nyquist evaluated at the cell centres; shorter files are interpolated linearly.
// 1:1 (mode 1): the first 1024 frames, one frame per cell, silence after the file's end (D51).
// Both: peak-normalised to the full cell range, cell = 0.5 + 0.5 x (the table's value for a signal x,
// since the voices read 2 cell - 1), DC kept (D54).

import { CELLS, clamp } from "./display_model.ts";

export const FIT = 0;
export const ONE_TO_ONE = 1;
export const FIT_MAX_SECONDS = 600;
/** Fit decimates by block means down to about this many frames per cell before the sinc stage. */
export const FRAMES_PER_CELL = 8;
/** Frames per buffer~ peek while a dropped file is read. */
export const CHUNK = 65536;
export const AUDIO_EXTENSIONS = ["wav", "wave", "aif", "aiff", "aifc", "flac", "mp3", "m4a", "caf", "ogg"];

export function isAudioPath(path: string): boolean {
	const m = /\.([A-Za-z0-9]+)$/.exec(String(path).trim());
	return m !== null && AUDIO_EXTENSIONS.indexOf(m[1].toLowerCase()) >= 0;
}

/** The file name of a Max path ("Macintosh HD:/Users/x/kick.wav" or "/Users/x/kick.wav"). */
export function fileName(path: string): string {
	const s = String(path).trim();
	const k = Math.max(s.lastIndexOf("/"), s.lastIndexOf(":"));
	return k >= 0 ? s.slice(k + 1) : s;
}

/** Frames of a file from sfinfo~'s length (ms) and sample rate. */
export function fileFrames(ms: number, sr: number): number {
	return ms > 0 && sr > 0 ? Math.round((ms * sr) / 1000) : 0;
}

/** Frames to read into the drop buffer: the whole file up to FIT_MAX_SECONDS (Fit) or one row (1:1;
 *  buffer~ leaves zeros after a shorter file's end). */
export function framesToRead(mode: number, frames: number, sr: number): number {
	if (mode === ONE_TO_ONE) return CELLS;
	return Math.max(1, Math.min(frames, Math.round(FIT_MAX_SECONDS * (sr > 0 ? sr : 48000))));
}

/** Duration argument of buffer~'s read (ms): a margin past n frames; the buffer's size caps the read. */
export function readMs(n: number, sr: number): number {
	return Math.round(((n / (sr > 0 ? sr : 48000)) * 1000 + 50) * 1000) / 1000;
}

/** Block length of Fit's first stage. */
export function decimation(frames: number): number {
	return Math.max(1, Math.floor(frames / (CELLS * FRAMES_PER_CELL)));
}

export interface BlockMeans {
	push(x: ArrayLike<number>): void;
	finish(): number[];
}

/** Streaming means over blocks of d frames (the last block may be shorter). */
export function blockMeans(d: number): BlockMeans {
	const out: number[] = [];
	let acc = 0;
	let k = 0;
	return {
		push(x: ArrayLike<number>): void {
			for (let i = 0; i < x.length; i++) {
				acc += Number(x[i]) || 0;
				if (++k === d) {
					out.push(acc / d);
					acc = 0;
					k = 0;
				}
			}
		},
		finish(): number[] {
			if (k > 0) out.push(acc / k);
			acc = 0;
			k = 0;
			return out;
		},
	};
}

function blackman(u: number): number {
	// u in -1..1, 0 at both ends
	const a = Math.PI * (u + 1);
	return 0.42 - 0.5 * Math.cos(a) + 0.08 * Math.cos(2 * a);
}

/** src resampled to n points: linear interpolation when src is not longer than n (point i at frame
 *  i * m / n), else a windowed-sinc low-pass at n's Nyquist sampled at the point centres (D52). */
export function resample(src: ArrayLike<number>, n: number): number[] {
	const m = src.length;
	const out = new Array<number>(n).fill(0);
	if (m === 0) return out;
	if (m === 1) return out.fill(Number(src[0]) || 0);
	const r = m / n;
	if (r <= 1) {
		for (let i = 0; i < n; i++) {
			const t = i * r;
			const k = Math.floor(t);
			const a = src[k];
			out[i] = a + (src[Math.min(k + 1, m - 1)] - a) * (t - k);
		}
		return out;
	}
	const w = (2 * Math.PI * 0.5) / r; // 2 pi fc, fc = 0.5 / r cycles per source frame
	const hw = Math.ceil(4 * r); // half width: four cells each side
	for (let i = 0; i < n; i++) {
		const t = (i + 0.5) * r - 0.5;
		const k0 = Math.max(0, Math.ceil(t - hw));
		const k1 = Math.min(m - 1, Math.floor(t + hw));
		let acc = 0;
		let sum = 0;
		for (let k = k0; k <= k1; k++) {
			const x = k - t;
			const h = (x === 0 ? 1 : Math.sin(w * x) / (w * x)) * blackman(x / hw);
			acc += h * src[k];
			sum += h;
		}
		out[i] = sum !== 0 ? acc / sum : 0;
	}
	return out;
}

/** Signal values -> cells 0..1, peak-normalised; silence gives the flat row 0.5. */
export function toCells(x: ArrayLike<number>): number[] {
	let peak = 0;
	for (let i = 0; i < x.length; i++) peak = Math.max(peak, Math.abs(Number(x[i]) || 0));
	const out = new Array<number>(x.length);
	for (let i = 0; i < x.length; i++) out[i] = peak < 1e-9 ? 0.5 : clamp(0.5 + (0.5 * (Number(x[i]) || 0)) / peak, 0, 1);
	return out;
}

/** One table row (CELLS values 0..1) from `frames` frames that read(start, count) returns in order. */
export function fitRow(mode: number, frames: number, read: (start: number, count: number) => ArrayLike<number>): number[] {
	if (mode === ONE_TO_ONE) {
		const x = new Array<number>(CELLS).fill(0);
		const a = frames > 0 ? read(0, Math.min(frames, CELLS)) : [];
		for (let i = 0; i < a.length && i < CELLS; i++) x[i] = Number(a[i]) || 0;
		return toCells(x);
	}
	const bm = blockMeans(decimation(frames));
	for (let s = 0; s < frames; s += CHUNK) bm.push(read(s, Math.min(CHUNK, frames - s)));
	return toCells(resample(bm.finish(), CELLS));
}

/** Header text after a drop (4 s). */
export function dropSummary(name: string, frames: number, sr: number, mode: number): string {
	const secs = sr > 0 ? frames / sr : 0;
	const len = secs >= 1 ? `${secs.toFixed(2)} s` : `${Math.round(secs * 1000)} ms`;
	const cut = mode === FIT && sr > 0 && frames > FIT_MAX_SECONDS * sr ? ` (first ${FIT_MAX_SECONDS / 60} min)` : "";
	return `${name} · ${len}${cut} → ${mode === ONE_TO_ONE ? "1:1" : "FIT"} · Freeze`;
}
