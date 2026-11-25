// paint_max: the Max-facing half of the painter kit (uses the jspainter globals box, mgraphics, max).
// ES5 ONLY (see paint_kit.ts). Every access to box/max is guarded: a failing attribute read must
// never stop paint(), it falls back to a neutral value instead.

import {
	enumLabelsFrom,
	firstNumber,
	palette,
	themeIsDark,
	type Palette,
	type RGBA,
} from "./paint_kit.ts";

export var FONT = "Ableton Sans Medium";
export var FONT_BOLD = "Ableton Sans Bold";

export function attr(name: string): any {
	try {
		return box.getattr(name);
	} catch (e) {
		return null;
	}
}

export function attrNum(name: string, fallback: number): number {
	var n = firstNumber(attr(name));
	return isNaN(n) ? fallback : n;
}

export function attrStr(name: string): string {
	var a = attr(name);
	if (a === null || a === undefined) return "";
	if (typeof a === "object" && a.length !== undefined) {
		var parts: string[] = [];
		for (var i = 0; i < a.length; i++) parts.push(String(a[i]));
		return parts.join(" ");
	}
	return String(a);
}

function getcolorFn(): ((id: string) => any) | null {
	try {
		if (typeof max !== "undefined" && max && typeof max.getcolor === "function") {
			return function (id: string) {
				return max.getcolor(id);
			};
		}
	} catch (e) {}
	return null;
}

/** Graphite palette for the current Live theme; read in every paint() (a theme change repaints). */
export function currentPalette(): Palette {
	return palette(themeIsDark(getcolorFn()));
}

export function varnameOf(): string {
	try {
		var v = (box as any).varname;
		if (v) return String(v);
	} catch (e) {}
	return attrStr("varname");
}

export function isActive(): boolean {
	return attrNum("active", 1) !== 0;
}

export function value(): number {
	var v: any = 0;
	try {
		v = box.getvalueof();
	} catch (e) {}
	var n = firstNumber(v);
	return isNaN(n) ? 0 : n;
}

export interface ParamInfo {
	lo: number;
	hi: number;
	exponent: number;
	type: number;
	unitstyle: number;
	units: string;
	labels: string[] | null;
}

/** Range, type, exponent and units of the box's Live parameter (hidden _parameter_* attributes). */
export function paramInfo(): ParamInfo {
	var type = attrNum("_parameter_type", 0);
	var range = attr("_parameter_range");
	var labels = enumLabelsFrom(range, type);
	var lo = 0;
	var hi = 1;
	if (labels) {
		hi = labels.length - 1;
	} else if (range && typeof range === "object" && range.length >= 2) {
		lo = parseFloat(range[0]);
		hi = parseFloat(range[1]);
		if (isNaN(lo) || isNaN(hi)) {
			lo = 0;
			hi = 1;
		}
	}
	return {
		lo: lo,
		hi: hi,
		exponent: attrNum("_parameter_exponent", 1),
		type: type,
		unitstyle: attrNum("_parameter_unitstyle", 1),
		units: attrStr("_parameter_units"),
		labels: labels,
	};
}

export function setColor(c: RGBA): void {
	mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
}

export function font(size: number, bold: boolean): void {
	mgraphics.select_font_face(bold ? FONT_BOLD : FONT);
	mgraphics.set_font_size(size);
}

export function measure(s: string): number {
	return mgraphics.text_measure(s)[0];
}

/** Text with the baseline at y; align "left" | "center" | "right". Font must be selected. */
export function text(s: string, x: number, y: number, color: RGBA, align: string): void {
	var w = measure(s);
	var tx = align === "center" ? x - w / 2 : align === "right" ? x - w : x;
	setColor(color);
	mgraphics.move_to(tx, y);
	mgraphics.show_text(s);
}

/** Draw Live's automation/modulation/macro dots even without parentpaint (Max 9.2; ignored before). */
export function enableAutomationDots(): void {
	try {
		box.setattr("jspainterautomation", 1);
	} catch (e) {}
}

export function polyline(pts: number[][], x: number, y: number, sx: number, sy: number): void {
	for (var i = 0; i < pts.length; i++) {
		var px = x + pts[i][0] * sx;
		var py = y + pts[i][1] * sy;
		if (i === 0) mgraphics.move_to(px, py);
		else mgraphics.line_to(px, py);
	}
}

export function dim(c: RGBA, active: boolean, p: Palette): RGBA {
	if (active) return c;
	return [c[0], c[1], c[2], c[3] * (p.dark ? 0.4 : 0.45)];
}
