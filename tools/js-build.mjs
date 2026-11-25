#!/usr/bin/env node
// Bundle a device's TypeScript entries for Max's v8 / v8ui objects.
//
//   node tools/js-build.mjs DEVICE
//
// Entries are devices/<device>/js/src/<device>_*.ts (other files there are modules they import).
// Each entry becomes one flat CommonJS file devices/<device>/<entry>.js with a header naming its
// source (esbuild --bundle --format=cjs --platform=neutral --target=es2020). Tree shaking is
// off so that the message handlers - top-level function declarations that nothing in the code
// calls - survive; the script then checks that every top-level function of the entry is still a
// top-level `function NAME(` in the bundle (Max calls handlers by message name; whether
// handlers attached via globalThis are found is an open check, so they are not used).
// Type checking (tsc --noEmit) and the Node tests run before this, from package.json.
//
// Painters: entries named <device>_paint_*.ts are jspainter scripts (@jspainterfile on live.*
// objects). Which JS engine runs them in Live is not known for every Max version, so they are built
// with target es5: esbuild then fails on any syntax newer than ES5 (let/const, arrows, classes,
// template strings ...), which keeps the painters loadable by the legacy engine too.
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const device = process.argv[2];
if (!device || device.startsWith("-")) {
	console.error("Usage: node tools/js-build.mjs DEVICE");
	process.exit(2);
}
const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dir = join(root, "devices", device);
const src = join(dir, "js", "src");
const entries = readdirSync(src).filter((f) => f.startsWith(`${device}_`) && f.endsWith(".ts"));
if (entries.length === 0) {
	console.error(`js-build: no entries ${device}_*.ts in ${relative(root, src)}`);
	process.exit(2);
}

// Message names the v8 / v8ui / jsui box handles itself, so a JS handler of that name is never
// called (or gets the wrong arguments): the box methods from the refpages (Max 9.2,
// max-ref/{v8,v8ui,jsui}.maxref.xml) and box attributes, which are settable by message.
// Example: `size <float>` to a v8ui logs "missing arguments for message size" (aliasing B1).
// [hypothesis: every listed attribute name is intercepted; the methods are documented]
const RESERVED = new Set([
	// methods
	"size", "compile", "open", "wclose", "read", "getprop", "setprop", "delprop", "jsfile",
	"assiststr", "autowatch", "editfontsize", "statemessage", "jsargs",
	// box attributes (jbox + v8ui/jsui)
	"patching_rect", "presentation_rect", "patching_position", "patching_size",
	"presentation_position", "presentation_size", "presentation", "hidden", "ignoreclick",
	"varname", "background", "color", "fontname", "fontsize", "fontface", "textcolor",
	"textjustification", "hint", "annotation", "border", "filename", "jsarguments", "nofsaa",
	"parameter_enable", "parameter_mappable", "embed",
]);

let failed = false;
for (const file of entries) {
	const entry = join(src, file);
	const name = basename(file, ".ts");
	const out = join(dir, `${name}.js`);
	const header =
		`// GENERATED from devices/${device}/js/src/${file} by tools/js-build.mjs - do not edit.\n` +
		`// Edit the TypeScript source and run tools/check.sh ${device}.`;
	const painter = name.startsWith(`${device}_paint_`);
	let result;
	try {
		result = await build({
		entryPoints: [entry],
		bundle: true,
		format: "cjs",
		platform: "neutral",
		target: painter ? "es5" : "es2020",
		treeShaking: false,
		charset: "ascii",
		legalComments: "none",
		banner: { js: header },
		write: false,
		logLevel: "silent",
		});
	} catch (e) {
		console.error(`js-build: ${name}.ts failed to build${painter ? " as ES5 (painter)" : ""}:`);
		for (const m of e.errors ?? []) console.error(`  ${m.location?.file}:${m.location?.line}: ${m.text}`);
		failed = true;
		continue;
	}
	// Drop esbuild's "use strict" (added for ESM input): Max scripts assign jsthis globals such
	// as `inlets = 1` at top level and are written as sloppy-mode scripts.
	const code = result.outputFiles[0].text.replace(/^"use strict";\n/m, "");

	const handlers = [...readFileSync(entry, "utf8").matchAll(/^function\s+([A-Za-z_$][\w$]*)\s*\(/gm)].map((m) => m[1]);
	const missing = handlers.filter((h) => !new RegExp(`^function ${h.replace(/\$/g, "\\$")}\\(`, "m").test(code));
	if (/^export\s|^import\s/m.test(code)) {
		console.error(`js-build: ${name}.js still contains ESM syntax`);
		failed = true;
	}
	const reserved = handlers.filter((h) => RESERVED.has(h));
	if (reserved.length) {
		console.error(`js-build: ${name}.ts names handlers after built-in box messages: ${reserved.join(", ")}`);
		failed = true;
		continue;
	}
	if (missing.length) {
		console.error(`js-build: ${name}.js lost or renamed top-level handlers: ${missing.join(", ")}`);
		failed = true;
		continue;
	}
	let old = "";
	try {
		old = readFileSync(out, "utf8");
	} catch {}
	if (old === code) {
		console.log(`${name}.js unchanged (${handlers.length} top-level functions)`);
	} else {
		writeFileSync(out, code);
		console.log(`${name}.js written (${handlers.length} top-level functions)`);
	}
}
process.exit(failed ? 1 : 0);
