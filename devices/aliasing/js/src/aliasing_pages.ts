// aliasing_pages: shows one page (LFO / Mod / Tone / Out) of the Aliasing device and the Free/Sync
// variants of the pointer rows and LFOs (R8, R11, R12), and greys out the resonator Freq while
// Track is on. Bundled by tools/js-build.mjs into devices/aliasing/aliasing_pages.js.
// Rules: pages_model.ts (scripting-name prefixes set by scripts/bootstrap_shell.py).
//
// Messages in: page n | wmode n | rmode n | l1mode n | l2mode n | track n | bang (re-apply all).

import { activeFor, clampPage, initialState, visibilityFor } from "./pages_model.ts";

inlets = 1;
outlets = 0;

const state = initialState();
let trackValue = 1;

let announced = false;

function apply(): void {
	let obj = patcher.firstobject;
	let touched = 0;
	while (obj) {
		const name = obj.varname;
		const vis = visibilityFor(name, state);
		if (vis !== null && Boolean(obj.hidden) === vis) obj.hidden = !vis; // only touch on change
		if (vis !== null) touched++;
		const act = activeFor(name, trackValue);
		if (act !== null) obj.message("active", act ? 1 : 0);
		obj = obj.nextobject;
	}
	if (!announced) {
		announced = true;
		post(`aliasing_pages: v0.2 ready, ${touched} paged objects\n`);
	}
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

function track(v: number): void {
	trackValue = Number(v) || 0;
	apply();
}

function bang(): void {
	apply();
}
