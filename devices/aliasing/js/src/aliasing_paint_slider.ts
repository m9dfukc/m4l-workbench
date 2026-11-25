// aliasing_paint_slider: jspainter for the horizontal live.sliders of the Aliasing face: the Size bar
// under the display (R9) and the bipolar Depth bars of the mod slots (R4).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_slider.js.
// Unipolar: fill from the left to the value (parameter exponent applied, so the fill follows the
// mouse); bipolar: fill from the centre. Short name left, value right. ES5 ONLY (see paint_kit.ts).

import { formatValue, normOf } from "./paint_kit.ts";
import { attrStr, currentPalette, dim, enableAutomationDots, font, isActive, paramInfo, setColor, text, value } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var v = value();
	var n = normOf(v, info.lo, info.hi, info.exponent);
	var bipolar = info.lo < 0 && info.hi > 0;

	setColor(dim(p.field, active, p));
	mgraphics.rectangle_rounded(0, 0, w, h, 4, 4);
	mgraphics.fill();
	setColor(dim(bipolar ? p.text : p.sizeFill, active, p));
	if (bipolar) {
		var c = normOf(0, info.lo, info.hi, info.exponent) * w;
		var x = n * w;
		var a = Math.min(c, x);
		var b = Math.max(c, x);
		if (b - a > 0.5) {
			mgraphics.set_source_rgba(p.text[0], p.text[1], p.text[2], active ? 0.55 : 0.22);
			mgraphics.rectangle(a, 1, b - a, h - 2);
			mgraphics.fill();
		}
		setColor(dim(p.label, active, p));
		mgraphics.rectangle(Math.round(c) - 0.5, 0, 1, h);
		mgraphics.fill();
	} else if (n > 0) {
		mgraphics.rectangle_rounded(0, 0, Math.max(n * w, 2), h, 4, 4);
		mgraphics.fill();
	}
	font(8, false);
	var name = attrStr("_parameter_shortname");
	if (!bipolar && name) text(name, 4, h / 2 + 3, dim(p.text, active, p), "left");
	text(formatValue(v, info.unitstyle, info.units, info.labels), w - 4, h / 2 + 3, dim(p.text, active, p), "right");
}
