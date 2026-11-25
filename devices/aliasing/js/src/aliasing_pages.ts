// aliasing_pages: shows one page (LFO · Env / Mod / Tone / Global) of the Aliasing device, the
// Free/Sync variants of the pointer rows and LFOs (R8, R11, R12) and the write Sym label of the write
// shape (D6); greys out the write controls in Clean (D5), the resonator Freq while Track is on and the
// controls of switched-off sections (D17, D19); on the Tone page it grows the display to the height of
// the table display + the hidden Size slider (D31). Bundled by tools/js-build.mjs into
// devices/aliasing/aliasing_pages.js. Rules: pages_model.ts (scripting names set by
// scripts/bootstrap_shell.py).
//
// Messages in: page n | wmode n | rmode n | l1mode n | l2mode n | wshape n | track n | wactive n |
//              drvon n | bandon n | reson n | limon n | bang (re-apply all) |
//              surface <name> r g b a (Live's device background from live.colors: colours the panel_*
//              objects, D22).

import { activeFor, clampPage, displayRectFor, initialActive, initialState, panelColor, visibilityFor } from "./pages_model.ts";

inlets = 1;
outlets = 0;

const state = initialState();
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
		post(`aliasing_pages: v0.3 ready, ${touched} paged objects\n`);
	}
}

/** The display's box rect for the current page (only touched on change: a rect change repaints). */
function setDisplayRect(obj: Maxobj): void {
	const want = displayRectFor(state.page);
	let cur: number[] = [];
	try {
		cur = (obj.getboxattr("presentation_rect") as number[]) || [];
	} catch (e) {
		cur = [];
	}
	const same = cur.length === 4 && want.every((x, i) => Math.abs(Number(cur[i]) - x) < 0.5);
	if (!same) obj.setboxattr("presentation_rect", want[0], want[1], want[2], want[3]);
}

function page(v: number): void {
	state.page = clampPage(Number(v));
	apply();
}

function wmode(v: number): void {
	state.wmode = Number(v) || 0;
	apply();
}

function rmode(v: number): void {
	state.rmode = Number(v) || 0;
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
	let obj = patcher.firstobject;
	while (obj) {
		const name = String(obj.varname || "");
		if (name.indexOf("panel_") === 0) obj.message("bgfillcolor", c[0], c[1], c[2], c[3]);
		obj = obj.nextobject;
	}
}
