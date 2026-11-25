// aliasing_paint_number: jspainter for the live.numbox fields of the Aliasing face (Sync multiplier
// "x1 .. x64", R2). Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_number.js.
// A dark field with the value centred. ES5 ONLY (see paint_kit.ts).

import { fitText, formatValue } from "./paint_kit.ts";
import { currentPalette, dim, enableAutomationDots, font, isActive, measure, paramInfo, setColor, text, value } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var v = value();

	setColor(dim(p.field, active, p));
	mgraphics.rectangle_rounded(0, 0, w, h, 6, 6);
	mgraphics.fill();
	font(9, false);
	text(fitText(formatValue(v, info.unitstyle, info.units, info.labels), w - 4, measure), w / 2, h / 2 + 3, dim(p.text, active, p), "center");
}
