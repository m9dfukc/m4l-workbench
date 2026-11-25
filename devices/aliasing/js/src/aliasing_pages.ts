// aliasing_pages: page logic of both Aliasing faces (D33, D40). Shows one page (hybrid: LFO · Env / Mod
// / Tone / Global; b: LFO 1 ... Global), the Free/Sync variants of the pointer rows and LFOs (R8, R11,
// R12), the write Sym label of the write shape (D6, D34) and, in face b, the eight strip cells of the
// Mod Target (D36); greys out the write controls in Clean (D5), the resonator Freq while Track is on,
// the controls of switched-off sections (D17, D19), Transpose without a Hz pointer and Sync Rate without
// a synced one (D37); on the hybrid's Tone page it grows the display (D31). Colours the panel_* surfaces
// (D22), the matrix row markers mod_mark_<target> and the live.meter~s (D39) from Live's theme.
// Bundled by tools/js-build.mjs into devices/aliasing/aliasing_pages.js. Rules: pages_model.ts
// (scripting names set by scripts/bootstrap_shell.py).
//
// Argument: the face (v8 aliasing_pages.js hybrid | b). Messages in: face <hybrid|b> (also applies) |
//   page n | target n | wmode n | rmode n | l1mode n | l2mode n | wshape n | track n | wactive n |
//   drvon n | bandon n | reson n | limon n | bang (re-apply all) |
//   surface <name> r g b a (Live's device background from live.colors).

import {
	activeFor,
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
	targetRole,
	visibilityFor,
} from "./pages_model.ts";

inlets = 1;
outlets = 0;

const state = initialState(faceOf(typeof jsarguments !== "undefined" ? jsarguments[1] : "hybrid"));
const act = initialActive();

let announced = false;

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
	const want = displayRectFor(state.page, state.face);
	if (!want) return;
	let cur: number[] = [];
	try {
		cur = (obj.getboxattr("presentation_rect") as number[]) || [];
	} catch (e) {
		cur = [];
	}
	const same = cur.length === 4 && want.every((x, i) => Math.abs(Number(cur[i]) - x) < 0.5);
	if (!same) obj.setboxattr("presentation_rect", want[0], want[1], want[2], want[3]);
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
