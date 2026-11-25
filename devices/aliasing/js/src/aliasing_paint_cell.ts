// aliasing_paint_cell: jspainter for the mod matrix cells (live.numbox mod_<source>_<target>, D10,
// D25): a small field with a bipolar bar from the centre, coloured by the target's role (write / read
// / neutral), and the depth as text while it is not 0, so the used cells stand out.
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_cell.js. ES5 ONLY (see
// paint_kit.ts).

import { accentFor, clamp, roleOf, withAlpha } from "./paint_kit.ts";
import { currentPalette, dim, enableAutomationDots, font, isActive, paramInfo, setColor, text, value, varnameOf } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var v = value();
	var span = Math.max(Math.abs(info.lo), Math.abs(info.hi), 1e-9);
	var n = clamp(v / span, -1, 1);
	var accent = accentFor(roleOf(varnameOf()), p);

	setColor(dim(p.field, active, p));
	mgraphics.rectangle_rounded(0, 0, w, h, 3, 3);
	mgraphics.fill();
	// centre tick
	setColor(dim(withAlpha(p.label, 0.35), active, p));
	mgraphics.rectangle(Math.round(w / 2) - 0.5, 2, 1, h - 4);
	mgraphics.fill();
	if (Math.abs(n) > 0.004) {
		var c = w / 2;
		var x = c + n * (w / 2);
		setColor(dim(withAlpha(accent, 0.55), active, p));
		mgraphics.rectangle(Math.min(c, x), 1, Math.abs(x - c), h - 2);
		mgraphics.fill();
		font(h <= 12 ? 7.5 : 8, false);
		var s = (n > 0 ? "+" : "\u2212") + Math.round(Math.abs(v));
		text(s, w / 2, h / 2 + 3, dim(p.text, active, p), "center");
	}
}
