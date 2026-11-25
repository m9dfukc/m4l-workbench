import assert from "node:assert/strict";
import { test } from "node:test";

import { activeFor, clampPage, initialState, visibilityFor, type PageState } from "../src/pages_model.ts";

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

test("Track greys out the resonator Freq only", () => {
	assert.equal(activeFor("tone_res_freq", 1), false);
	assert.equal(activeFor("tone_res_freq", 0), true);
	assert.equal(activeFor("tone_res_fb", 1), null);
});

test("page numbers are clamped and rounded", () => {
	assert.equal(clampPage(-1), 0);
	assert.equal(clampPage(9), 3);
	assert.equal(clampPage(1.6), 2);
	assert.equal(clampPage(Number.NaN), 0);
});
