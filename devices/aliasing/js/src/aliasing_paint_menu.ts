// aliasing_paint_menu: jspainter for the live.menus of the Aliasing faces (option (b): the modulation
// strip's target menu, D36).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_menu.js.
// A field with the item text and a small down triangle. An item ending in " \u2022" (a modulated target,
// set by the pages script, D48) is drawn as its name and a filled dot in the read accent.
// ES5 ONLY (see paint_kit.ts).

import { baselineOf, FONT_SIZE, fitText } from "./paint_kit.ts";
import { currentPalette, dim, enableAutomationDots, font, isActive, measure, paramInfo, setColor, text, value } from "./paint_max.ts";

enableAutomationDots();

function paint(): void {
	var w = mgraphics.size[0];
	var h = mgraphics.size[1];
	var p = currentPalette();
	var active = isActive();
	var info = paramInfo();
	var labels = info.labels || [];
	var k = Math.round(value());
	var label = k >= 0 && k < labels.length ? labels[k] : String(k);

	setColor(dim(p.field, active, p));
	mgraphics.rectangle_rounded(0, 0, w, h, 6, 6);
	mgraphics.fill();
	font(h >= 15 ? FONT_SIZE : 9, false);
	var marked = label.length > 2 && label.substring(label.length - 2) === " \u2022";
	if (marked) label = label.substring(0, label.length - 2);
	var shown = fitText(label, w - (marked ? 26 : 18), measure);
	text(shown, 5, baselineOf(h), dim(p.text, active, p), "left");
	if (marked) {
		setColor(dim(p.read, active, p));
		mgraphics.ellipse(Math.round(5 + measure(shown) + 4), Math.round(h / 2) - 2, 4, 4);
		mgraphics.fill();
	}
	setColor(dim(p.label, active, p));
	mgraphics.move_to(w - 11, h / 2 - 2);
	mgraphics.line_to(w - 4, h / 2 - 2);
	mgraphics.line_to(w - 7.5, h / 2 + 2);
	mgraphics.close_path();
	mgraphics.fill();
}
