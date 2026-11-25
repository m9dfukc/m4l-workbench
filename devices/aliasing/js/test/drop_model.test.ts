// Sample drop (D50-D54): file filter, read sizes, Fit (band-limited) and 1:1 rows, normalisation.
import assert from "node:assert/strict";
import { test } from "node:test";

import { CELLS } from "../src/display_model.ts";
import {
	CHUNK,
	FIT,
	FIT_MAX_SECONDS,
	ONE_TO_ONE,
	blockMeans,
	decimation,
	dropSummary,
	fileFrames,
	fileName,
	fitRow,
	framesToRead,
	isAudioPath,
	readMs,
	resample,
	toCells,
} from "../src/drop_model.ts";

/** A reader over an array, recording the requested chunks. */
function reader(x: Float32Array | number[]) {
	const asked: [number, number][] = [];
	return {
		asked,
		read(start: number, count: number): number[] {
			asked.push([start, count]);
			return Array.from(x.slice(start, start + count));
		},
	};
}

function sine(frames: number, cycles: number, amp = 1, phase = 0): Float32Array {
	const x = new Float32Array(frames);
	for (let i = 0; i < frames; i++) x[i] = amp * Math.sin((2 * Math.PI * cycles * i) / frames + phase);
	return x;
}

function maxErr(a: number[], b: number[], from = 0, to = a.length): number {
	let e = 0;
	for (let i = from; i < to; i++) e = Math.max(e, Math.abs(a[i] - b[i]));
	return e;
}

test("audio files by extension, names from Max and POSIX paths", () => {
	assert.ok(isAudioPath("Macintosh HD:/Users/x/Kick 01.WAV"));
	assert.ok(isAudioPath("/tmp/a.aif"));
	assert.ok(isAudioPath("/tmp/b.flac "));
	assert.ok(!isAudioPath("/tmp/set.als"));
	assert.ok(!isAudioPath("/tmp/folder"));
	assert.ok(!isAudioPath("none"));
	assert.equal(fileName("Macintosh HD:/Users/x/Kick 01.wav"), "Kick 01.wav");
	assert.equal(fileName("kick.wav"), "kick.wav");
});

test("frames to read: the whole file up to 10 min (Fit), one row (1:1)", () => {
	assert.equal(fileFrames(1000, 48000), 48000);
	assert.equal(fileFrames(0, 48000), 0);
	assert.equal(framesToRead(FIT, 48000, 48000), 48000);
	assert.equal(framesToRead(FIT, 60 * 60 * 48000, 48000), FIT_MAX_SECONDS * 48000);
	assert.equal(framesToRead(ONE_TO_ONE, 48000, 48000), CELLS);
	assert.equal(framesToRead(ONE_TO_ONE, 300, 44100), CELLS);
	assert.ok(readMs(CELLS, 48000) > (CELLS / 48000) * 1000);
	assert.equal(decimation(8191), 1);
	assert.equal(decimation(16384), 2);
	assert.equal(decimation(48000 * 120), Math.floor((48000 * 120) / 8192));
});

test("block means stream across chunk borders", () => {
	const bm = blockMeans(3);
	bm.push([1, 2]);
	bm.push([3, 4, 5, 6, 7]);
	assert.deepEqual(bm.finish(), [2, 5, 7]);
});

test("toCells: peak-normalised around 0.5, silence flat", () => {
	assert.deepEqual(toCells([0, 0.25, -0.5]), [0.5, 0.75, 0]);
	assert.deepEqual(toCells([0, 0, 0]), [0.5, 0.5, 0.5]);
});

test("1:1 takes the first 1024 frames, one per cell, silence after a short file", () => {
	const x = new Float32Array(5000);
	for (let i = 0; i < x.length; i++) x[i] = ((i % 512) - 256) / 256; // saw, peak 1 (at -1)
	const r = reader(x);
	const row = fitRow(ONE_TO_ONE, x.length, r.read);
	assert.equal(row.length, CELLS);
	assert.deepEqual(r.asked, [[0, CELLS]]);
	for (let i = 0; i < CELLS; i++) assert.ok(Math.abs(row[i] - (0.5 + 0.5 * x[i])) < 1e-6, `cell ${i}`);
	// a 300-frame file: buffer~ zero-fills the rest of the 1024-frame buffer
	const short = new Float32Array(CELLS);
	short.set(sine(300, 3, 0.4));
	const row2 = fitRow(ONE_TO_ONE, CELLS, reader(short).read);
	assert.ok(Math.abs(Math.max(...row2) - 1) < 0.01 || Math.abs(Math.min(...row2)) < 0.01, "normalised");
	for (let i = 300; i < CELLS; i++) assert.equal(row2[i], 0.5);
});

test("Fit, shorter than the row: interpolated, first cell = first frame", () => {
	const x = sine(600, 1);
	const row = fitRow(FIT, x.length, reader(x).read);
	const want = Array.from({ length: CELLS }, (_, i) => 0.5 + 0.5 * Math.sin((2 * Math.PI * i) / CELLS));
	assert.ok(maxErr(row, want) < 0.01, `err ${maxErr(row, want)}`);
});

test("Fit, 4096 frames of 4 cycles -> 4 cycles over the row", () => {
	const x = sine(4096, 4, 0.5);
	const row = fitRow(FIT, x.length, reader(x).read);
	// cell centres: frame (i + 0.5) * 4 - 0.5
	const want = Array.from({ length: CELLS }, (_, i) => 0.5 + 0.5 * Math.sin((2 * Math.PI * 4 * ((i + 0.5) * 4 - 0.5)) / 4096));
	assert.ok(maxErr(row, want, 8, CELLS - 8) < 0.01, `inner err ${maxErr(row, want, 8, CELLS - 8)}`);
	assert.ok(maxErr(row, want) < 0.05, `edge err ${maxErr(row, want)}`);
});

test("Fit, a long file: the slow part survives, content above the row's Nyquist is removed", () => {
	const frames = 48000 * 20; // 20 s: decimation 117, then the sinc stage
	const slow = sine(frames, 10, 0.5);
	const x = new Float32Array(frames);
	for (let i = 0; i < frames; i++) x[i] = slow[i] + 0.5 * Math.sin(2 * Math.PI * 0.013 * i) + 0.3 * Math.sin(2 * Math.PI * 0.21 * i);
	const r = reader(x);
	const row = fitRow(FIT, frames, r.read);
	assert.ok(r.asked.every(([, n]) => n <= CHUNK) && r.asked.length === Math.ceil(frames / CHUNK), "chunked");
	const d = decimation(frames);
	const m = Math.ceil(frames / d);
	const want = Array.from({ length: CELLS }, (_, i) => {
		const t = ((i + 0.5) * (m / CELLS) - 0.5) * d + (d - 1) / 2; // cell centre in source frames
		return Math.sin((2 * Math.PI * 10 * t) / frames);
	});
	// row is normalised by its own peak: compare shapes after scaling the expectation the same way
	const peak = Math.max(...want.map(Math.abs));
	const want01 = want.map((v) => 0.5 + (0.5 * v) / peak);
	assert.ok(maxErr(row, want01, 8, CELLS - 8) < 0.03, `err ${maxErr(row, want01, 8, CELLS - 8)}`);
});

test("resample keeps DC and length", () => {
	assert.deepEqual(resample([], 4), [0, 0, 0, 0]);
	assert.deepEqual(resample([0.3], 3), [0.3, 0.3, 0.3]);
	const flat = resample(new Array(50000).fill(0.25), CELLS);
	assert.equal(flat.length, CELLS);
	assert.ok(flat.every((v) => Math.abs(v - 0.25) < 1e-9));
});

test("summary line", () => {
	assert.equal(dropSummary("a.wav", 96000, 48000, FIT), "a.wav · 2.00 s → FIT · Freeze");
	assert.equal(dropSummary("b.wav", 480, 48000, ONE_TO_ONE), "b.wav · 10 ms → 1:1 · Freeze");
	assert.match(dropSummary("long.wav", 48000 * 900, 48000, FIT), /first 10 min/);
});
