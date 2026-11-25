import assert from "node:assert/strict";
import { test } from "node:test";

import {
	activeFor,
	clampPage,
	displayRectFor,
	initialActive,
	initialState,
	isTonePage,
	markerColor,
	meterColors,
	panelColor,
	surfaceIsDark,
	symLabelOf,
	TARGETS,
	cellsOf,
	targetLabels,
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

test("the write Sym label follows the shape (D6, D34: Ramp, Tri, Pulsar, Spike, Noise)", () => {
	const labels = ["curve", "skew", "duty", "width", "smooth"];
	labels.forEach((l, k) => assert.equal(symLabelOf(k), l, `shape ${k}`));
	assert.equal(visibilityFor("w_symlbl_duty", st({ wshape: 2 })), true);
	assert.equal(visibilityFor("w_symlbl_skew", st({ wshape: 2 })), false);
	assert.equal(visibilityFor("w_symlbl_curve", st({ wshape: 0, page: 2 })), true, "rows are always visible");
	assert.equal(visibilityFor("w_free_lblfine", st({ wmode: 0 })), true, "Fine / Detune overlays follow the mode");
	assert.equal(visibilityFor("w_sync_lbldetune", st({ wmode: 0 })), false);
});

test("Transpose greys out without a Hz pointer, Sync Rate without a synced one (D37)", () => {
	const a = (o: Partial<ActiveState>): ActiveState => ({ ...initialActive(), ...o });
	for (const n of ["out_transpose"]) {
		assert.equal(activeFor(n, a({ wmode: 0, rmode: 0 })), true);
		assert.equal(activeFor(n, a({ wmode: 1, rmode: 0 })), true, "read still in Hz");
		assert.equal(activeFor(n, a({ wmode: 1, rmode: 1 })), false, "both synced");
	}
	assert.equal(activeFor("out_syncrate", a({ wmode: 0, rmode: 0 })), false, "both in Hz");
	assert.equal(activeFor("out_syncrate", a({ wmode: 0, rmode: 1 })), true);
});

test("face b: seven side pages, the strip shows the cells of one target (D33, D36)", () => {
	const b = (o: Partial<PageState>): PageState => ({ ...initialState("b"), ...o });
	assert.equal(visibilityFor("lfo1_l1shape", b({ page: 0 })), true);
	assert.equal(visibilityFor("lfo1_l1shape", b({ page: 1 })), false);
	assert.equal(visibilityFor("lfo2_hz2_rate", b({ page: 1, l2mode: 0 })), true);
	assert.equal(visibilityFor("lfo2_sy2_note", b({ page: 1, l2mode: 0 })), false);
	assert.equal(visibilityFor("band_band_center", b({ page: 3 })), true);
	assert.equal(visibilityFor("res_res_freq", b({ page: 4 })), true);
	assert.equal(visibilityFor("lim_lim_gain", b({ page: 5 })), true);
	assert.equal(visibilityFor("out_syncrate", b({ page: 6 })), true);
	assert.equal(visibilityFor("out_syncrate", b({ page: 0 })), false);
	assert.equal(clampPage(9, "b"), 6);
	TARGETS.forEach((t, k) => {
		assert.equal(visibilityFor(`mod_l1_${t}`, b({ target: k, page: 3 })), true, `target ${t} on any page`);
		assert.equal(visibilityFor(`mod_ro_${t}`, b({ target: (k + 1) % 9 })), false);
	});
	for (const n of ["strip_lbl_l1", "row_size", "row_meterl", "mod_target"]) assert.equal(visibilityFor(n, b({})), null, n);
	assert.ok(isTonePage(3, "b") && isTonePage(4, "b") && !isTonePage(2, "b"), "Band and Res show the tone curve");
	assert.equal(displayRectFor(3, "b", [6, 6, 496, 85]), null, "face b keeps its display rect (no D31)");
	assert.equal(visibilityFor("strip_clear", b({})), null, "Clear is always visible");
	const a = initialActive();
	assert.equal(activeFor("band_band_center", { ...a, bandon: 0 }), false, "same greying rules as the hybrid");
	assert.equal(activeFor("band_drive", { ...a, drvon: 0 }), false);
	assert.equal(activeFor("res_res_freq", { ...a, reson: 1, track: 1 }), false);
	assert.equal(activeFor("lim_lim_ceil", { ...a, limon: 0 }), false);
	assert.equal(activeFor("mod_l1_bc", a), null, "matrix cells are never greyed");
});

test("theme colours: markers by row role, graphite meters (D39)", () => {
	const panel = panelColor(0xa5 / 255, 0xa5 / 255, 0xa5 / 255);
	assert.equal(surfaceIsDark(0xa5 / 255, 0xa5 / 255, 0xa5 / 255), false);
	assert.equal(surfaceIsDark(0x36 / 255, 0x36 / 255, 0x36 / 255), true);
	assert.equal(Math.round(markerColor("read", false, panel)[2] * 255), 0x73, "light read blue #2f5873");
	assert.equal(Math.round(markerColor("write", true, panel)[0] * 255), 0xe4, "dark write graphite #e4e4e4");
	const n = markerColor("neutral", false, panel);
	assert.ok(n[0] < panel[0] && n[0] > 0x26 / 255, "neutral marker between panel and label grey");
	assert.equal(Math.round(meterColors(false).fill[0] * 255), 0x3c);
	assert.equal(Math.round(meterColors(true).bg[0] * 255), 0x26);
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

test("the display grows to table + Size height on the Tone page, keeping its x, y, width (D31, D47)", () => {
	const cur = [258, 6, 328, 136];
	assert.deepEqual(displayRectFor(2, "hybrid", cur), [258, 6, 328, 157]);
	for (const p of [0, 1, 3]) assert.deepEqual(displayRectFor(p, "hybrid", [258, 6, 328, 157]), [258, 6, 328, 136]);
	assert.equal(displayRectFor(2, "hybrid", []), null, "no rect read: leave the box alone");
	assert.equal(displayRectFor(3, "b", [6, 6, 496, 85]), null);
});

test("face b: modulated targets get a dot in the Mod Target menu, Clear knows its eight cells (D48, D49)", () => {
	assert.deepEqual(targetLabels({}), ["Write Pitch", "Write Sym", "Write Gate", "Read Pitch", "Read Spread", "Size",
		"Band Center", "Res Freq", "Output"]);
	const l = targetLabels({ mx_l1_sz: 50, mx_ro_ou: -3, mx_vo_wp: 0, mx_en_bc: 0.2 });
	assert.equal(l[5], "Size \u2022");
	assert.equal(l[8], "Output \u2022");
	assert.equal(l[0], "Write Pitch", "a depth of 0 is no modulation");
	assert.equal(l[6], "Band Center", "below half a percent counts as 0 (the cells step in 0.1 %)");
	assert.deepEqual(cellsOf(5), ["mod_l1_sz", "mod_l2_sz", "mod_en_sz", "mod_ve_sz", "mod_mw_sz", "mod_vo_sz", "mod_nb_sz", "mod_ro_sz"]);
	assert.equal(cellsOf(99)[0], "mod_l1_ou", "clamped to the last target");
});
