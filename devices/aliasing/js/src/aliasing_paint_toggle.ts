// aliasing_paint_toggle: jspainter for every live.text of the Aliasing face (R12 pill toggles, the
// Sync button, and the section power switches, D17/D19/D32). Bundled (ES5) by tools/js-build.mjs into
// devices/aliasing/aliasing_paint_toggle.js. The texts come from the box's text / texton attributes.
// - Pills: on = filled with the role accent (write/read) or the selection colour; off = outlined.
// - Section power switches (scripting names ending in _on, D32 = mock-up variant E): a plain bold
//   section title with a power symbol right after it, measured in Live's own font; on = filled symbol,
//   off = outlined symbol and a dimmed title. The whole box is the click area. v0.3b: sized to the
//   15-px line, 9.5 pt bold, title text 2 px in (= a live.comment's text 2 px left of the box, D43).
// Text 9.5 pt from a 15-px line up, baseline (h + 8) >> 1 (face review §1.3).
// ES5 ONLY (see paint_kit.ts).

import { baselineOf, FONT_SIZE, fitText, roleOf, withAlpha, type Palette, type RGBA } from "./paint_kit.ts";
import { attrStr, currentPalette, dim, enableAutomationDots, font, isActive, measure, setColor, text, value, varnameOf } from "./paint_max.ts";

enableAutomationDots();

/** Power symbol (ring with a gap at the top and a short stem) centred at cx, cy; 9 px (user, D32). */
var POWER_R = 4.5;

function powerSymbol(cx: number, cy: number, on: boolean, active: boolean, p: Palette): void {
	var r = POWER_R;
	mgraphics.ellipse(cx - r, cy - r, 2 * r, 2 * r);
	if (on) {
		setColor(dim(p.sel, active, p));
		mgraphics.fill();
	} else {
		mgraphics.set_line_width(1);
		setColor(dim(p.track, active, p));
		mgraphics.stroke();
	}
	var g: RGBA = on ? p.selFg : p.track;
	setColor(dim(g, active, p));
	mgraphics.set_line_width(1.1);
	mgraphics.set_line_cap("round");
	// arc from 1 o'clock clockwise to 11 o'clock (Max arcs: radians, 0 = 3 o'clock, clockwise)
	mgraphics.arc(cx, cy, 2.3, -Math.PI / 2 + 0.75, Math.PI * 1.5 - 0.75);
	mgraphics.stroke();
	mgraphics.move_to(cx, cy - 3.1);
	mgraphics.line_to(cx, cy - 0.7);
	mgraphics.stroke();
}

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var on = value() > 0.5;
	var name = varnameOf();
	var label = attrStr(on ? "texton" : "text") || attrStr("text");

	var fs = h >= 15 ? FONT_SIZE : h >= 14 ? 9 : 8;
	var base = baselineOf(h);
	if (name.length > 3 && name.substring(name.length - 3) === "_on") {
		font(fs, true);
		var title = fitText(label, w - 18, measure);
		var tw = measure(title);
		text(title, 2, base, dim(on ? p.text : withAlpha(p.text, 0.45), active, p), "left");
		powerSymbol(Math.min(w - POWER_R - 0.5, Math.round(2 + tw + 4 + POWER_R) + 0.5), Math.round(h / 2) - 0.5, on, active, p);
		return;
	}

	var role = roleOf(name);
	var accent = role === "write" ? p.write : role === "read" ? p.read : p.sel;
	var rad = Math.min(h - 1, 16);
	if (on) {
		setColor(dim(accent, active, p));
		mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
		mgraphics.fill();
	}
	mgraphics.set_line_width(1);
	setColor(dim(on ? accent : p.track, active, p));
	mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
	mgraphics.stroke();
	font(fs, false);
	text(fitText(label, w - 6, measure), w / 2, base, dim(on ? p.selFg : p.text, active, p), "center");
}
