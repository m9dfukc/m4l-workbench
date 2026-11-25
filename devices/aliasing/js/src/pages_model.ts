// Pure page logic for aliasing_pages (v8): which objects are visible for a page / mode state.
// Scripting names (set by scripts/bootstrap_shell.py) carry the rule:
//   <area>_<rest>       area lfo | mod | tone | out = page 0..3 (tabs LFO · Env, Mod, Tone, Global;
//                       "out" is the Global page); tbl = hidden on the Tone page (R11);
//                       w | r = the always visible pointer rows
//   <area>_<cond>_...   cond free | sync (the row's Hz|Sync mode, w -> wmode, r -> rmode; ignored
//                       outside the pointer rows),
//                       hz1 | sy1 (LFO 1 mode), hz2 | sy2 (LFO 2 mode),
//   w_symlbl_<group>    the write Sym label of a shape group: curve | skew | width | duty | smooth,
//                       shown for the write shape it belongs to (D6)
// Names that match none of these are left alone (null).
// Active (greyed) state, activeFor(): the write controls in Clean (D5), the resonator Freq while Track
// is on, and every control of a switched-off section (D17, D19) except its own power switch (_on).

export const PAGES = ["lfo", "mod", "tone", "out"] as const;
export const PAGE_TONE = 2;

export interface PageState {
	page: number;
	wmode: number;
	rmode: number;
	l1mode: number;
	l2mode: number;
	wshape: number;
}

export function initialState(): PageState {
	return { page: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1, wshape: 1 };
}

/** The write Sym label group of a write shape (D6): Ramp curve; Tri, Tri ±, Sine skew; Pulse, Spike
 *  width; Pulsar duty; Noise smooth. */
export function symLabelOf(shape: number): string {
	const k = Math.round(Number(shape)) || 0;
	if (k <= 0) return "curve";
	if (k <= 3) return "skew";
	if (k === 5) return "duty";
	if (k === 7) return "smooth";
	return "width";
}

export function clampPage(page: number): number {
	if (!Number.isFinite(page)) return 0;
	return Math.min(PAGES.length - 1, Math.max(0, Math.round(page)));
}

function condOk(area: string, cond: string, s: PageState, extra: string): boolean | null {
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
		case "symlbl":
			return area === "w" ? symLabelOf(s.wshape) === extra : true;
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
	const c = condOk(area, parts[1], s, parts[2] || "");
	if (c === null) return null;
	return areaOk && c;
}

export interface ActiveState {
	track: number; // Res Track
	wactive: number; // write state: 0 Freeze, 1 Write, 2 Clean
	drvon: number;
	bandon: number;
	reson: number;
	limon: number;
}

export function initialActive(): ActiveState {
	return { track: 1, wactive: 1, drvon: 1, bandon: 1, reson: 0, limon: 1 };
}

/** Write controls without effect in Clean (the write position follows the read signal). */
const CLEAN_IDLE = ["w_free_pitch", "w_sync_note", "w_fine", "w_sync_mult", "w_sync_div", "w_sym", "w_shape"];

/** `active` state of objects that depend on a switch, or null for objects not handled here. */
export function activeFor(varname: string | null | undefined, a: ActiveState): boolean | null {
	if (!varname) return null;
	const n = String(varname);
	if (CLEAN_IDLE.indexOf(n) >= 0) return !(a.wactive > 1.5);
	if (n.slice(-3) === "_on") return null;
	if (n === "tone_drive") return a.drvon > 0.5;
	if (n.indexOf("tone_band_") === 0) return a.bandon > 0.5;
	if (n === "tone_res_freq") return a.reson > 0.5 && !(a.track > 0.5);
	if (n.indexOf("tone_res_") === 0) return a.reson > 0.5;
	if (n.indexOf("out_lim_") === 0) return a.limon > 0.5;
	return null;
}

/** Panel fill for the device background colour from live.colors (D22, mock-up v0.3): a bit darker on a
 *  light background (8 % toward black), a bit lighter on a dark one (6 % toward white). */
export function panelColor(r: number, g: number, b: number): [number, number, number, number] {
	const ok = [r, g, b].every((x) => Number.isFinite(x));
	if (!ok) return [0, 0, 0, 0.07];
	const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
	if (lum > 0.5) return [r * 0.92, g * 0.92, b * 0.92, 1];
	return [r + (1 - r) * 0.06, g + (1 - g) * 0.06, b + (1 - b) * 0.06, 1];
}

/** Presentation rect of the v8ui display: on the Tone page the Size slider is hidden, so the tone curve
 *  takes the height of the table display + the slider (user, 2026-11-25; mock-up v0.3). */
export const DISPLAY_RECT = [308, 6, 328, 136];
export const DISPLAY_RECT_TONE = [308, 6, 328, 157];

export function displayRectFor(page: number): number[] {
	return clampPage(page) === PAGE_TONE ? DISPLAY_RECT_TONE : DISPLAY_RECT;
}
