import assert from "node:assert/strict";
import { test } from "node:test";

import { clampPage, visibilityFor } from "../src/pages_model.ts";

test("paged objects are visible only on their page", () => {
	assert.equal(visibilityFor("mod_wsym", 0), true);
	assert.equal(visibilityFor("mod_wsym", 1), false);
	assert.equal(visibilityFor("tone_hp", 1), true);
	assert.equal(visibilityFor("out_width", 2), true);
	assert.equal(visibilityFor("out_width", 0), false);
});

test("objects without a page prefix are left alone", () => {
	assert.equal(visibilityFor("display", 0), null);
	assert.equal(visibilityFor("model", 0), null);
	assert.equal(visibilityFor("", 0), null);
	assert.equal(visibilityFor(undefined, 0), null);
});

test("page numbers are clamped and rounded", () => {
	assert.equal(clampPage(-1), 0);
	assert.equal(clampPage(7), 2);
	assert.equal(clampPage(1.4), 1);
	assert.equal(clampPage(NaN), 0);
});
