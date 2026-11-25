// aliasing_paint_cell: jspainter for the mod matrix cells (live.numbox mod_<source>_<target>, D25, D36;
// face review §7 "cell painter"). Bundled (ES5) by tools/js-build.mjs into
// devices/aliasing/aliasing_paint_cell.js. ES5 ONLY (see paint_kit.ts).
// - Depth 0: a quiet slot (light #8c8c8c / dark #393939, radius 2, no tick), so empty cells are the
//   calmest thing on the page; in a 15-px strip box (option (b)) it shows a dim "0".
// - Depth != 0: the field colour with the depth as text ("+35", "-40") and a 2-px bar from the centre
//   along the bottom edge in the target's accent (write graphite, read blue, D39) over a 1-px hairline.

import { accentFor, baselineOf, clamp, FONT_SIZE, mixColor, roleOf } from "./paint_kit.ts";
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
	var used = Math.abs(Math.round(v)) >= 1 || Math.abs(n) > 0.004;
	var strip = h >= 15;

	setColor(dim(used ? p.field : p.slot, active, p));
	mgraphics.rectangle_rounded(0, 0, w, h, strip ? 6 : 4, strip ? 6 : 4);
	mgraphics.fill();
	font(strip ? FONT_SIZE : 9, false);
	var base = strip ? baselineOf(h) - 1 : h - 3;
	if (!used) {
		if (strip) text("0", w / 2, base + 1, dim(mixColor(p.slot, p.label, 0.55), active, p), "center");
		return;
	}
	var c = Math.round(w / 2);
	var x = c + n * (w / 2 - 1);
	setColor(dim(mixColor(p.field, p.label, 0.2), active, p));
	mgraphics.rectangle(2, h - 2, w - 4, 1);
	mgraphics.fill();
	setColor(dim(accentFor(roleOf(varnameOf()), p), active, p));
	mgraphics.rectangle(Math.min(c, x), h - 3, Math.max(1, Math.abs(x - c)), 2);
	mgraphics.fill();
	var s = (n > 0 ? "+" : "−") + Math.round(Math.abs(v));
	text(s, w / 2, base, dim(p.text, active, p), "center");
}
