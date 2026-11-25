// aliasing_paint_tab: jspainter for every live.tab of the Aliasing face (R5, R12, D4, D5).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_tab.js.
// A pill-shaped segmented control as in the mock-up: rounded frame, the selected segment filled. A tab
// with several rows (num_lines_presentation, e.g. the 2 x 4 Write Shape grid) is drawn as a grid,
// items row by row [hypothesis: live.tab lays out and hit-tests its items row by row; t4 check].
// Shape labels are drawn as waveform icons (write shapes as write-head paths on w_shape, LFO and
// read shapes as waveforms; stroke 1.1 px, points on pixel centres), everything else as text
// (v0.3b: 9.5 pt from a 15-px line up, baseline (h + 8) >> 1, D43). ES5 ONLY (see paint_kit.ts).

import { baselineOf, FONT_SIZE, fitText, iconPath } from "./paint_kit.ts";
import { attrNum, currentPalette, dim, enableAutomationDots, font, isActive, measure, paramInfo, polyline, setColor, text, value, varnameOf } from "./paint_max.ts";

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
	// draw the rows Max hit-tests: with multiline 0 live.tab ignores num_lines (one row)
	var lines = attrNum("multiline", 1) !== 0 ? attrNum("num_lines_presentation", 1) : 1;
	var rows = Math.max(1, Math.min(n, Math.round(lines)));
	var cols = Math.ceil(n / rows);
	var segw = (w - 1) / cols;
	var segh = (h - 1) / rows;
	var family = varnameOf() === "w_shape" ? "write" : "";
	var hasIcons = iconPath(labels[0], family) !== null;
	var rad = rows > 1 || hasIcons ? 8 : Math.min(h - 1, 16);

	// selected segment: in a single row rounded at the pill's ends and square towards its neighbours;
	// in a grid a small rounded cell
	setColor(dim(p.sel, active, p));
	if (sel >= 0 && sel < n) {
		var sr = Math.floor(sel / cols);
		var sc = sel % cols;
		var x0 = 0.5 + sc * segw;
		var y0 = 0.5 + sr * segh;
		if (rows > 1 || hasIcons) {
			mgraphics.rectangle_rounded(x0 + 1, y0 + 1, segw - 2, segh - 2, 6, 6);
			mgraphics.fill();
		} else if (n === 1 || sel === 0 || sel === n - 1) {
			mgraphics.rectangle_rounded(x0, 0.5, segw, h - 1, rad, rad);
			mgraphics.fill();
			if (n > 1) {
				mgraphics.rectangle(sel === 0 ? x0 + segw / 2 : x0, 0.5, segw / 2, h - 1);
				mgraphics.fill();
			}
		} else {
			mgraphics.rectangle(x0, 0.5, segw, h - 1);
			mgraphics.fill();
		}
	}
	// frame and separators
	mgraphics.set_line_width(1);
	setColor(dim(p.track, active, p));
	mgraphics.rectangle_rounded(0.5, 0.5, w - 1, h - 1, rad, rad);
	mgraphics.stroke();

	font(segh < 13 ? 8 : segh < 14 ? 9 : FONT_SIZE, false);
	var base = baselineOf(segh);
	for (var i = 0; i < n; i++) {
		var on = i === sel;
		var fg = dim(on ? p.selFg : p.text, active, p);
		var cx = 0.5 + segw * ((i % cols) + 0.5);
		var cy = 0.5 + segh * (Math.floor(i / cols) + 0.5);
		var icon = iconPath(labels[i], family);
		if (icon) {
			var iw = Math.min(segw - 6, 22);
			var ih = Math.min(segh - 5, 12);
			mgraphics.set_line_width(1.1);
			mgraphics.set_line_join("round");
			setColor(on ? fg : dim(p.label, active, p));
			// icon points 1..21 x 1..11 onto pixel centres (face review §2)
			polyline(icon, Math.round(cx - iw / 2) + 0.5 - (iw - 1) / 20, Math.round(cy - ih / 2) + 0.5 - (ih - 1) / 10,
				(iw - 1) / 20, (ih - 1) / 10);
			mgraphics.stroke();
		} else {
			var s = fitText(labels[i], segw - 2, measure);
			text(s, cx, 0.5 + segh * Math.floor(i / cols) + base, fg, "center");
		}
	}
}
