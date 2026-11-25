// aliasing_paint_dial: jspainter for every live.dial of the Aliasing face (R5).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_dial.js.
// Draws the mock-up's dial: a 270-degree track, the value arc (from the centre for bipolar ranges),
// a needle, and the value text below. The label is a separate comment box above the dial (so it can
// change with Free/Sync and survives a failing painter). Accent from the scripting name (paint_kit
// roleOf): w_ = write, r_ = read, tone_band = write, tone_res = read, else the text colour.
// ES5 ONLY (see paint_kit.ts).

import { accentFor, fitText, formatValue, normOf, roleOf } from "./paint_kit.ts";
import { currentPalette, dim, enableAutomationDots, font, isActive, measure, paramInfo, setColor, text, value, varnameOf } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var v = value();
	var accent = dim(accentFor(roleOf(varnameOf()), p), active, p);
	var small = w < 40;
	var textH = small ? 10 : 11;
	var knob = Math.min(w, h - textH);
	var cx = w / 2;
	var cy = knob / 2;
	var r = knob / 2 - (small ? 3.5 : 4);
	var lw = small ? 2.6 : 2.5;
	var a0 = Math.PI * 0.75;
	var sweep = Math.PI * 1.5;
	var n = normOf(v, info.lo, info.hi, info.exponent);
	var av = a0 + sweep * n;
	var bipolar = !info.labels && info.lo < 0 && info.hi > 0;
	var ac = bipolar ? a0 + sweep * normOf(0, info.lo, info.hi, info.exponent) : a0;

	mgraphics.set_line_cap("round");
	mgraphics.set_line_width(lw);
	setColor(dim(p.track, active, p));
	mgraphics.arc(cx, cy, r, a0, a0 + sweep);
	mgraphics.stroke();
	if (Math.abs(av - ac) > 0.01) {
		setColor(accent);
		mgraphics.arc(cx, cy, r, Math.min(ac, av), Math.max(ac, av));
		mgraphics.stroke();
	}
	setColor(accent);
	mgraphics.set_line_width(small ? 1.8 : 1.5);
	mgraphics.move_to(cx, cy);
	mgraphics.line_to(cx + Math.cos(av) * r * 0.71, cy + Math.sin(av) * r * 0.71);
	mgraphics.stroke();

	font(small ? 8 : 9, false);
	var s = fitText(formatValue(v, info.unitstyle, info.units, info.labels), w, measure);
	text(s, cx, h - (small ? 2 : 2.5), dim(p.text, active, p), "center");
}
