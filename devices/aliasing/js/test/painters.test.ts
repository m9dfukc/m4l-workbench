// Runs every jspainter bundle (aliasing_paint_*.ts, built here as ES5 like tools/js-build.mjs does)
// in a Node vm with a mock box / mgraphics / max, across values, ranges and both themes.
// Catches runtime errors and calls to mgraphics methods that do not exist (the method list comes
// from the MGraphics class of @types/maxmsp). It does not judge the look: that is the Live test.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

import { build } from "esbuild";

import {
	baselineOf,
	compactValue,
	enumLabelsFrom,
	fitName,
	fitText,
	formatHz,
	formatValue,
	iconPath,
	normOf,
	roleOf,
	sprintf1,
	themeIsDark,
} from "../src/paint_kit.ts";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "src");
const root = join(here, "..", "..", "..", "..");

function mgraphicsMethods(): Set<string> {
	const dts = readFileSync(join(root, "node_modules", "@types", "maxmsp", "index.d.ts"), "utf8");
	const start = dts.indexOf("declare class MGraphics {");
	const end = dts.indexOf("\n}", start);
	const body = dts.slice(start, end);
	return new Set([...body.matchAll(/^\s{4}([a-z_]+)\(/gm)].map((m) => m[1]));
}
const METHODS = mgraphicsMethods();

interface Calls {
	names: string[];
}

function mockMgraphics(w: number, h: number, calls: Calls) {
	const target: Record<string, unknown> = { size: [w, h] };
	return new Proxy(target, {
		get(t, prop: string) {
			if (prop in t) return t[prop];
			if (!METHODS.has(prop)) throw new Error(`mgraphics.${prop} does not exist in MGraphics`);
			return (...args: unknown[]) => {
				for (const a of args) {
					if (typeof a === "number" && !Number.isFinite(a)) throw new Error(`mgraphics.${prop}: non-finite argument`);
				}
				calls.names.push(prop);
				if (prop === "text_measure") return [String(args[0]).length * 5, 10];
				return undefined;
			};
		},
	});
}

function mockBox(attrs: Record<string, unknown>, value: unknown, varname: string) {
	return {
		varname,
		getattr(name: string) {
			return name in attrs ? attrs[name] : null;
		},
		setattr() {},
		getvalueof() {
			return value;
		},
	};
}

const bundles = new Map<string, string>();
async function bundle(entry: string): Promise<string> {
	if (!bundles.has(entry)) {
		const r = await build({
			entryPoints: [join(src, entry)],
			bundle: true,
			format: "cjs",
			platform: "neutral",
			target: "es5",
			treeShaking: false,
			write: false,
			logLevel: "silent",
		});
		bundles.set(entry, r.outputFiles[0].text);
	}
	return bundles.get(entry)!;
}

async function runPainter(
	entry: string,
	size: [number, number],
	attrs: Record<string, unknown>,
	value: unknown,
	varname: string,
	dark: boolean,
	withGetcolor = true,
): Promise<Calls> {
	const code = await bundle(entry);
	const calls: Calls = { names: [] };
	const max = withGetcolor ? { getcolor: () => (dark ? [0.8, 0.8, 0.8, 1] : [0.1, 0.1, 0.1, 1]) } : {};
	const ctx = vm.createContext({
		box: mockBox(attrs, value, varname),
		mgraphics: mockMgraphics(size[0], size[1], calls),
		max,
		post() {},
		error() {},
	});
	vm.runInContext(code, ctx);
	vm.runInContext("paint()", ctx);
	return calls;
}

test("every painter entry exists and paints without errors", async () => {
	const entries = readdirSync(src).filter((f) => f.startsWith("aliasing_paint_") && f.endsWith(".ts"));
	assert.deepEqual(entries.sort(), [
		"aliasing_paint_cell.ts",
		"aliasing_paint_dial.ts",
		"aliasing_paint_menu.ts",
		"aliasing_paint_number.ts",
		"aliasing_paint_slider.ts",
		"aliasing_paint_tab.ts",
		"aliasing_paint_toggle.ts",
	]);
});

test("dial painter: float, Hz with exponent, bipolar, enum, inactive, both themes, no getcolor", async () => {
	const cases: [Record<string, unknown>, unknown, string][] = [
		[{ _parameter_type: 0, _parameter_range: [-1, 1], _parameter_unitstyle: 9, _parameter_units: "%0.3f st" }, 0.217, "w_fine"],
		[{ _parameter_type: 0, _parameter_range: [20, 20000], _parameter_exponent: 4, _parameter_unitstyle: 3 }, 632, "tone_band_center"],
		[{ _parameter_type: 1, _parameter_range: [-64, 130], _parameter_unitstyle: 7 }, [71], "w_free_pitch"],
		[{ _parameter_type: 2, _parameter_range: ["1/4", "1/8", "1/16"] }, 2, "r_sync_note"],
		[{ _parameter_type: 0, _parameter_range: [0, 100], _parameter_unitstyle: 5, active: 0 }, 50, "lfo_l1spread"],
		[{}, "garbage", ""],
	];
	for (const [attrs, value, varname] of cases) {
		for (const dark of [true, false]) {
			const calls = await runPainter("aliasing_paint_dial.ts", [40, 45], attrs, value, varname, dark);
			assert.ok(calls.names.includes("arc"), `arc drawn for ${varname}`);
			assert.ok(calls.names.includes("show_text"), `value text drawn for ${varname}`);
		}
	}
	await runPainter("aliasing_paint_dial.ts", [36, 36], cases[1][0], 632, "tone_band_center", true, false);
});

test("dial painter v0.3b: 48-px box with the name row, overlays skip the name, 36-px box without (D43)", async () => {
	const texts = async (size: [number, number], attrs: Record<string, unknown>, v: unknown, name: string) =>
		(await runPainter("aliasing_paint_dial.ts", size, attrs, v, name, false)).names.filter((n) => n === "show_text").length;
	const env = { _parameter_type: 0, _parameter_range: [0.1, 100], _parameter_unitstyle: 2, _parameter_shortname: "Attack" };
	assert.equal(await texts([34, 48], env, 0.1, "lfo_env_att"), 2, "name and value in the 48-px box");
	assert.equal(await texts([48, 48], env, 0.1, "env_env_att"), 2);
	const sym = { _parameter_type: 0, _parameter_range: [-1, 1], _parameter_shortname: "Sym" };
	assert.equal(await texts([42, 48], sym, 0, "w_sym"), 1, "Sym name comes from the overlay comment (h.2)");
	assert.equal(await texts([42, 48], { ...sym, _parameter_shortname: "Fine" }, 0, "r_fine"), 1);
	assert.equal(await texts([40, 36], env, 0.1, "lfo_env_att"), 1, "36-px box: value only");
});

test("tab painter v0.3b: one row of 5 write-shape icons, 15-px text tabs (D34, D44)", async () => {
	const shapes = { _parameter_type: 2, _parameter_range: ["Ramp", "Tri", "Pulsar", "Spike", "Noise"], num_lines_presentation: 1, multiline: 0 };
	for (const sel of [0, 2, 4]) {
		const calls = await runPainter("aliasing_paint_tab.ts", [120, 15], shapes, sel, "w_shape", sel === 2);
		assert.equal(calls.names.filter((n) => n === "stroke").length, 6, "frame + 5 icons");
		assert.ok(!calls.names.includes("show_text"));
	}
	const pages = { _parameter_type: 2, _parameter_range: ["LFO 1", "LFO 2", "Env", "Band", "Res", "Limit", "Global"] };
	const calls = await runPainter("aliasing_paint_tab.ts", [280, 15], pages, 6, "page", true);
	assert.equal(calls.names.filter((n) => n === "show_text").length, 7);
});

test("tab painter: icon grid, text, end and middle selections, single segment", async () => {
	const shapes = { _parameter_type: 2, _parameter_range: ["Ramp", "Tri", "Tri ±", "Sine", "Pulse", "Pulsar", "Spike", "Noise"], num_lines_presentation: 2 };
	for (const sel of [0, 3, 4, 7, 9, -1]) {
		const calls = await runPainter("aliasing_paint_tab.ts", [108, 32], shapes, sel, "w_shape", sel % 2 === 0);
		assert.ok(calls.names.includes("rectangle_rounded"));
		assert.equal(calls.names.filter((n) => n === "stroke").length, 9, "frame + 8 icons");
	}
	const state = { _parameter_type: 2, _parameter_range: ["Freeze", "Write", "Clean"] };
	for (const sel of [0, 1, 2]) {
		const calls = await runPainter("aliasing_paint_tab.ts", [108, 14], state, sel, "w_active", false);
		assert.equal(calls.names.filter((n) => n === "show_text").length, 3);
	}
	const lfo = { _parameter_type: 2, _parameter_range: ["Sine", "Tri", "Saw", "Square", "S&H", "Random"] };
	await runPainter("aliasing_paint_tab.ts", [102, 16], lfo, 0, "lfo_l1shape", true);
	const words = { _parameter_type: 2, _parameter_range: ["Off", "1", "2", "4", "8"] };
	const calls = await runPainter("aliasing_paint_tab.ts", [118, 16], words, 2, "out_resync", false);
	assert.ok(calls.names.includes("show_text"));
	await runPainter("aliasing_paint_tab.ts", [50, 14], { _parameter_type: 2, _parameter_range: ["Only"] }, 0, "x", true);
	await runPainter("aliasing_paint_tab.ts", [50, 14], {}, 0, "x", true);
});

test("toggle, slider, menu and number painters", async () => {
	for (const v of [0, 1]) {
		await runPainter("aliasing_paint_toggle.ts", [50, 14], { text: "Active", texton: "Active", mode: 1 }, v, "w_active", true);
		await runPainter("aliasing_paint_toggle.ts", [118, 16], { text: "Sync now" }, v, "out_sync", false);
		const pw = await runPainter("aliasing_paint_toggle.ts", [80, 13], { text: "RESONATOR", texton: "RESONATOR", mode: 1 }, v, "tone_res_on", v === 0);
		assert.ok(pw.names.includes("arc") && pw.names.includes("ellipse"), "section switch draws the power symbol (D32)");
		assert.ok(!pw.names.includes("rectangle_rounded"), "no pill frame around a section title");
	}
	for (const [v, name] of [[0, "mod_l1_wp"], [35, "mod_vo_rp"], [-100, "mod_en_ou"], [100, "mod_ro_sz"]] as [number, string][]) {
		const calls = await runPainter("aliasing_paint_cell.ts", [20, 12], { _parameter_type: 0, _parameter_range: [-100, 100], _parameter_unitstyle: 5 }, v, name, v >= 0);
		assert.equal(calls.names.includes("show_text"), v !== 0, `depth text only when not 0 (${name} ${v})`);
	}
	await runPainter("aliasing_paint_cell.ts", [20, 12], {}, "garbage", "", true);
	const cell = { _parameter_type: 0, _parameter_range: [-100, 100], _parameter_unitstyle: 5 };
	for (const [v, dark] of [[0, true], [0, false], [-40, true], [35, false]] as [number, boolean][]) {
		const strip = await runPainter("aliasing_paint_cell.ts", [39, 15], cell, v, "mod_l1_wp", dark);
		assert.equal(strip.names.filter((n) => n === "show_text").length, 1, `the 15-px strip box always shows its depth (${v})`);
		const hyb = await runPainter("aliasing_paint_cell.ts", [28, 12], cell, v, "mod_l1_wp", dark);
		assert.equal(hyb.names.filter((n) => n === "rectangle").length, v === 0 ? 0 : 2, "quiet slot, or hairline + bar");
	}
	for (const v of [0, 1]) {
		const pw = await runPainter("aliasing_paint_toggle.ts", [66, 15], { text: "Resonator", texton: "Resonator", mode: 1 }, v, "res_res_on", v === 1);
		assert.ok(pw.names.includes("ellipse"), "15-px power switch (D43)");
	}
	await runPainter("aliasing_paint_menu.ts", [86, 15], { _parameter_type: 2, _parameter_range: ["Write Pitch", "Write Sym", "Write Gate"] }, 1, "mod_target", false);
	await runPainter("aliasing_paint_slider.ts", [328, 18], { _parameter_type: 0, _parameter_range: [0.1, 100], _parameter_exponent: 2, _parameter_unitstyle: 5, _parameter_shortname: "Size" }, 10, "tbl_size", true);
	await runPainter("aliasing_paint_slider.ts", [100, 14], { _parameter_type: 0, _parameter_range: [-100, 100], _parameter_unitstyle: 5 }, -35, "mod_m1depth", true);
	await runPainter("aliasing_paint_slider.ts", [100, 14], { _parameter_type: 0, _parameter_range: [-100, 100], _parameter_unitstyle: 5 }, 0, "mod_m1depth", false);
	const src = { _parameter_type: 2, _parameter_range: ["None", "LFO 1", "LFO 2", "Drift", "Velocity", "Mod Wheel"] };
	for (const v of [0, 3, 9]) await runPainter("aliasing_paint_menu.ts", [80, 18], src, v, "mod_m1src", true);
	await runPainter("aliasing_paint_number.ts", [30, 14], { _parameter_type: 1, _parameter_range: [1, 64], _parameter_unitstyle: 9, _parameter_units: "×%d" }, 16, "w_sync_mult", true);
});

test("paint_kit: value formatting", () => {
	assert.equal(sprintf1("%0.3f st", 0.217), "0.217 st");
	assert.equal(sprintf1("×%d", 16), "×16");
	assert.equal(sprintf1("%0.0f %%", 50), "50 %");
	assert.equal(sprintf1("%0.1f oct", 10), "10.0 oct");
	assert.equal(formatHz(632.4), "632 Hz");
	assert.equal(formatHz(2110), "2.11 kHz");
	assert.equal(formatHz(20000), "20.0 kHz");
	assert.equal(formatHz(0.15), "0.15 Hz");
	assert.equal(formatValue(71, 7, "", null), "+71 st");
	assert.equal(formatValue(-6, 4, "", null), "-6.0 dB");
	assert.equal(formatValue(25, 5, "", null), "25 %");
	assert.equal(formatValue(2, 0, "", ["a", "b", "c"]), "c");
	assert.equal(formatValue(9, 0, "", ["a", "b", "c"]), "c");
	assert.equal(formatValue(NaN, 1, "", null), "");
});

test("paint_kit: ranges, roles, theme, icons, fitting", () => {
	assert.equal(normOf(632, 20, 20000, 4).toFixed(3), Math.pow(612 / 19980, 0.25).toFixed(3));
	assert.equal(normOf(5, 0, 1, 1), 1);
	assert.equal(normOf(0, 0, 0, 1), 0);
	assert.equal(roleOf("w_free_pitch"), "write");
	assert.equal(roleOf("tone_band_res"), "write");
	assert.equal(roleOf("r_spread"), "read");
	assert.equal(roleOf("tone_res_mix"), "read");
	assert.equal(roleOf("lfo_l1phase"), "neutral");
	assert.equal(themeIsDark(() => [0.85, 0.85, 0.85, 1]), true);
	assert.equal(themeIsDark(() => [0.1, 0.1, 0.1, 1]), false);
	assert.equal(themeIsDark(null), true);
	assert.equal(themeIsDark(() => {
		throw new Error("no colour");
	}), true);
	assert.deepEqual(enumLabelsFrom(["a", "b"], 2), ["a", "b"]);
	assert.equal(enumLabelsFrom([0, 1], 0), null);
	for (const l of ["Ramp", "Tri", "Tri ±", "Sine", "Saw", "Square", "S&H", "Random"]) {
		const pts = iconPath(l);
		assert.ok(pts && pts.length >= 3, l);
		for (const [x, y] of pts!) assert.ok(x >= 0 && x <= 22 && y >= 0 && y <= 12, `${l} inside 22x12`);
	}
	for (const l of ["Ramp", "Tri", "Tri ±", "Sine", "Pulse", "Pulsar", "Spike", "Noise"]) {
		const pts = iconPath(l, "write");
		assert.ok(pts && pts.length >= 3, `write ${l}`);
		for (const [x, y] of pts!) assert.ok(x >= 0 && x <= 22 && y >= 0 && y <= 12, `write ${l} inside 22x12`);
	}
	assert.notDeepEqual(iconPath("Sine", "write"), iconPath("Sine"), "the write Sine is a position hump, not the LFO sine");
	assert.equal(roleOf("mod_l1_wp"), "write");
	assert.equal(roleOf("mod_vo_sp"), "read");
	assert.equal(roleOf("mod_en_bc"), "neutral");
	assert.equal(roleOf("band_band_center"), "write", "face b: band page");
	assert.equal(roleOf("res_res_fb"), "read", "face b: res page");
	assert.equal(roleOf("lim_lim_gain"), "neutral");
	assert.equal(roleOf("row_size"), "neutral");
	assert.equal(iconPath("Off"), null);
	const m = (s: string) => s.length * 5;
	assert.equal(fitText("Velocity", 100, m), "Velocity");
	assert.ok(m(fitText("Mod Wheel long text", 40, m)) <= 40);
});

test("paint_kit v0.3b: baselines, compact values, short names (face review §1.3, D43)", () => {
	assert.equal(baselineOf(15), 11);
	assert.equal(baselineOf(14), 11);
	assert.equal(baselineOf(13), 10);
	assert.equal(baselineOf(12), 10);
	const m = (s: string) => s.length * 5;
	assert.equal(compactValue("0.10 ms", 40, m), "0.10 ms", "fits as is");
	assert.equal(compactValue("0.10 ms", 30, m), "0.10ms", "gap before the unit goes first");
	assert.equal(compactValue("0.10 ms", 25, m), "0.1ms", "then trailing zeros");
	assert.equal(compactValue("2.00 kHz", 25, m), "2kHz");
	assert.equal(compactValue("-0.3 dB", 30, m), "-0.3dB");
	assert.equal(compactValue("1.05 ms", 30, m), "1.05ms", "inner zeros stay");
	assert.ok(m(compactValue("12345.678 Hz", 20, m)) <= 20);
	assert.equal(fitName("Release", 35, m), "Release");
	assert.equal(fitName("Release", 30, m), "Rel");
	assert.equal(fitName("Attack", 15, m), "Att");
});
