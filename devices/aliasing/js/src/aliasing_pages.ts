// aliasing_pages: page logic of both Aliasing faces (D33, D40). Shows one page (hybrid: LFO · Env / Mod
// / Tone / Global; b: LFO 1 ... Global), the Free/Sync variants of the pointer rows and LFOs (R8, R11,
// R12), the write Sym label of the write shape (D6, D34) and, in face b, the eight strip cells of the
// Mod Target (D36); greys out the write controls in Clean (D5), the resonator Freq while Track is on,
// the controls of switched-off sections (D17, D19), Transpose without a Hz pointer and Sync Rate without
// a synced one (D37); on the hybrid's Tone page it grows the display (D31). Colours the panel_* surfaces
// (D22), the matrix row markers mod_mark_<target> and the live.meter~s (D39) from Live's theme. Face b:
// marks the modulated targets in the Mod Target menu with a dot (D48, from the mx_* values the shell
// copies here) and resets the shown target's eight depths on "clear" (D49).
// Bundled by tools/js-build.mjs into devices/aliasing/aliasing_pages.js. Rules: pages_model.ts
// (scripting names set by scripts/bootstrap_shell.py).
//
// Argument: the face (v8 aliasing_pages.js hybrid | b). Messages in: face <hybrid|b> (also applies) |
//   page n | target n | wmode n | rmode n | l1mode n | l2mode n | wshape n | track n | wactive n |
//   drvon n | bandon n | reson n | limon n | bang (re-apply all) |
//   surface <name> r g b a (Live's device background from live.colors) |
//   mx_<source>_<target> v (face b: a matrix depth) | clearmod (face b: reset the shown target).

import {
	activeFor,
	cellsOf,
	clampPage,
	clampTarget,
	displayRectFor,
	faceOf,
	initialActive,
	initialState,
	markerColor,
	meterColors,
	panelColor,
	surfaceIsDark,
	targetLabels,
	targetRole,
	visibilityFor,
} from "./pages_model.ts";

inlets = 1;
outlets = 0;

const state = initialState(faceOf(typeof jsarguments !== "undefined" ? jsarguments[1] : "hybrid"));
const act = initialActive();

let announced = false;
const depths: { [k: string]: number } = {};
let menuLabels = targetLabels(depths).join("|");

function apply(): void {
	let obj = patcher.firstobject;
	let touched = 0;
	while (obj) {
		const name = obj.varname;
		const vis = visibilityFor(name, state);
		if (vis !== null && Boolean(obj.hidden) === vis) obj.hidden = !vis; // only touch on change
		if (vis !== null) touched++;
		const on = activeFor(name, act);
		if (on !== null) obj.message("active", on ? 1 : 0);
		if (name === "display") setDisplayRect(obj);
		obj = obj.nextobject;
	}
	if (!announced) {
		announced = true;
		post(`aliasing_pages: v0.3b ready, face ${state.face}, ${touched} paged objects\n`);
	}
}

/** The display's box rect for the current page (only touched on change: a rect change repaints). */
function setDisplayRect(obj: Maxobj): void {
	let cur: number[] = [];
	try {
		cur = (obj.getboxattr("presentation_rect") as number[]) || [];
	} catch (e) {
		cur = [];
	}
	const want = displayRectFor(state.page, state.face, cur);
	if (!want) return;
	const same = want.every((x, i) => Math.abs(Number(cur[i]) - x) < 0.5);
	if (!same) obj.setboxattr("presentation_rect", want[0], want[1], want[2], want[3]);
}

function findNamed(name: string): Maxobj | null {
	let obj = patcher.firstobject;
	while (obj) {
		if (obj.varname === name) return obj;
		obj = obj.nextobject;
	}
	return null;
}

/** Face b: the Mod Target menu's items with a dot on every modulated target (D48); only on change. */
function updateMenu(): void {
	const labels = targetLabels(depths);
	const key = labels.join("|");
	if (key === menuLabels) return;
	menuLabels = key;
	const menu = findNamed("mod_target");
	if (!menu) return;
	menu.message("_parameter_range", ...labels);
	let back = "";
	try {
		back = String(menu.getattr("_parameter_range"));
	} catch (e) {
		back = "(not readable)";
	}
	post(`aliasing_pages: mod targets ${labels.filter((l) => l.indexOf("\u2022") >= 0).length} marked; menu reads back: ${back}\n`);
}

function face(v: string): void {
	state.face = faceOf(v);
	state.page = clampPage(state.page, state.face);
	apply();
}

function page(v: number): void {
	state.page = clampPage(Number(v), state.face);
	apply();
}

function target(v: number): void {
	state.target = clampTarget(Number(v));
	apply();
}

function wmode(v: number): void {
	state.wmode = Number(v) || 0;
	act.wmode = state.wmode;
	apply();
}

function rmode(v: number): void {
	state.rmode = Number(v) || 0;
	act.rmode = state.rmode;
	apply();
}

function l1mode(v: number): void {
	state.l1mode = Number(v) || 0;
	apply();
}

function l2mode(v: number): void {
	state.l2mode = Number(v) || 0;
	apply();
}

function wshape(v: number): void {
	state.wshape = Number(v) || 0;
	apply();
}

function track(v: number): void {
	act.track = Number(v) || 0;
	apply();
}

function wactive(v: number): void {
	act.wactive = Number(v) || 0;
	apply();
}

function drvon(v: number): void {
	act.drvon = Number(v) || 0;
	apply();
}

function bandon(v: number): void {
	act.bandon = Number(v) || 0;
	apply();
}

function reson(v: number): void {
	act.reson = Number(v) || 0;
	apply();
}

function limon(v: number): void {
	act.limon = Number(v) || 0;
	apply();
}

function bang(): void {
	apply();
}

/** Face b: a matrix depth mx_<source>_<target> (copied from the shell's prepend to gen~). */
function anything(...args: number[]): void {
	const name = String(messagename);
	if (name.indexOf("mx_") !== 0) return;
	depths[name] = Number(args[0]) || 0;
	if (state.face === "b") updateMenu();
}

/** Face b: the eight depths of the shown target back to 0 (D49); each cell outputs to gen~ and here. */
function clearmod(): void {
	let n = 0;
	for (const name of cellsOf(state.target)) {
		const obj = findNamed(name);
		if (obj) {
			obj.message("float", 0);
			n++;
		}
	}
	post(`aliasing_pages: clear target ${state.target}, ${n} cells\n`);
}

function surface(_name: string, r: number, g: number, b: number, _a: number): void {
	const c = panelColor(Number(r), Number(g), Number(b));
	const dark = surfaceIsDark(Number(r), Number(g), Number(b));
	const m = meterColors(dark);
	let obj = patcher.firstobject;
	while (obj) {
		const name = String(obj.varname || "");
		if (name.indexOf("panel_") === 0) obj.message("bgfillcolor", c[0], c[1], c[2], c[3]);
		else if (name.indexOf("mod_mark_") === 0) {
			const k = markerColor(targetRole(name.substring(9)), dark, c);
			obj.message("bgfillcolor", k[0], k[1], k[2], k[3]);
		} else if (obj.maxclass === "live.meter~") {
			for (const a of ["coldcolor", "warmcolor", "hotcolor"]) obj.message(a, m.fill[0], m.fill[1], m.fill[2], m.fill[3]);
			obj.message("overloadcolor", m.over[0], m.over[1], m.over[2], m.over[3]);
			obj.message("bgcolor", m.bg[0], m.bg[1], m.bg[2], m.bg[3]);
		}
		obj = obj.nextobject;
	}
}
