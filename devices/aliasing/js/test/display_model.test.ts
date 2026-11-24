import assert from "node:assert/strict";
import { test } from "node:test";

import {
	CELLS,
	Gesture,
	HEADER,
	READ_COLOR,
	VOICE_COLORS,
	WRITE_COLOR,
	cellAlpha,
	decimateMinMax,
	headCell,
	hexToRgba,
	normalizeRow,
	parseRgba,
	plotRect,
	posToX,
	sampleColumns,
	sizeEdgeX,
	sizeFromX,
	valueToY,
} from "../src/display_model.ts";

test("accent and voice colours match gui.md", () => {
	assert.deepEqual(WRITE_COLOR.map((c) => Math.round(c * 255)), [0xff, 0x5c, 0x8a, 255]);
	assert.deepEqual(READ_COLOR.map((c) => Math.round(c * 255)), [0x3c, 0xc6, 0xf0, 255]);
	assert.equal(VOICE_COLORS.length, 5);
	assert.deepEqual(VOICE_COLORS[0].slice(0, 3).map((c) => Math.round(c * 255)), [0xf2, 0xf2, 0xf2]);
	assert.deepEqual(VOICE_COLORS[4].slice(0, 3).map((c) => Math.round(c * 255)), [0x66, 0x66, 0x66]);
	assert.throws(() => hexToRgba("#12345"));
});

test("plot geometry: value 1 at the top, 0 at the bottom, positions clamp", () => {
	const p = plotRect(300, 134);
	assert.equal(p.y, HEADER);
	assert.equal(valueToY(1, p), p.y);
	assert.equal(valueToY(0, p), p.y + p.h);
	assert.equal(valueToY(2, p), p.y);
	assert.equal(posToX(0.5, p), 150);
	assert.equal(posToX(-1, p), 0);
});

test("headCell maps 0..1 to 0..1023", () => {
	assert.equal(headCell(0), 0);
	assert.equal(headCell(0.5), 512);
	assert.equal(headCell(1), CELLS - 1);
	assert.equal(headCell(-0.2), 0);
});

test("decimateMinMax keeps the extremes of each column", () => {
	const row = new Array(1024).fill(0.5);
	row[10] = 1;
	row[11] = 0;
	const { min, max } = decimateMinMax(row, 300);
	assert.equal(min.length, 300);
	// column c covers cells floor(c * 1024 / 300) .. floor((c + 1) * 1024 / 300) - 1
	const col = max.findIndex((v) => v === 1);
	assert.ok(Math.floor((col * 1024) / 300) <= 10 && 11 < Math.floor(((col + 1) * 1024) / 300));
	assert.equal(max.filter((v) => v === 1).length, 1);
	assert.equal(min[col], 0);
	assert.equal(max[299], 0.5);
	// more columns than cells: every column still gets a value
	const wide = decimateMinMax([0, 1], 4);
	assert.deepEqual(wide.max, [0, 0, 1, 1]);
});

test("sampleColumns and cellAlpha (2D mode)", () => {
	const ramp = Array.from({ length: 1024 }, (_, i) => i / 1024);
	const cols = sampleColumns(ramp, 100);
	assert.equal(cols.length, 100);
	assert.ok(cols[0] < cols[99]);
	assert.equal(cellAlpha(0), 0.06);
	assert.equal(cellAlpha(1), 1);
	assert.equal(cellAlpha(5), 1);
});

test("Size edge: x <-> size, clamped to 0.001..1", () => {
	assert.equal(sizeEdgeX(0.5, 300), 150);
	assert.equal(sizeEdgeX(0, 300), 0.3);
	assert.equal(sizeFromX(150, 300), 0.5);
	assert.equal(sizeFromX(-10, 300), 0.001);
	assert.equal(sizeFromX(400, 300), 1);
});

test("Gesture: a press on the Size edge drags, no mode toggle", () => {
	const g = new Gesture();
	assert.equal(g.down(148, 60, 0.5, 300), true);
	assert.equal(g.move(90, 60, 300), 0.3);
	assert.equal(g.up(), null);
});

test("Gesture: a click away from the edge toggles the mode", () => {
	const g = new Gesture();
	assert.equal(g.down(40, 60, 0.5, 300), false);
	assert.equal(g.move(41, 61, 300), null);
	assert.equal(g.up(), "toggle");
});

test("Gesture: a drag away from the edge neither drags Size nor toggles", () => {
	const g = new Gesture();
	g.down(40, 60, 0.5, 300);
	assert.equal(g.move(80, 60, 300), null);
	assert.equal(g.up(), null);
	// a release without a press does nothing
	assert.equal(g.up(), null);
});

test("parseRgba and normalizeRow", () => {
	assert.deepEqual(parseRgba([0.1, 0.2, 0.3]), [0.1, 0.2, 0.3, 1]);
	assert.deepEqual(parseRgba([2, -1, 0.5, 0.5]), [1, 0, 0.5, 0.5]);
	assert.equal(parseRgba([0.1, 0.2]), null);
	assert.equal(parseRgba([0.1, NaN, 0.2]), null);
	assert.deepEqual(normalizeRow(null, 3), [0, 0, 0]);
	assert.deepEqual(normalizeRow([0.5, NaN], 3), [0.5, 0, 0]);
	assert.deepEqual(normalizeRow([1, 2, 3, 4], 2), [1, 2]);
});
