// Pure page logic for aliasing_pages (v8): which objects are visible for a page / mode state, which are
// greyed out, and the theme colours of panels, markers and meters. Both faces of the device (D33, D40):
// "hybrid" (Aliasing.amxd: four pages, the 72-cell matrix on page Mod) and "b" (Aliasing B.amxd: seven
// side pages, a modulation strip showing the eight cells of one target).
// Scripting names (set by scripts/bootstrap_shell.py) carry the rule:
//   <area>_<rest>       area = a page of the face: hybrid lfo | mod | tone | out (LFO · Env, Mod, Tone,
//                       Global); b lfo1 | lfo2 | env | band | res | lim | out (LFO 1 ... Global);
//                       tbl = hidden on the hybrid's Tone page (R11); w | r = the always visible
//                       pointer rows; in face b, mod_<source>_<target> = a strip cell, visible while
//                       the strip shows its target (Mod Target menu)
//   <area>_<cond>_...   cond free | sync (the row's Hz|Sync mode, w -> wmode, r -> rmode; ignored
//                       outside the pointer rows),
//                       hz1 | sy1 (LFO 1 mode), hz2 | sy2 (LFO 2 mode),
//   w_symlbl_<group>    the write Sym label of a shape group (D6, D34): curve | skew | duty | width |
//                       smooth, shown for the write shape it belongs to
// Names that match none of these are left alone (null).
// Active (greyed) state, activeFor(): the write controls in Clean (D5), the resonator Freq while Track
// is on, every control of a switched-off section (D17, D19) except its own power switch (_on),
// Transpose while no pointer runs in Hz and Sync Rate while none runs in Sync (D37). The rule looks at
// the part of the name after the page prefix, so tone_band_center (hybrid) and band_band_center (b)
// behave alike.

export type Face = "hybrid" | "b";

export interface FaceSpec {
	pages: string[];
	tonePages: number[]; // pages on which the display shows the tone curve
	strip: boolean; // mod_ cells follow the Mod Target menu instead of a page
	resize: boolean; // D31: the display grows on the tone page
}

export const FACES: { [k: string]: FaceSpec } = {
	hybrid: { pages: ["lfo", "mod", "tone", "out"], tonePages: [2], strip: false, resize: true },
	b: { pages: ["lfo1", "lfo2", "env", "band", "res", "lim", "out"], tonePages: [3, 4], strip: true, resize: false },
};

export const PAGES = FACES.hybrid.pages;
export const PAGE_TONE = 2;

/** Matrix targets in the order of the Mod Target menu (D36) = the gen~ Param suffixes. */
export const TARGETS = ["wp", "sy", "wa", "rp", "sp", "sz", "bc", "rf", "ou"];

export function faceOf(name: unknown): Face {
	return String(name) === "b" ? "b" : "hybrid";
}

export interface PageState {
	face: Face;
	page: number;
	target: number;
	wmode: number;
	rmode: number;
	l1mode: number;
	l2mode: number;
	wshape: number;
}

export function initialState(face: Face = "hybrid"): PageState {
	return { face, page: 0, target: 0, wmode: 0, rmode: 0, l1mode: 0, l2mode: 1, wshape: 1 };
}

/** The write Sym label group of a write shape (D6, D34): Ramp curve, Tri skew, Pulsar duty, Spike
 *  width, Noise smooth. */
export function symLabelOf(shape: number): string {
	const k = Math.round(Number(shape)) || 0;
	if (k <= 0) return "curve";
	if (k === 1) return "skew";
	if (k === 2) return "duty";
	if (k === 3) return "width";
	return "smooth";
}

export function clampPage(page: number, face: Face = "hybrid"): number {
	const n = FACES[face].pages.length;
	if (!Number.isFinite(page)) return 0;
	return Math.min(n - 1, Math.max(0, Math.round(page)));
}

export function clampTarget(t: number): number {
	if (!Number.isFinite(t)) return 0;
	return Math.min(TARGETS.length - 1, Math.max(0, Math.round(t)));
}

export function isTonePage(page: number, face: Face = "hybrid"): boolean {
	return FACES[face].tonePages.indexOf(clampPage(page, face)) >= 0;
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
	const spec = FACES[s.face] || FACES.hybrid;
	const p = clampPage(s.page, s.face);
	if (spec.strip && area === "mod") {
		const t = TARGETS.indexOf(parts[2] || "");
		return t < 0 ? null : t === clampTarget(s.target);
	}
	let areaOk: boolean;
	const pageIndex = spec.pages.indexOf(area);
	if (pageIndex >= 0) areaOk = pageIndex === p;
	else if (area === "tbl") areaOk = !isTonePage(p, s.face);
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
	wmode: number; // pointer modes, for Transpose / Sync Rate (D37)
	rmode: number;
}

export function initialActive(): ActiveState {
	return { track: 1, wactive: 1, drvon: 1, bandon: 1, reson: 0, limon: 1, wmode: 0, rmode: 0 };
}

/** Write controls without effect in Clean (the write position follows the read signal). */
const CLEAN_IDLE = ["w_free_pitch", "w_sync_note", "w_fine", "w_sync_mult", "w_sync_div", "w_sym", "w_shape"];

/** `active` state of objects that depend on a switch, or null for objects not handled here. */
export function activeFor(varname: string | null | undefined, a: ActiveState): boolean | null {
	if (!varname) return null;
	const n = String(varname);
	if (CLEAN_IDLE.indexOf(n) >= 0) return !(a.wactive > 1.5);
	if (n.slice(-3) === "_on") return null;
	if (n.indexOf("mod_") === 0) return null;
	const key = n.substring(n.indexOf("_") + 1);
	if (key === "transpose") return a.wmode < 0.5 || a.rmode < 0.5;
	if (key === "syncrate") return a.wmode > 0.5 || a.rmode > 0.5;
	if (key === "drive") return a.drvon > 0.5;
	if (key.indexOf("band_") === 0) return a.bandon > 0.5;
	if (key === "res_freq") return a.reson > 0.5 && !(a.track > 0.5);
	if (key.indexOf("res_") === 0) return a.reson > 0.5;
	if (key.indexOf("lim_") === 0) return a.limon > 0.5;
	return null;
}

export type RGBA4 = [number, number, number, number];

function lumOf(r: number, g: number, b: number): number {
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Panel fill for the device background colour from live.colors (D22, mock-up v0.3): a bit darker on a
 *  light background (8 % toward black), a bit lighter on a dark one (6 % toward white). */
export function panelColor(r: number, g: number, b: number): RGBA4 {
	const ok = [r, g, b].every((x) => Number.isFinite(x));
	if (!ok) return [0, 0, 0, 0.07];
	if (lumOf(r, g, b) > 0.5) return [r * 0.92, g * 0.92, b * 0.92, 1];
	return [r + (1 - r) * 0.06, g + (1 - g) * 0.06, b + (1 - b) * 0.06, 1];
}

/** Live's device background is dark (the panels and painters then use the dark palette). */
export function surfaceIsDark(r: number, g: number, b: number): boolean {
	return !(lumOf(r, g, b) > 0.5);
}

const hex = (h: string): RGBA4 => {
	const n = parseInt(h.replace("#", ""), 16);
	return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1];
};

/** Colour of a matrix row marker (D39, face review §7 option A): write = the graphite write accent,
 *  read = the read blue, neutral = 45 % of the label grey on the panel (palette of paint_kit). */
export function markerColor(role: string, dark: boolean, panel: RGBA4): RGBA4 {
	if (role === "write") return hex(dark ? "#e4e4e4" : "#1c1c1c");
	if (role === "read") return hex(dark ? "#8fb0c4" : "#2f5873");
	const l = hex(dark ? "#b0b0b0" : "#262626");
	return [panel[0] + (l[0] - panel[0]) * 0.45, panel[1] + (l[1] - panel[1]) * 0.45, panel[2] + (l[2] - panel[2]) * 0.45, 1];
}

/** Role of a matrix target (rows of the hybrid's matrix): as paint_kit roleOf for mod_ cells. */
export function targetRole(t: string): string {
	if (t === "wp" || t === "sy" || t === "wa") return "write";
	if (t === "rp" || t === "sp") return "read";
	return "neutral";
}

/** live.meter~ colours in the graphite palette instead of stock green (D39, face review §9.2):
 *  light #3c3c3c on #dedede, dark #9a9a9a on #262626; overload in the text colour. */
export function meterColors(dark: boolean): { fill: RGBA4; bg: RGBA4; over: RGBA4 } {
	return dark
		? { fill: hex("#9a9a9a"), bg: hex("#262626"), over: hex("#d2d2d2") }
		: { fill: hex("#3c3c3c"), bg: hex("#dedede"), over: hex("#111111") };
}

/** Presentation rect of the hybrid's v8ui display: on the Tone page the Size slider is hidden, so the
 *  tone curve takes the height of the table display + the slider (D31). Face b keeps its rect (null). */
export const DISPLAY_RECT = [308, 6, 328, 136];
export const DISPLAY_RECT_TONE = [308, 6, 328, 157];

export function displayRectFor(page: number, face: Face = "hybrid"): number[] | null {
	if (!FACES[face].resize) return null;
	return isTonePage(page, face) ? DISPLAY_RECT_TONE : DISPLAY_RECT;
}
