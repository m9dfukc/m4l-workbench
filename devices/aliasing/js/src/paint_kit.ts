// paint_kit: shared drawing code of the Aliasing jspainter scripts (aliasing_paint_*.ts).
//
// ES5 ONLY: var and function, no let/const, arrows, classes, template strings, default or rest
// parameters, for-of or spread. Which JS engine runs jspainter scripts in Live is unknown (probe
// t2 not run), so the painters must parse on the legacy engine too. tools/js-build.mjs builds the
// painters with esbuild target es5, which fails on any newer syntax.
//
// Pure functions take what they need as arguments (no Max globals), so js/test/ can run them in
// Node. The colour palette is "Graphite" from the approved mock-up (redesign-t1.md, mock-up §).

export type RGBA = number[];

export interface Palette {
	dark: boolean;
	text: RGBA;
	label: RGBA;
	track: RGBA;
	rule: RGBA;
	field: RGBA;
	sel: RGBA;
	selFg: RGBA;
	sizeFill: RGBA;
	write: RGBA;
	read: RGBA;
	disp: RGBA;
	voice: RGBA;
	meter: RGBA;
}

export function hex(h: string, a?: number): RGBA {
	var n = parseInt(h.replace("#", ""), 16);
	return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, a === undefined ? 1 : a];
}

export function withAlpha(c: RGBA, a: number): RGBA {
	return [c[0], c[1], c[2], a];
}

export function mixColor(a: RGBA, b: RGBA, t: number): RGBA {
	return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t];
}

export function luminance(c: RGBA): number {
	return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

/** Graphite palette, dark or light: the v0.3 mock-up's theme values (docs/mockup-v0.3/Main.dc.html THEME),
 *  tuned for the theme panels (D22): outlines stay visible on the panel surfaces. */
export function palette(dark: boolean): Palette {
	if (dark) {
		return {
			dark: true,
			text: hex("#d2d2d2"),
			label: hex("#b0b0b0"),
			track: hex("#5c5c5c"),
			rule: hex("#2a2a2a"),
			field: hex("#262626"),
			sel: hex("#d6d6d6"),
			selFg: hex("#1b1b1b"),
			sizeFill: hex("#4c4c4c"),
			write: hex("#e4e4e4"),
			read: hex("#8fb0c4"),
			disp: hex("#161616"),
			voice: hex("#a6a6a6"),
			meter: hex("#9a9a9a"),
		};
	}
	return {
		dark: false,
		text: hex("#111111"),
		label: hex("#262626"),
		track: hex("#6e6e6e"),
		rule: hex("#d0d0d0"),
		field: hex("#dedede"),
		sel: hex("#1f1f1f"),
		selFg: hex("#efefef"),
		sizeFill: hex("#bdbdbd"),
		write: hex("#1c1c1c"),
		read: hex("#2f5873"),
		disp: hex("#ececec"),
		voice: hex("#4a4a4a"),
		meter: hex("#3c3c3c"),
	};
}

/**
 * Dark or light Live theme, from the theme's control foreground colour (light text = dark theme).
 * getcolor is Max's max.getcolor or null when it is not available (then: dark).
 */
export function themeIsDark(getcolor: ((id: string) => any) | null): boolean {
	if (!getcolor) return true;
	try {
		var c = getcolor("live_control_fg");
		if (c && c.length >= 3) return luminance([Number(c[0]), Number(c[1]), Number(c[2]), 1]) > 0.45;
	} catch (e) {}
	return true;
}

/** Accent role of a control from its scripting name: write, read or neutral. Matrix cells
 *  mod_<source>_<target> take the role of their target: Write Pitch, Write Sym, Write = write;
 *  Read Pitch, Read Spread = read (mock-up v0.3). */
export function roleOf(varname: string): string {
	var v = String(varname || "");
	if (v.indexOf("mod_") === 0) {
		var t = v.substring(v.lastIndexOf("_") + 1);
		if (t === "wp" || t === "sy" || t === "wa") return "write";
		if (t === "rp" || t === "sp") return "read";
		return "neutral";
	}
	if (v.indexOf("w_") === 0 || v.indexOf("tone_band") === 0) return "write";
	if (v.indexOf("r_") === 0 || v.indexOf("tone_res") === 0) return "read";
	return "neutral";
}

export function accentFor(role: string, p: Palette): RGBA {
	if (role === "write") return p.write;
	if (role === "read") return p.read;
	return p.text;
}

export function clamp(x: number, lo: number, hi: number): number {
	return x < lo ? lo : x > hi ? hi : x;
}

/** First number of a getvalueof()/getattr() result (arrays, strings, numbers), or NaN. */
export function firstNumber(v: any): number {
	if (v === null || v === undefined) return NaN;
	if (typeof v === "object" && v.length !== undefined) return v.length ? parseFloat(v[0]) : NaN;
	return parseFloat(v);
}

/** Normalised 0..1 position of a value in [lo, hi] with Live's parameter exponent. */
export function normOf(v: number, lo: number, hi: number, exponent: number): number {
	if (!(hi > lo)) return 0;
	var n = clamp((v - lo) / (hi - lo), 0, 1);
	var e = exponent > 0 ? exponent : 1;
	return Math.pow(n, 1 / e);
}

/** Minimal printf for Live's custom unit strings: %d %i %f %.Nf %0.Nf %s %%. */
export function sprintf1(fmt: string, v: number): string {
	var out = "";
	var i = 0;
	while (i < fmt.length) {
		var ch = fmt.charAt(i);
		if (ch !== "%") {
			out += ch;
			i++;
			continue;
		}
		var j = i + 1;
		var spec = "";
		while (j < fmt.length && "0123456789.-+ ".indexOf(fmt.charAt(j)) >= 0) {
			spec += fmt.charAt(j);
			j++;
		}
		var conv = fmt.charAt(j);
		if (conv === "%") {
			out += "%";
		} else if (conv === "d" || conv === "i") {
			out += String(Math.round(v));
		} else if (conv === "f") {
			var dot = spec.indexOf(".");
			var prec = dot >= 0 ? parseInt(spec.substring(dot + 1), 10) : 6;
			if (isNaN(prec)) prec = 6;
			out += v.toFixed(prec);
		} else if (conv === "s") {
			out += String(v);
		} else {
			out += "%" + spec + conv;
		}
		i = j + 1;
	}
	return out;
}

/** Frequency text like Live's Hertz unit: "20.0 Hz", "632 Hz", "2.11 kHz", "20.0 kHz". */
export function formatHz(f: number): string {
	if (f >= 10000) return (f / 1000).toFixed(1) + " kHz";
	if (f >= 1000) return (f / 1000).toFixed(2) + " kHz";
	if (f >= 100) return String(Math.round(f)) + " Hz";
	if (f >= 10) return f.toFixed(1) + " Hz";
	return f.toFixed(2) + " Hz";
}

/**
 * Value text of a parameter: Live unit styles 0 int, 1 float, 2 ms, 3 Hz, 4 dB, 5 %, 6 pan,
 * 7 semitones, 8 MIDI note, 9 custom (printf `units`), 10 native; enums show their label.
 */
export function formatValue(v: number, unitstyle: number, units: string, enumLabels: string[] | null): string {
	if (isNaN(v)) return "";
	if (enumLabels && enumLabels.length) {
		var k = clamp(Math.round(v), 0, enumLabels.length - 1);
		return String(enumLabels[k]);
	}
	switch (unitstyle) {
		case 0:
			return String(Math.round(v));
		case 2:
			return v >= 1000 ? (v / 1000).toFixed(2) + " s" : v.toFixed(v < 10 ? 2 : 0) + " ms";
		case 3:
			return formatHz(v);
		case 4:
			return (v <= -69.95 ? "-inf" : v.toFixed(1)) + " dB";
		case 5:
			return v.toFixed(Math.abs(v) < 10 ? 1 : 0) + " %";
		case 6:
			return v === 0 ? "C" : Math.abs(Math.round(v)) + (v < 0 ? "L" : "R");
		case 7:
			return (v > 0 ? "+" : "") + Math.round(v) + " st";
		case 9:
			return units ? sprintf1(units, v) : v.toFixed(2);
		default:
			return Math.abs(v) >= 100 ? String(Math.round(v)) : v.toFixed(2);
	}
}

/** Enum labels from getattr("_parameter_range") of an enum parameter (Ableton's painter reads it so). */
export function enumLabelsFrom(range: any, type: number): string[] | null {
	if (type !== 2 || !range || typeof range !== "object" || range.length === undefined) return null;
	var out: string[] = [];
	for (var i = 0; i < range.length; i++) out.push(String(range[i]));
	return out.length ? out : null;
}

/** Write-shape icons (D4): the write head's position over one cycle (mock-up v0.3), 22 x 12 box. */
function writeIcon(label: string): number[][] | null {
	switch (label) {
		case "Ramp":
			return [[1, 11], [21, 1], [21, 11]];
		case "Tri":
			return [[1, 11], [11, 1], [21, 11]];
		case "Tri ±":
			return [[1, 11], [6, 11], [11, 1], [16, 11], [21, 11]];
		case "Sine": {
			var pts: number[][] = [];
			for (var i = 0; i <= 20; i++) pts.push([1 + i, 11 - 10 * (0.5 - 0.5 * Math.cos((i / 20) * 2 * Math.PI))]);
			return pts;
		}
		case "Pulse":
			return [[1, 11], [11, 11], [11, 1], [21, 1]];
		case "Pulsar":
			return [[1, 11], [9, 1], [9, 11], [21, 11]];
		case "Spike":
			return [[1, 11], [5, 1], [9, 11], [21, 11]];
		case "Noise":
			return [[1, 7], [4, 7], [4, 2], [7, 2], [7, 9], [10, 9], [10, 4], [13, 4], [13, 10], [16, 10], [16, 3], [19, 3], [19, 6], [21, 6]];
		default:
			return null;
	}
}

/** Points of a waveform icon for a shape label, in a 22 x 12 box; null = draw the label as text.
 *  family "write" = the write shapes (positions), otherwise the LFO / read shapes. */
export function iconPath(label: string, family?: string): number[][] | null {
	if (family === "write") return writeIcon(label);
	switch (label) {
		case "Ramp":
		case "Saw":
			return [[1, 11], [21, 1], [21, 11]];
		case "Tri":
			return [[1, 11], [11, 1], [21, 11]];
		case "Tri ±":
			return [[1, 6], [6, 1], [16, 11], [21, 6]];
		case "Square":
			return [[1, 11], [1, 1], [11, 1], [11, 11], [21, 11], [21, 1]];
		case "S&H":
			return [[1, 8], [5, 8], [5, 3], [9, 3], [9, 10], [13, 10], [13, 5], [17, 5], [17, 9], [21, 9]];
		case "Sine": {
			var pts: number[][] = [];
			for (var i = 0; i <= 20; i++) pts.push([1 + i, 6 - 5 * Math.sin((i / 20) * 2 * Math.PI)]);
			return pts;
		}
		case "Random": {
			var r = [6, 2.5, 4, 8, 10.5, 9, 4.5, 3, 6, 5];
			var q: number[][] = [];
			for (var k = 0; k < r.length; k++) q.push([1 + (k * 20) / (r.length - 1), r[k]]);
			return q;
		}
		default:
			return null;
	}
}

/** Text that fits into maxw: shortened with a trailing "." when needed. measure(s) -> width. */
export function fitText(s: string, maxw: number, measure: (t: string) => number): string {
	if (measure(s) <= maxw) return s;
	var t = s;
	while (t.length > 1 && measure(t + ".") > maxw) t = t.substring(0, t.length - 1);
	return t + ".";
}
