// aliasing_paint_menu: jspainter for the live.menus of the Aliasing face (mod slot Source/Target).
// Bundled (ES5) by tools/js-build.mjs into devices/aliasing/aliasing_paint_menu.js.
// A dark field with the item text and a small down triangle; "None" is drawn in the label colour.
// ES5 ONLY (see paint_kit.ts).

import { fitText } from "./paint_kit.ts";
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
	font(9, false);
	text(fitText(label, w - 18, measure), 6, h / 2 + 3, dim(k === 0 ? p.label : p.text, active, p), "left");
	setColor(dim(p.label, active, p));
	mgraphics.move_to(w - 11, h / 2 - 2);
	mgraphics.line_to(w - 4, h / 2 - 2);
	mgraphics.line_to(w - 7.5, h / 2 + 2);
	mgraphics.close_path();
	mgraphics.fill();
}
