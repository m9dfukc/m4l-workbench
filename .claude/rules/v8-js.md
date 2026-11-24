---
paths:
  - "devices/**/js/**"
  - "devices/**/*.js"
  - "devices/**/*.ts"
  - "package.json"
  - "tsconfig*.json"
---

# v8 JavaScript (from TypeScript)

Control logic only: parameter mapping, presets/dicts, Live API (`LiveAPI`), UI glue. **Never
audio-rate work** — `v8`/`js` run in Max's low-priority thread and jitter.

- Add the TS layer only when a device needs logic Max objects cannot do cleanly (presets,
  table management, UI text). The toolchain is set up then, project-local: `pnpm add -D
  typescript esbuild @types/maxmsp` (`@types/maxmsp` is the only typings package for the Max JS
  API; `@types/max-api` is for Node for Max, not v8). A root `package.json` script
  `build:<device>` is what `tools/check.sh` runs.
- Sources: `devices/<name>/js/src/*.ts` → CommonJS JS flat in `devices/<name>/`, committed with
  a header naming its source; never edit the output by hand. Two options, decide with the
  first device: plain `tsc` (`module: commonjs`, `target: es2020`, one file per module, Max's
  `require` loads siblings — no tree-shaking risk), or esbuild `--bundle --format=cjs
  --platform=neutral --target=es2020` (one file, inlines npm deps). Run `tsc --noEmit` either
  way (esbuild does not type-check). Do **not** take code from `zsteinkamp/m4l-typescript-base`
  (GPL-3.0, targets legacy `js`).
- v8 supports CommonJS `require`, **not** ESM `import` at runtime; legacy `js` is ES5 — use
  `v8` for new code.
- Max calls **global functions by message name** (`bang`, `msg_int`, `msg_float`, `list`,
  `anything`, custom names); `fn.local = 1` hides one. After bundling they must be global:
  whether handlers attached via `globalThis.<name> = fn` are found by v8 is [open] — test it
  once in Max before relying on it; otherwise keep top-level `function` declarations.
- Never name a handler after a message the box handles itself (`size`, `open`, `read`,
  `hidden`, `presentation_rect`, …): v8ui swallows `size <float>` with "missing arguments for
  message size" (aliasing B1). `tools/js-build.mjs` rejects the names in its `RESERVED` list.
- Code that must run in stock Live (Max 9.1.5) must not rely on 9.2-only v8 APIs (timers,
  `fetch`, `MaxFFT`); use `Task` for scheduling.
- Declare `inlets`/`outlets` (and `autowatch = 1` during development) at top level.
- No DOM, no Node APIs (Node lives in `node.script`, a different object). Max 9.2's v8 has
  native fetch/WebSocket, but keep devices offline unless a device needs it.
- `---` device-local names are not substituted inside JS strings: receive such names by
  message from the patch.
- Pure logic goes into modules without Max globals so it can be unit-tested in Node; keep
  the thin Max-facing layer (`post`, `outlet`, `Dict`, `Buffer`, `LiveAPI`) separate.
- Tests send real values (no `int 60` message-box shortcuts).
