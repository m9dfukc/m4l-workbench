// probe_dial_painter.js: jspainter for the live.dial "Probe Dial" in ProbeUI.amxd (check G-UI1).
// Plain ES5 on purpose: which JS engine runs jspainter scripts is one of the questions this probe
// answers, so the painter itself must not depend on the answer. Modern syntax is only tested
// inside strings via new Function(...) in try/catch.
//
// Draws: track + value arc in a muted accent, value text, short name, and a status row that says
// whether the automation/modulation/macro state attributes (Max 9.2 user guide, "Hidden jspainter
// attributes") are readable here. Native dots are requested via jspainterautomation = 1.
// Theme colours come from max.getcolor() inside paint(), so a Live theme change must repaint.

var PAINTER = "probe_dial_painter";
var MUTED = [0.46, 0.64, 0.60, 1.0]; // muted sage accent
var FONT = "Ableton Sans Medium";
var reported = false;
var stateReadable = null; // null until the first paint, then true/false
var lastFg = "";

try {
	box.setattr("jspainterautomation", 1); // as in the 9.2 user guide example (top level)
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

function report(w, h) {
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
	a.push("stylemap=" + (typeof box.attrname_forstylemap === "function" ? 1 : 0));
	a.push("isautomated=" + readAttr("isautomated"));
	a.push("ismodulated=" + readAttr("ismodulated"));
	a.push("ismacroassigned=" + readAttr("ismacroassigned"));
	a.push("hasfocus=" + readAttr("hasfocus"));
	a.push("jspainterautomation=" + readAttr("jspainterautomation"));
	a.push("jspainterfocus=" + readAttr("jspainterfocus"));
	a.push("_parameter_range=" + String(box.getattr("_parameter_range")));
	a.push("value=" + String(box.getvalueof()));
	a.push("size=" + Math.round(w) + "x" + Math.round(h));

	var line = PAINTER + ": ENGINE " + f.join(" ") + " | API " + a.join(" ");
	post(line + "\n");
	// also as an error line so it reaches Live's Log.txt ("Message from Max") [open: whether post() does]
	error("[ProbeUI info, not an error] " + line + "\n");
}
report.local = 1;

function text(str, x, y, size, color, align) {
	mgraphics.select_font_face(FONT);
	mgraphics.set_font_size(size);
	var m = mgraphics.text_measure(str);
	var tx = align === "center" ? x - m[0] / 2 : align === "right" ? x - m[0] : x;
	mgraphics.set_source_rgba(color);
	mgraphics.move_to(tx, y);
	mgraphics.show_text(str);
	return m[0];
}
text.local = 1;

function paint() {
	var size = mgraphics.size;
	var w = size[0];
	var h = size[1];

	// theme colours, read on every paint (a theme change must repaint)
	var fg = themeColor("live_control_fg", [0.85, 0.85, 0.85, 1]);
	var sel = themeColor("live_control_selection", [0.4, 0.7, 0.9, 1]);
	var accent = mix(MUTED, themeColor("live_dial_fg", MUTED), 0.25);
	var fgKey = fg.join(",");
	if (reported && fgKey !== lastFg) post(PAINTER + ": repaint with new theme colour live_control_fg=" + fgKey + "\n");
	lastFg = fgKey;

	if (!reported) {
		reported = true;
		try {
			box.setattr("jspainterautomation", 1);
			box.setattr("automationpoint", w - 10, 1);
		} catch (e) {
			post(PAINTER + ": setattr failed: " + e + "\n");
		}
		report(w, h);
		stateReadable = readAttr("isautomated") !== null;
	}

	if (readAttr("active") === 0) accent = mix(accent, alpha(fg, 1), 0.6);

	// value -> 0..1
	var raw = box.getvalueof();
	var v = parseFloat(raw && typeof raw === "object" ? raw[0] : raw);
	if (isNaN(v)) v = 0;
	var lo = 0;
	var hi = 1;
	var range = box.getattr("_parameter_range");
	if (range && range.length >= 2 && typeof range[0] === "number") {
		lo = range[0];
		hi = range[1];
	}
	var expo = parseFloat(box.getattr("_parameter_exponent"));
	if (!(expo > 0)) expo = 1;
	var norm = hi !== lo ? (v - lo) / (hi - lo) : 0;
	norm = Math.pow(Math.max(0, Math.min(1, norm)), 1 / expo);

	// arc
	var r = Math.min(w, h - 30) / 2 - 4;
	var cx = w / 2;
	var cy = r + 6;
	var a0 = Math.PI * 0.75;
	var sweep = Math.PI * 1.5;
	mgraphics.set_line_cap("round");
	mgraphics.set_line_width(3.5);
	mgraphics.set_source_rgba(alpha(fg, 0.18));
	mgraphics.arc(cx, cy, r, a0, a0 + sweep);
	mgraphics.stroke();
	if (norm > 0.001) {
		mgraphics.set_source_rgba(accent);
		mgraphics.arc(cx, cy, r, a0, a0 + sweep * norm);
		mgraphics.stroke();
	}
	// needle dot at the value end
	var ae = a0 + sweep * norm;
	mgraphics.set_source_rgba(accent);
	mgraphics.ellipse(cx + Math.cos(ae) * r - 3, cy + Math.sin(ae) * r - 3, 6, 6);
	mgraphics.fill();

	// value text and name
	text(v.toFixed(2), cx, cy + 4, 11, fg, "center");
	var name = String(box.getattr("_parameter_shortname") || "Probe Dial");
	text(name, cx, cy + r + 9, 9, alpha(fg, 0.7), "center");

	// theme swatch (top left): live_control_selection straight from getcolor()
	mgraphics.set_source_rgba(sel);
	mgraphics.rectangle(1, 1, 5, 5);
	mgraphics.fill();

	// automation / modulation / macro state
	var y = h - 3;
	if (!stateReadable) {
		text("state attrs: n/a", cx, y, 8, alpha(fg, 0.6), "center");
	} else {
		var labels = ["aut", "mod", "mac"];
		var attrs = ["isautomated", "ismodulated", "ismacroassigned"];
		var x = cx - 30;
		for (var i = 0; i < 3; i++) {
			var on = readAttr(attrs[i]) === 1;
			x += text(labels[i], x, y, 8, on ? accent : alpha(fg, 0.3), "left") + 4;
		}
	}
}
