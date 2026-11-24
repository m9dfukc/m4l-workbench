// probe_tab_painter.js: jspainter for the live.tab "Probe Tab" in ProbeUI.amxd (check G-UI1).
// Plain ES5 on purpose (see probe_dial_painter.js): modern syntax is only tested inside strings.
//
// Draws a pill-style segmented control; each segment shows a waveform icon drawn as a path
// (sine, triangle, saw, square). The selected segment is filled with a muted accent.
// Theme colours come from max.getcolor() inside paint(), so a Live theme change must repaint.

var PAINTER = "probe_tab_painter";
var MUTED = [0.46, 0.64, 0.60, 1.0]; // muted sage accent, same as the dial
var FALLBACK_ITEMS = ["Sine", "Tri", "Saw", "Square"];
var reported = false;
var lastFg = "";

try {
	box.setattr("jspainterautomation", 1);
} catch (e) {}

function tryParse(src) {
	try {
		new Function(src);
		return 1;
	} catch (e) {
		return 0;
	}
}
tryParse.local = 1;

function stackStyle() {
	try {
		throw new Error("probe");
	} catch (e) {
		var s = String(e.stack || "");
		if (s.indexOf("    at ") >= 0) return "v8";
		if (s.indexOf("@") >= 0) return "spidermonkey";
		return s.length ? "other" : "none";
	}
}
stackStyle.local = 1;

function readAttr(name) {
	try {
		var v = box.getattr(name);
		if (v === undefined || v === null) return null;
		if (typeof v === "object" && v.length !== undefined) v = v.length ? v[0] : null;
		return v;
	} catch (e) {
		return null;
	}
}
readAttr.local = 1;

function themeColor(id, fallback) {
	try {
		if (typeof max !== "undefined" && typeof max.getcolor === "function") {
			var c = max.getcolor(id);
			if (c && c.length >= 3) return [c[0], c[1], c[2], c.length > 3 ? c[3] : 1];
		}
	} catch (e) {}
	return fallback;
}
themeColor.local = 1;

function mix(a, b, t) {
	return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t];
}
mix.local = 1;

function alpha(c, a) {
	return [c[0], c[1], c[2], a];
}
alpha.local = 1;

function items() {
	var r = null;
	try {
		r = box.getattr("_parameter_range");
	} catch (e) {}
	if (r && r.length >= 2) {
		if (typeof r[0] === "string") return r;
		var n = Math.round(r[1] - r[0]) + 1;
		if (n >= 1 && n <= 16) return FALLBACK_ITEMS.slice(0, n);
	}
	return FALLBACK_ITEMS;
}
items.local = 1;

function report(w, h, list) {
	var f = [];
	f.push("let=" + tryParse("let a = 1; return a;"));
	f.push("const=" + tryParse("const a = 1; return a;"));
	f.push("arrow=" + tryParse("var g = (x) => x; return g(1);"));
	f.push("template=" + tryParse("var s = `t${1}`; return s;"));
	f.push("class=" + tryParse("class A {} return A;"));
	f.push("destructuring=" + tryParse("var [a, b] = [1, 2]; return a + b;"));
	f.push("optchain=" + tryParse("var o = null; return o?.x;"));
	f.push("Symbol=" + (typeof Symbol === "function" ? 1 : 0));
	f.push("Promise=" + (typeof Promise === "function" ? 1 : 0));
	f.push("globalThis=" + (typeof globalThis === "object" ? 1 : 0));
	f.push("stack=" + stackStyle());

	var a = [];
	var hasMax = typeof max !== "undefined";
	a.push("max.version=" + (hasMax ? max.version : "n/a"));
	a.push("getcolor=" + (hasMax && typeof max.getcolor === "function" ? 1 : 0));
	a.push("parentpaint=" + (typeof mgraphics.parentpaint === "function" ? 1 : 0));
	a.push("isautomated=" + readAttr("isautomated"));
	a.push("hasfocus=" + readAttr("hasfocus"));
	a.push("jspainterautomation=" + readAttr("jspainterautomation"));
	a.push("_parameter_range=" + String(box.getattr("_parameter_range")));
	a.push("items=" + list.join("/"));
	a.push("value=" + String(box.getvalueof()));
	a.push("size=" + Math.round(w) + "x" + Math.round(h));

	var line = PAINTER + ": ENGINE " + f.join(" ") + " | API " + a.join(" ");
	post(line + "\n");
	error("[ProbeUI info, not an error] " + line + "\n");
}
report.local = 1;

function icon(kind, x, y, w, h) {
	var mid = y + h / 2;
	mgraphics.move_to(x, mid);
	if (kind === "sin") {
		for (var i = 1; i <= 24; i++) {
			var t = i / 24;
			mgraphics.line_to(x + t * w, mid - Math.sin(t * Math.PI * 2) * h / 2);
		}
	} else if (kind === "tri") {
		mgraphics.line_to(x + w * 0.25, y);
		mgraphics.line_to(x + w * 0.75, y + h);
		mgraphics.line_to(x + w, mid);
	} else if (kind === "saw") {
		mgraphics.line_to(x + w * 0.5, y);
		mgraphics.line_to(x + w * 0.5, y + h);
		mgraphics.line_to(x + w, mid);
	} else {
		mgraphics.move_to(x, y + h);
		mgraphics.line_to(x, y);
		mgraphics.line_to(x + w * 0.5, y);
		mgraphics.line_to(x + w * 0.5, y + h);
		mgraphics.line_to(x + w, y + h);
		mgraphics.line_to(x + w, y);
	}
	mgraphics.stroke();
}
icon.local = 1;

function kindOf(name, i) {
	var s = String(name).toLowerCase();
	if (s.indexOf("sin") >= 0) return "sin";
	if (s.indexOf("tri") >= 0) return "tri";
	if (s.indexOf("saw") >= 0 || s.indexOf("ramp") >= 0) return "saw";
	if (s.indexOf("sq") >= 0 || s.indexOf("pul") >= 0) return "sq";
	return ["sin", "tri", "saw", "sq"][i % 4];
}
kindOf.local = 1;

function paint() {
	var size = mgraphics.size;
	var w = size[0];
	var h = size[1];
	var list = items();
	var n = list.length;

	var fg = themeColor("live_control_fg", [0.85, 0.85, 0.85, 1]);
	var dark = themeColor("live_control_bg", [0.12, 0.12, 0.12, 1]);
	var accent = mix(MUTED, themeColor("live_control_selection", MUTED), 0.25);
	var fgKey = fg.join(",");
	if (reported && fgKey !== lastFg) post(PAINTER + ": repaint with new theme colour live_control_fg=" + fgKey + "\n");
	lastFg = fgKey;

	if (!reported) {
		reported = true;
		report(w, h, list);
	}
	if (readAttr("active") === 0) accent = mix(accent, alpha(fg, 1), 0.6);

	var raw = box.getvalueof();
	var idx = Math.round(parseFloat(raw && typeof raw === "object" ? raw[0] : raw));
	if (isNaN(idx)) idx = 0;
	idx = Math.max(0, Math.min(n - 1, idx));

	// pill body
	var rad = h - 1;
	mgraphics.set_source_rgba(alpha(fg, 0.1));
	mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
	mgraphics.fill();
	mgraphics.set_line_width(1);
	mgraphics.set_source_rgba(alpha(fg, readAttr("hasfocus") === 1 ? 0.6 : 0.22));
	mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
	mgraphics.stroke();

	// selected segment
	var sw = w / n;
	mgraphics.set_source_rgba(accent);
	mgraphics.rectangle_rounded(idx * sw + 2, 2, sw - 4, h - 4, h - 4, h - 4);
	mgraphics.fill();

	// icons
	var iw = Math.min(sw * 0.5, 18);
	var ih = h * 0.4;
	mgraphics.set_line_width(1.5);
	mgraphics.set_line_cap("round");
	mgraphics.set_line_join("round");
	for (var i = 0; i < n; i++) {
		mgraphics.set_source_rgba(i === idx ? dark : alpha(fg, 0.75));
		icon(kindOf(list[i], i), i * sw + (sw - iw) / 2, (h - ih) / 2, iw, ih);
	}
}
