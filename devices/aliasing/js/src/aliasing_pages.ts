// aliasing_pages: shows one page (Mod / Tone / Out) of the paged area of the Aliasing device.
// Bundled by tools/js-build.mjs into devices/aliasing/aliasing_pages.js (never edit that file).
// Paged objects carry a scripting name with a page prefix (mod_, tone_, out_); this sets their
// `hidden` attribute. Spec: devices/aliasing/docs/gui.md section 5. Pure logic: pages_model.ts.
//
// Messages in: an int (0 Mod, 1 Tone, 2 Out) from the Page live.tab; bang re-applies.

import { clampPage, visibilityFor } from "./pages_model.ts";

inlets = 1;
outlets = 0;

let current = 0;

function apply(page: number): void {
	current = clampPage(page);
	let obj = patcher.firstobject;
	while (obj) {
		const vis = visibilityFor(obj.varname, current);
		if (vis !== null && Boolean(obj.hidden) === vis) obj.hidden = !vis; // only touch on change
		obj = obj.nextobject;
	}
}

function msg_int(page: number): void {
	apply(page);
}

function msg_float(page: number): void {
	apply(page);
}

function bang(): void {
	apply(current);
}
