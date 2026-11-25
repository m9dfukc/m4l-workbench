// aliasing_paint_tab: jspainter for every live.tab of the Aliasing face (R5, R12).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_tab.js.
// A pill-shaped segmented control as in the mock-up: rounded frame, the selected segment filled.
// Shape labels (Ramp, Tri, Tri +-, =Read, Sine, Saw, Square, S&H, Random) are drawn as waveform
// icons, everything else as text. ES5 ONLY (see paint_kit.ts).

import { fitText, iconPath } from "./paint_kit.ts";
import { currentPalette, dim, enableAutomationDots, font, isActive, measure, paramInfo, polyline, setColor, text, value } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var labels = info.labels || ["0", "1"];
	var n = labels.length;
	var sel = Math.round(value());
	var seg = (w - 1) / n;
	var rad = Math.min(h - 1, 16);

	// selected segment: rounded at the pill's ends, square towards its neighbours
	setColor(dim(p.sel, active, p));
	if (sel >= 0 && sel < n) {
		var x0 = 0.5 + sel * seg;
		if (n === 1 || sel === 0 || sel === n - 1) {
			mgraphics.rectangle_rounded(x0, 0.5, seg, h - 1, rad, rad);
			mgraphics.fill();
			if (n > 1) {
				mgraphics.rectangle(sel === 0 ? x0 + seg / 2 : x0, 0.5, seg / 2, h - 1);
				mgraphics.fill();
			}
		} else {
			mgraphics.rectangle(x0, 0.5, seg, h - 1);
			mgraphics.fill();
		}
	}
	// frame and separators
	mgraphics.set_line_width(1);
	setColor(dim(p.track, active, p));
	mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
	mgraphics.stroke();

	font(h <= 14 ? 8 : 9, false);
	for (var i = 0; i < n; i++) {
		var on = i === sel;
		var fg = dim(on ? p.selFg : p.text, active, p);
		var cx = 0.5 + seg * (i + 0.5);
		var icon = iconPath(labels[i]);
		if (icon) {
			var iw = Math.min(seg - 6, 22);
			var ih = Math.min(h - 6, 12);
			mgraphics.set_line_width(1.4);
			mgraphics.set_line_join("round");
			setColor(on ? fg : dim(p.label, active, p));
			polyline(icon, cx - iw / 2, h / 2 - ih / 2, iw / 22, ih / 12);
			mgraphics.stroke();
		} else {
			var s = fitText(labels[i], seg - 4, measure);
			text(s, cx, h / 2 + 3, fg, "center");
		}
	}
}
