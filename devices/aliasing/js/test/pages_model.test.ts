import assert from "node:assert/strict";
import { test } from "node:test";

import {
	activeFor,
	clampPage,
	displayRectFor,
	initialActive,
	initialState,
	panelColor,
	symLabelOf,
	visibilityFor,
	type ActiveState,
	type PageState,
} from "../src/pages_model.ts";

const st = (o: Partial<PageState>): PageState => ({ ...initialState(), ...o });

test("paged objects are visible only on their page", () => {
	assert.equal(visibilityFor("lfo_l1shape", st({ page: 0 })), true);
	assert.equal(visibilityFor("lfo_l1shape", st({ page: 1 })), false);
	assert.equal(visibilityFor("mod_m1src", st({ page: 1 })), true);
	assert.equal(visibilityFor("tone_band_center", st({ page: 2 })), true);
	assert.equal(visibilityFor("out_width", st({ page: 3 })), true);
	assert.equal(visibilityFor("out_width", st({ page: 0 })), false);
});

test("the Size bar (tbl_) is hidden on the Tone page only", () => {
	for (const page of [0, 1, 3]) assert.equal(visibilityFor("tbl_size", st({ page })), true);
	assert.equal(visibilityFor("tbl_size", st({ page: 2 })), false);
});

test("pointer rows follow their own Hz|Sync mode on every page", () => {
	for (const page of [0, 1, 2, 3]) {
		assert.equal(visibilityFor("w_free_pitch", st({ page, wmode: 0 })), true);
		assert.equal(visibilityFor("w_sync_note", st({ page, wmode: 0 })), false);
		assert.equal(visibilityFor("w_sync_note", st({ page, wmode: 1 })), true);
		assert.equal(visibilityFor("w_free_pitch", st({ page, wmode: 1 })), false);
	}
	assert.equal(visibilityFor("r_sync_mult", st({ rmode: 1, wmode: 0 })), true);
	assert.equal(visibilityFor("r_free_lbl2", st({ rmode: 1, wmode: 0 })), false);
	assert.equal(visibilityFor("w_fine", st({ wmode: 1 })), true);
	assert.equal(visibilityFor("w_shape", st({})), true);
});

test("LFO rate dials follow their LFO's mode, only on the LFO page", () => {
	assert.equal(visibilityFor("lfo_hz1_rate", st({ page: 0, l1mode: 0 })), true);
	assert.equal(visibilityFor("lfo_sy1_note", st({ page: 0, l1mode: 0 })), false);
	assert.equal(visibilityFor("lfo_sy2_note", st({ page: 0, l2mode: 1 })), true);
	assert.equal(visibilityFor("lfo_hz2_rate", st({ page: 0, l2mode: 1 })), false);
	assert.equal(visibilityFor("lfo_sy2_note", st({ page: 1, l2mode: 1 })), false);
});

test("objects without a rule are left alone", () => {
	for (const n of ["display", "gen", "", undefined, null, "foo_bar", "page", "x_sync_y"]) {
		assert.equal(visibilityFor(n, st({})), null, String(n));
	}
});

test("free/sync only bind in the pointer rows (out_sync stays a page object)", () => {
	assert.equal(visibilityFor("out_sync", st({ page: 3 })), true);
	assert.equal(visibilityFor("out_sync", st({ page: 0 })), false);
	assert.equal(visibilityFor("tbl_sync", st({ page: 2 })), false);
});

test("greying: Track and the resonator switch, section switches, Clean (D5, D17, D19)", () => {
	const a = (o: Partial<ActiveState>): ActiveState => ({ ...initialActive(), ...o });
	assert.equal(activeFor("tone_res_freq", a({ reson: 1, track: 1 })), false);
	assert.equal(activeFor("tone_res_freq", a({ reson: 1, track: 0 })), true);
	assert.equal(activeFor("tone_res_freq", a({ reson: 0, track: 0 })), false, "resonator off");
	assert.equal(activeFor("tone_res_fb", a({ reson: 0 })), false);
	assert.equal(activeFor("tone_res_fb", a({ reson: 1 })), true);
	assert.equal(activeFor("tone_res_on", a({ reson: 0 })), null, "a power switch stays active");
	assert.equal(activeFor("tone_band_center", a({ bandon: 0 })), false);
	assert.equal(activeFor("tone_drive", a({ drvon: 0 })), false);
	assert.equal(activeFor("out_lim_gain", a({ limon: 0 })), false);
	assert.equal(activeFor("out_lim_on", a({ limon: 0 })), null);
	for (const n of ["w_free_pitch", "w_fine", "w_sym", "w_shape", "w_sync_mult", "w_sync_div", "w_sync_note"]) {
		assert.equal(activeFor(n, a({ wactive: 2 })), false, `${n} idle in Clean`);
		assert.equal(activeFor(n, a({ wactive: 1 })), true, `${n} active in Write`);
	}
	assert.equal(activeFor("w_active", a({ wactive: 2 })), null);
	assert.equal(activeFor("out_width", a({})), null);
});

test("the write Sym label follows the shape (D6)", () => {
	const labels = ["curve", "skew", "skew", "skew", "width", "duty", "width", "smooth"];
	labels.forEach((l, k) => assert.equal(symLabelOf(k), l, `shape ${k}`));
	assert.equal(visibilityFor("w_symlbl_duty", st({ wshape: 5 })), true);
	assert.equal(visibilityFor("w_symlbl_skew", st({ wshape: 5 })), false);
	assert.equal(visibilityFor("w_symlbl_curve", st({ wshape: 0, page: 2 })), true, "rows are always visible");
});

test("page numbers are clamped and rounded", () => {
	assert.equal(clampPage(-1), 0);
	assert.equal(clampPage(9), 3);
	assert.equal(clampPage(1.6), 2);
	assert.equal(clampPage(Number.NaN), 0);
});

test("panels: darker on Live's light device background, lighter on the dark one (D22)", () => {
	const light = panelColor(0xa5 / 255, 0xa5 / 255, 0xa5 / 255);
	assert.equal(Math.round(light[0] * 255), 0x98, "#a5a5a5 -> #989898 as in the mock-up");
	const dark = panelColor(0x36 / 255, 0x36 / 255, 0x36 / 255);
	assert.equal(Math.round(dark[0] * 255), 0x42, "#363636 -> about #414141");
	assert.deepEqual(panelColor(Number.NaN, 0, 0), [0, 0, 0, 0.07]);
});

test("the display grows to table + Size height on the Tone page (D31)", () => {
	assert.deepEqual(displayRectFor(2), [308, 6, 328, 157]);
	for (const p of [0, 1, 3]) assert.deepEqual(displayRectFor(p), [308, 6, 328, 136]);
	const [x, y, w, h] = displayRectFor(2);
	assert.ok(y + h <= 165 && x >= 306 && x + w <= 638, "inside the display panel");
});
