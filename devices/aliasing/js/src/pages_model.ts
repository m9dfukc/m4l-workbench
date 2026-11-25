// Pure page logic for aliasing_pages (v8): which objects are visible for a page / mode state.
// Scripting names (set by scripts/bootstrap_shell.py) carry the rule:
//   <area>_<rest>       area lfo | mod | tone | out = page 0..3; tbl = hidden on the Tone page (R11);
//                       w | r = the always visible pointer rows
//   <area>_<cond>_...   cond free | sync (the row's Hz|Sync mode, w -> wmode, r -> rmode; ignored
//                       outside the pointer rows),
//                       hz1 | sy1 (LFO 1 mode), hz2 | sy2 (LFO 2 mode)
// Names that match none of these are left alone (null).

export const PAGES = ["lfo", "mod", "tone", "out"] as const;
export const PAGE_TONE = 2;

export interface PageState {
	page: number;
	wmode: number;
	rmode: number;
	l1mode: number;
	l2mode: number;
}

export function initialState(): PageState {
	return { page: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1 };
}

export function clampPage(page: number): number {
	if (!Number.isFinite(page)) return 0;
	return Math.min(PAGES.length - 1, Math.max(0, Math.round(page)));
}

function condOk(area: string, cond: string, s: PageState): boolean | null {
	const sync = (m: number): boolean => m > 0.5;
	switch (cond) {
		case "free":
			return area === "w" ? !sync(s.wmode) : area === "r" ? !sync(s.rmode) : true;
		case "sync":
			return area === "w" ? sync(s.wmode) : area === "r" ? sync(s.rmode) : true;
		case "hz1":
			return !sync(s.l1mode);
		case "sy1":
			return sync(s.l1mode);
		case "hz2":
			return !sync(s.l2mode);
		case "sy2":
			return sync(s.l2mode);
		default:
			return true;
	}
}

/** Visibility of the object named `varname`: true / false, or null for objects not handled here. */
export function visibilityFor(varname: string | null | undefined, s: PageState): boolean | null {
	if (!varname) return null;
	const parts = String(varname).split("_");
	if (parts.length < 2) return null;
	const area = parts[0];
	const p = clampPage(s.page);
	let areaOk: boolean;
	const pageIndex = (PAGES as readonly string[]).indexOf(area);
	if (pageIndex >= 0) areaOk = pageIndex === p;
	else if (area === "tbl") areaOk = p !== PAGE_TONE;
	else if (area === "w" || area === "r") areaOk = true;
	else return null;
	const c = condOk(area, parts[1], s);
	if (c === null) return null;
	return areaOk && c;
}

/** `active` state of objects that depend on a toggle: the resonator's Freq dial is off while Track is on. */
export function activeFor(varname: string | null | undefined, track: number): boolean | null {
	if (varname === "tone_res_freq") return !(track > 0.5);
	return null;
}
