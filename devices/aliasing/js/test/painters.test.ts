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
	enumLabelsFrom,
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

test("tab painter: icons, text, end and middle selections, single segment", async () => {
	const shapes = { _parameter_type: 2, _parameter_range: ["Ramp", "Tri", "Tri ±", "=Read"] };
	for (const sel of [0, 1, 2, 3, 7, -1]) {
		const calls = await runPainter("aliasing_paint_tab.ts", [104, 18], shapes, sel, "w_shape", true);
		assert.ok(calls.names.includes("rectangle_rounded"));
	}
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
	}
	await runPainter("aliasing_paint_slider.ts", [320, 11], { _parameter_type: 0, _parameter_range: [0.1, 100], _parameter_exponent: 2, _parameter_unitstyle: 5, _parameter_shortname: "Size" }, 10, "tbl_size", true);
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
	for (const l of ["Ramp", "Tri", "Tri ±", "=Read", "Sine", "Saw", "Square", "S&H", "Random"]) {
		const pts = iconPath(l);
		assert.ok(pts && pts.length >= 3, l);
		for (const [x, y] of pts!) assert.ok(x >= 0 && x <= 22 && y >= 0 && y <= 12, `${l} inside 22x12`);
	}
	assert.equal(iconPath("Off"), null);
	const m = (s: string) => s.length * 5;
	assert.equal(fitText("Velocity", 100, m), "Velocity");
	assert.ok(m(fitText("Mod Wheel long text", 40, m)) <= 40);
});
