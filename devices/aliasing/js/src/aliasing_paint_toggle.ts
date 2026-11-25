// aliasing_paint_toggle: jspainter for every live.text of the Aliasing face (R12 pill toggles and
// the Sync button). Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_toggle.js.
// On = filled with the role accent (write/read) or the selection colour; off = outlined.
// The texts come from the box's text / texton attributes. ES5 ONLY (see paint_kit.ts).

import { fitText, roleOf } from "./paint_kit.ts";
import { attrStr, currentPalette, dim, enableAutomationDots, font, isActive, measure, setColor, text, value, varnameOf } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var on = value() > 0.5;
	var role = roleOf(varnameOf());
	var accent = role === "write" ? p.write : role === "read" ? p.read : p.sel;
	var rad = Math.min(h - 1, 16);
	var label = attrStr(on ? "texton" : "text") || attrStr("text");

	if (on) {
		setColor(dim(accent, active, p));
		mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
		mgraphics.fill();
	}
	mgraphics.set_line_width(1);
	setColor(dim(on ? accent : p.track, active, p));
	mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
	mgraphics.stroke();
	font(h <= 14 ? 8 : 9, false);
	text(fitText(label, w - 6, measure), w / 2, h / 2 + 3, dim(on ? p.selFg : p.text, active, p), "center");
}
