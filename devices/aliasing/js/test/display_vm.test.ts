// Runs the aliasing_display bundle (built here like tools/js-build.mjs does) in a Node vm with mock
// Max globals: mgraphics (methods checked against @types/maxmsp), Buffer, Dict, Task, outlet.
// Exercises paint() on every page and mode, the mouse gestures and the table store/restore path.
// It cannot judge the look or Max's real API behaviour: that is the Live test.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

import { build } from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..", "..", "..");

const dts = readFileSync(join(root, "node_modules", "@types", "maxmsp", "index.d.ts"), "utf8");
const mgStart = dts.indexOf("declare class MGraphics {");
const METHODS = new Set([...dts.slice(mgStart, dts.indexOf("\n}", mgStart)).matchAll(/^\s{4}([a-z_]+)\(/gm)].map((m) => m[1]));

async function load() {
	const r = await build({
		entryPoints: [join(here, "..", "src", "aliasing_display.ts")],
		bundle: true,
		format: "cjs",
		platform: "neutral",
		target: "es2020",
		treeShaking: false,
		write: false,
		logLevel: "silent",
	});
	const code = r.outputFiles[0].text.replace(/^"use strict";\n/m, "");
	const buffers = new Map<string, { frames: number; ch: number; data: Float32Array }>();
	const mkbuf = (name: string, frames: number, ch: number) => buffers.set(name, { frames, ch, data: new Float32Array(frames * ch) });
	mkbuf("atab", 1024, 5);
	mkbuf("aheads", 5, 10);
	const dicts = new Map<string, unknown>();
	let dictN = 0;
	const outs: unknown[][] = [];
	const calls: string[] = [];
	const mg = new Proxy({ size: [328, 157] } as Record<string, unknown>, {
		get(t, prop: string) {
			if (prop in t) return t[prop];
			if (!METHODS.has(prop)) throw new Error(`mgraphics.${prop} does not exist`);
			return (...args: unknown[]) => {
				for (const a of args) if (typeof a === "number" && !Number.isFinite(a)) throw new Error(`mgraphics.${prop}: non-finite argument`);
				calls.push(prop);
				return prop === "text_measure" ? [String(args[0]).length * 4.5, 9] : undefined;
			};
		},
		set(t, prop: string, v) {
			t[prop] = v;
			return true;
		},
	});
	class Buffer {
		b: { frames: number; ch: number; data: Float32Array };
		constructor(name: string) {
			const b = buffers.get(name);
			if (!b) throw new Error(`no buffer ${name}`);
			this.b = b;
		}
		peek(ch: number, frame: number, count: number) {
			const out: number[] = [];
			for (let i = 0; i < count; i++) out.push(this.b.data[(frame + i) * this.b.ch + (ch - 1)]);
			return count === 1 ? out[0] : out;
		}
		poke(ch: number, frame: number, values: number | number[]) {
			const vs = Array.isArray(values) ? values : [values];
			if (ch < 1 || ch > this.b.ch) throw new Error(`poke channel ${ch} out of range`);
			vs.forEach((v, i) => {
				if (frame + i >= this.b.frames) throw new Error("poke beyond the buffer");
				this.b.data[(frame + i) * this.b.ch + (ch - 1)] = v;
			});
		}
	}
	class Dict {
		name: string;
		constructor(name?: string) {
			this.name = name ?? `u${++dictN}`;
			if (!dicts.has(this.name)) dicts.set(this.name, {});
		}
		parse(s: string) {
			dicts.set(this.name, JSON.parse(s));
		}
		get(k: string) {
			return (dicts.get(this.name) as Record<string, unknown>)[k];
		}
	}
	class Task {
		running = false;
		interval = 0;
		fn: () => void;
		constructor(fn: () => void) {
			this.fn = fn;
		}
		repeat() {
			this.running = true;
		}
		cancel() {
			this.running = false;
		}
	}
	const ctx = vm.createContext({
		mgraphics: mg,
		Buffer,
		Dict,
		Task,
		max: { getcolor: () => [0.8, 0.8, 0.8, 1] },
		outlet: (...a: unknown[]) => outs.push(a),
		post() {},
		error() {},
	});
	vm.runInContext(code, ctx);
	const call = (fn: string, ...args: unknown[]) => (ctx[fn] as (...a: unknown[]) => unknown)(...args);
	return { call, buffers, dicts, outs, calls, ctx };
}

test("paints every page and mode, before and after the buffers arrive", async () => {
	const d = await load();
	d.call("paint");
	d.call("buffers", "atab", "aheads");
	const heads = d.buffers.get("aheads")!;
	for (let v = 0; v < 5; v++) {
		heads.data[v * 10 + 0] = 0.05; // write head
		heads.data[v * 10 + 1] = 0.02; // read head
		heads.data[v * 10 + 2] = 1;
		heads.data[v * 10 + 3] = 0.1; // size
		heads.data[v * 10 + 4] = 16004;
		heads.data[v * 10 + 5] = 46;
		heads.data[v * 10 + 6] = 632 * (1 + 0.1 * v);
		heads.data[v * 10 + 7] = 10;
		heads.data[v * 10 + 8] = 46;
	}
	heads.data[0 * 10 + 9] = 48000;
	for (const page of [0, 1, 2, 3]) {
		d.call("page", page);
		for (const mode of [0, 1]) {
			d.call("mode", mode);
			d.call("tick");
			d.call("paint");
		}
	}
	for (const [k, v] of [["bmode", 1], ["bslope", 0], ["rsmix", 80], ["rstrack", 0], ["bres", 100], ["bwidth", 0.2]] as [string, number][]) {
		d.call("pv", k, v);
		d.call("page", 2);
		d.call("paint");
	}
	assert.ok(d.calls.includes("show_text"));
});

test("drawing writes the lane and stores the table; double-click resets it", async () => {
	const d = await load();
	d.call("buffers", "atab", "aheads");
	const tab = d.buffers.get("atab")!;
	const heads = d.buffers.get("aheads")!;
	for (let v = 0; v < 5; v++) heads.data[v * 10 + 3] = 1; // size 1: the lane shows all cells
	d.call("tick");
	d.call("page", 0);
	// press in lane 1 at the left, near the top; drag to the right, near the bottom; release
	d.call("onclick", 10, 17 + 24 + 3, 1, 0, 0, 0, 0, 0);
	d.call("ondrag", 300, 17 + 24 + 20, 1, 0, 0, 0, 0, 0);
	d.call("ondrag", 300, 17 + 24 + 20, 0, 0, 0, 0, 0, 0);
	const cell = (v: number, i: number) => tab.data[i * 5 + v];
	assert.ok(cell(1, 20) > 0.8, `drawn high at the start (${cell(1, 20)})`);
	assert.ok(cell(1, 900) < 0.3, `drawn low at the end (${cell(1, 900)})`);
	assert.equal(cell(0, 20), 0, "other lanes untouched");
	const store = d.outs.find((o) => o[0] === 1 && o[1] === "dictionary");
	assert.ok(store, "table stored after the gesture");
	const stored = d.dicts.get(String(store![2])) as { table: number[] };
	assert.equal(stored.table.length, 5120);
	// double-click resets lane 1 to the identity ramp
	d.call("ondblclick", 100, 17 + 24 + 10, 1, 0, 0, 0, 0, 0);
	assert.ok(Math.abs(cell(1, 512) - 0.5) < 1e-6);
	// Shift + Alt: a straight line in all lanes
	d.call("onclick", 4, 17 + 3, 1, 0, 1, 0, 1, 0);
	d.call("ondrag", 324, 17 + 3, 1, 0, 1, 0, 1, 0);
	d.call("ondrag", 324, 17 + 3, 0, 0, 1, 0, 1, 0);
	for (let v = 0; v < 5; v++) assert.ok(cell(v, 700) > 0.9, `voice ${v} drawn by the Shift gesture`);
});

test("a recalled table is written into the buffer and flagged for gen~", async () => {
	const d = await load();
	const flat = new Array(5120).fill(0).map((_, i) => (i % 1024) / 2048);
	d.dicts.set("recalled", { table: flat });
	d.call("dictionary", "recalled"); // before the buffers: held back
	d.call("buffers", "atab", "aheads");
	const tab = d.buffers.get("atab")!;
	const heads = d.buffers.get("aheads")!;
	assert.ok(Math.abs(tab.data[1000 * 5 + 3] - 1000 / 2048) < 1e-6);
	assert.equal(heads.data[1 * 10 + 9], 1, "table-valid flag in aheads ch 9 sample 1");
	d.dicts.set("broken", { table: [1, 2, 3] });
	d.call("dictionary", "broken"); // ignored
	assert.ok(Math.abs(tab.data[1000 * 5 + 3] - 1000 / 2048) < 1e-6);
});

test("the stored table is read by name at init when the dict did not output", async () => {
	const d = await load();
	d.dicts.set("---atable", { table: new Array(5120).fill(0.75) });
	d.call("buffers", "atab", "aheads", "---atable");
	assert.ok(Math.abs(d.buffers.get("atab")!.data[700 * 5 + 2] - 0.75) < 1e-6);
	const e = await load();
	e.call("buffers", "atab", "aheads", "missing-dict");
	assert.equal(e.buffers.get("atab")!.data[700 * 5 + 2], 0, "an empty dict leaves the buffer alone");
});

test("tone page gestures send parameter values", async () => {
	const d = await load();
	d.call("buffers", "atab", "aheads");
	d.call("page", 2);
	for (const [k, v] of [["center", 1000], ["bwidth", 2], ["bres", 30], ["rsfreq", 140], ["rsfb", 50], ["rsmix", 0], ["rstrack", 0]] as [string, number][]) d.call("pv", k, v);
	const rect = { x: 4, y: 17, w: 320, h: 125 };
	const xOf = (f: number) => rect.x + (Math.log(f / 20) / Math.log(1000)) * rect.w;
	// drag the band body to the right
	d.outs.length = 0;
	d.call("onclick", xOf(1000), 80, 1, 0, 0, 0, 0, 0);
	d.call("ondrag", xOf(1000) + 20, 60, 1, 0, 0, 0, 0, 0);
	const center = d.outs.find((o) => o[0] === 0 && o[1] === "center");
	assert.ok(center && (center[2] as number) > 1000);
	assert.ok(d.outs.find((o) => o[0] === 0 && o[1] === "bres"));
	d.call("ondrag", 0, 0, 0, 0, 0, 0, 0, 0);
	// the R handle switches Track off and opens Mix
	d.outs.length = 0;
	const yFb = rect.y + 8 + (1 - (50 + 95) / 190) * (rect.h - 16);
	d.call("pv", "rstrack", 1);
	d.call("onclick", xOf(140), yFb, 1, 0, 0, 0, 0, 0);
	d.call("ondrag", xOf(300), yFb, 1, 0, 0, 0, 0, 0);
	assert.ok(d.outs.find((o) => o[1] === "rstrack" && o[2] === 0));
	assert.ok(d.outs.find((o) => o[1] === "rsmix" && o[2] === 50));
	// double-click in the band toggles Pass/Reject
	d.outs.length = 0;
	d.call("ondblclick", xOf(1000), 80, 1, 0, 0, 0, 0, 0);
	assert.deepEqual(d.outs[0], [0, "bmode", 1]);
	// Line / 2D icons on a table page
	d.call("page", 0);
	d.outs.length = 0;
	d.call("onclick", 328 - 4 - 14 + 5, 6, 1, 0, 0, 0, 0, 0);
	assert.deepEqual(d.outs[0], [0, "mode", 1]);
});

test("line view at Size 100 % with a jagged table stays cheap (D8, t3 slowdown)", async () => {
	const d = await load();
	(d.ctx.mgraphics as { size: number[] }).size = [328, 136];
	d.call("buffers", "atab", "aheads");
	const tab = d.buffers.get("atab")!;
	const heads = d.buffers.get("aheads")!;
	let seed = 1;
	for (let i = 0; i < tab.data.length; i++) {
		seed = (seed * 16807) % 2147483647;
		tab.data[i] = seed / 2147483647; // worst case: every pixel column spans most of the lane
	}
	for (let v = 0; v < 5; v++) heads.data[v * 10 + 3] = 1;
	d.call("pv", "size", 100);
	d.call("page", 0);
	d.call("mode", 0);
	d.call("tick");
	d.calls.length = 0;
	d.call("paint");
	const n = d.calls.length;
	const strokes = d.calls.filter((c) => c === "stroke").length;
	// v0.2 stroked each lane's zigzag twice (4-px glow with round joins + line): about 6400 path calls
	// and 10 wide strokes per frame here. v0.3 fills one band per lane.
	assert.ok(n < 4000, `mgraphics calls per frame at Size 100 % (${n})`);
	assert.ok(d.calls.filter((c) => c === "set_line_join").length === 0, "no round-join strokes of the band");
	assert.ok(strokes <= 3 * 5 + 2, `only the short head lines and rings are stroked (${strokes})`);
	console.log(`  mgraphics calls per frame at Size 100 %: ${n}, strokes ${strokes}`);
});
