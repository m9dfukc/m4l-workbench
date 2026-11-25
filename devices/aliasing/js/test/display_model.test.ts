import assert from "node:assert/strict";
import { test } from "node:test";

import {
	CELLS,
	CURVE_H,
	CURVE_TOP,
	LANE_TOP,
	PAD,
	VOICES,
	W,
	bandEdges,
	decimateMinMax,
	fOfX,
	fbOfY,
	fmtFraction,
	fmtHz,
	fsFraction,
	headCell,
	headX,
	hitCurve,
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
	yOfFb,
	yOfRes,
	type Tone,
} from "../src/display_model.ts";

const curve = { x: PAD, y: CURVE_TOP, w: W - 2 * PAD, h: CURVE_H };
const open: Tone = { center: 632, width: 10, res: 0, slope24: true, reject: false, rsFreq: 140, rsFb: 50, rsMix: 0 };

test("lanes stack under the header and stay above the overview", () => {
	const last = laneRect(VOICES - 1);
	assert.equal(laneRect(0).y, LANE_TOP);
	assert.ok(last.y + last.h <= 140, "lanes end above the overview bar");
	assert.equal(laneRect(0).x, PAD);
});

test("span, heads and the zoom to the active span", () => {
	assert.equal(spanCells(0.1), 102);
	assert.equal(spanCells(1), CELLS);
	assert.equal(spanCells(0), 1);
	const lane = laneRect(0);
	assert.equal(headX(0.05, 0.1, lane), lane.x + lane.w / 2);
	assert.equal(headX(0.5, 0.1, lane), lane.x + lane.w, "heads beyond the span are clamped");
	assert.equal(headCell(0.05, 0.1), 51);
	assert.equal(headCell(0.5, 0.1), 101);
	assert.ok(laneY(1, lane) < laneY(0, lane));
});

test("decimation keeps jagged content of the span only", () => {
	const row = identityRow();
	row[3] = 1;
	const env = decimateMinMax(row, 10, 5);
	assert.equal(env.max[1], 1);
	assert.equal(env.min[0], 0);
	assert.equal(env.max.length, 5);
	assert.deepEqual(sampleColumns([0, 0.5, 1, 1], 4, 2), [0.5, 1]);
});

test("fs fraction hint for the write rate (init state = fs/3 + 4 Hz)", () => {
	const fr = fsFraction(16004, 48000);
	assert.ok(fr);
	assert.deepEqual([fr!.p, fr!.q], [1, 3]);
	assert.ok(Math.abs(fr!.beat - 4) < 1e-9);
	assert.equal(fmtFraction(fr!), "fs/3 +4.0 Hz");
	assert.equal(fmtFraction(fsFraction(18003.1, 48000)!), "3fs/8 +3.1 Hz");
	assert.equal(fsFraction(440, 48000), null, "below fs/16: no hint");
	assert.equal(fsFraction(16500, 48000), null, "drift above 200 Hz: no hint");
	assert.match(tableInfo(102, 16004, 46.2, 48000), /^102 cells .* W 16\.00 kHz = fs\/3 \+4\.0 Hz .* R 46\.2 Hz$/);
	assert.equal(fmtHz(632.4), "632 Hz");
	assert.equal(fmtHz(Number.NaN), "-");
});

test("tone curve: open band is flat, Pass and Reject behave, resonator adds peaks", () => {
	assert.ok(Math.abs(toneDb(632, open)) < 0.5, "open band ~0 dB at the centre");
	const pass: Tone = { ...open, center: 1000, width: 1 };
	assert.ok(toneDb(1000, pass) > -3.5);
	assert.ok(toneDb(100, pass) < -24);
	const rej: Tone = { ...pass, reject: true };
	assert.ok(toneDb(1000, rej) < -10);
	assert.ok(toneDb(100, rej) > -1);
	const comb: Tone = { ...open, rsMix: 100, rsFb: 90, rsFreq: 200 };
	assert.ok(toneDb(200, comb) > toneDb(300, comb) + 6, "comb peak at the resonator frequency");
	const e = bandEdges(pass);
	assert.ok(Math.abs(e.lo - 707.1) < 0.5 && Math.abs(e.hi - 1414.2) < 0.5);
});

test("curve mapping round trips and hit tests", () => {
	assert.ok(Math.abs(fOfX(xOfF(1234, curve), curve) - 1234) < 1e-6);
	assert.ok(Math.abs(resOfY(yOfRes(40, curve), curve) - 40) < 1e-9);
	assert.ok(Math.abs(fbOfY(yOfFb(-30, curve), curve) + 30) < 1e-9);
	const t: Tone = { ...open, center: 1000, width: 2, res: 30 };
	const e = bandEdges(t);
	assert.equal(hitCurve(xOfF(1000, curve), yOfRes(30, curve), t, curve), "body");
	assert.equal(hitCurve(xOfF(e.lo, curve) + 2, 60, t, curve), "edge");
	assert.equal(hitCurve(xOfF(t.rsFreq, curve), yOfFb(t.rsFb, curve), t, curve), "rs");
	assert.equal(hitCurve(xOfF(10000, curve), 60, t, curve), null);
	assert.ok(Math.abs(widthFromEdge(xOfF(2000, curve), 1000, curve) - 2) < 1e-9);
});

test("drawing: lane hit, segments, stored tables", () => {
	const hit = laneHit(PAD + 0.5 * (W - 2 * PAD), LANE_TOP + 24 * 2 + 12);
	assert.ok(hit);
	assert.equal(hit!.voice, 2);
	assert.ok(Math.abs(hit!.xn - 0.5) < 1e-9);
	assert.equal(laneHit(100, 5), null, "header is not a lane");
	const seg = segmentCells(0.9, 1, 0.1, 0, 10);
	assert.equal(seg.start, 1);
	assert.equal(seg.values.length, 9);
	assert.equal(seg.values[0], 0);
	assert.equal(seg.values[8], 1);
	assert.deepEqual(segmentCells(0.5, 0.3, 0.5, 0.3, 10), { start: 5, values: [0.3] });
	const flat = new Array(VOICES * CELLS).fill(0.25);
	const rows = rowsFromStored(flat);
	assert.ok(rows && rows.length === VOICES && rows[4][1023] === 0.25);
	assert.equal(rowsFromStored(flat.slice(1)), null);
	assert.equal(rowsFromStored("x"), null);
	assert.equal(rowsFromStored([...flat.slice(1), Number.NaN]), null);
});

test("header icons and helpers", () => {
	const ic = iconRects();
	assert.ok(inRect(ic.twoD.x + 2, ic.twoD.y + 2, ic.twoD));
	assert.ok(!inRect(ic.line.x - 1, ic.line.y, ic.line));
	assert.ok(ic.twoD.x + ic.twoD.w <= W - PAD);
	assert.deepEqual(normalizeRow([1, Number.NaN], 3), [1, 0, 0]);
	assert.deepEqual(normalizeRow(0.5, 2), [0.5, 0]);
	assert.deepEqual(normalizeRow(null, 2), [0, 0]);
});
