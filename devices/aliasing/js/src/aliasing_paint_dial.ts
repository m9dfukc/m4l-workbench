// aliasing_paint_dial: jspainter for every live.dial of the Aliasing faces (R5; v0.3b D33, D43).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_dial.js.
// Two layouts, chosen by the box height Live gives the painter (it is fixed by showname/shownumber,
// not by the saved rect [measured: dial probe 2026-11-25, build/aliasing/dialprobe/Max.log]):
// - 48-px box (showname 1, shownumber 1; face review "Hybrid"): the parameter's short name on top
//   (9.5 pt, baseline y+10), a 270-degree ring r 12.5 with its centre at y+26, the value below
//   (9.5 pt, baseline y+47). The name is skipped for dials whose name changes with another parameter
//   (Sym per write shape, Fine/Detune per mode): a live.comment overlay shows it (face review h.2).
// - 36-px box (showname 0, face review §1.1): ring r = min(w/2 - 3.5, (h - 10)/2), centre r + 2, the
//   value 9 pt in the ring's open end, baseline h - 1.
// Values that are wider than the box are written compactly ("0.1ms", D43); names that do not fit
// shrink to three letters ("Att"). Accent from the scripting name (paint_kit roleOf).
// ES5 ONLY (see paint_kit.ts).

import { accentFor, compactValue, FONT_SIZE, fitName, formatValue, normOf, roleOf } from "./paint_kit.ts";
import { attrStr, currentPalette, dim, enableAutomationDots, font, isActive, measure, paramInfo, setColor, text, value, varnameOf } from "./paint_max.ts";

enableAutomationDots();

/** Dials whose name row is drawn by a live.comment overlay (it changes with another parameter). */
var NAME_OVERLAY = ["w_sym", "w_fine", "r_fine"];

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var v = value();
	var name = varnameOf();
	var accent = dim(accentFor(roleOf(name), p), active, p);
	var tall = h >= 44;
	var cx = Math.round(w / 2);
	var r: number;
	var cy: number;
	var valueBase: number;
	var fs: number;
	if (tall) {
		r = 12.5;
		cy = 26;
		valueBase = 47;
		fs = FONT_SIZE;
	} else {
		r = Math.max(4, Math.min(w / 2 - 3.5, (h - 10) / 2));
		cy = r + 2;
		valueBase = h - 1;
		fs = 9;
	}
	var a0 = Math.PI * 0.75;
	var sweep = Math.PI * 1.5;
	var n = normOf(v, info.lo, info.hi, info.exponent);
	var av = a0 + sweep * n;
	var bipolar = !info.labels && info.lo < 0 && info.hi > 0;
	var ac = bipolar ? a0 + sweep * normOf(0, info.lo, info.hi, info.exponent) : a0;

	mgraphics.set_line_cap("round");
	mgraphics.set_line_width(2.5);
	setColor(dim(p.dialTrack, active, p));
	mgraphics.arc(cx, cy, r, a0, a0 + sweep);
	mgraphics.stroke();
	if (Math.abs(av - ac) > 0.01) {
		setColor(accent);
		mgraphics.arc(cx, cy, r, Math.min(ac, av), Math.max(ac, av));
		mgraphics.stroke();
	}
	setColor(accent);
	mgraphics.set_line_width(1.5);
	mgraphics.move_to(cx, cy);
	mgraphics.line_to(cx + Math.cos(av) * r * 0.71, cy + Math.sin(av) * r * 0.71);
	mgraphics.stroke();

	font(fs, false);
	if (tall && NAME_OVERLAY.indexOf(name) < 0) {
		var short = attrStr("_parameter_shortname");
		if (short) text(fitName(short, w - 1, measure), cx, 10, dim(p.label, active, p), "center");
	}
	// keep 3 px between neighbouring boxes (34-px LFO · Env dials, face review h.2)
	var s = compactValue(formatValue(v, info.unitstyle, info.units, info.labels), w - 3, measure);
	text(s, cx, valueBase, dim(p.text, active, p), "center");
}
