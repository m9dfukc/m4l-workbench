---
paths:
  - "devices/**/js/**"
  - "devices/**/*.js"
  - "devices/**/*.ts"
  - "tools/js-build.mjs"
  - "package.json"
---

# v8 JavaScript (from TypeScript)

Control logic only: parameter mapping, presets/dicts, Live API (`LiveAPI`), UI glue and painting.
**Never audio-rate work** — `v8`/`js` run in Max's low-priority thread and jitter.

## Build

- Sources: `devices/<name>/js/src/*.ts`. Every `<name>_*.ts` there is an **entry**; the other
  files are modules the entries import. `pnpm run build:<name>` (run by `tools/check.sh`)
  type-checks with `tsc` (esbuild does not), runs the Node tests in `js/test/*.test.ts`, then
  `tools/js-build.mjs` bundles each entry with esbuild into one flat CommonJS file
  `devices/<name>/<entry>.js`, committed, with a header naming its source. Never edit the output
  by hand.
- **Painters** (`<name>_paint_*.ts`, a `jspainterfile` of `live.*` objects) are built with target
  **es5**: jspainter runs on Max's legacy JS engine [measured: smoke test in standalone Max 9.2.1,
  2026-11-25]. No `let`/`const`, arrows, classes or template strings there; the build fails on
  them. Everything else is es2020 for `v8`/`v8ui`.
- A new entry is a new runtime file: list it in the shell's device project, or Freeze does not
  embed it (`max-patch.md`).
- Typings: `@types/maxmsp` (`@types/max-api` is for Node for Max, not v8). Do **not** take code
  from `zsteinkamp/m4l-typescript-base` (GPL-3.0, targets legacy `js`).

## Rules for the code

- Max calls **global functions by message name** (`bang`, `msg_int`, `msg_float`, `list`,
  `anything`, custom names); `fn.local = 1` hides one. Write handlers as **top-level `function`
  declarations** in the entry: the build keeps tree shaking off and checks that each one is still
  top-level in the bundle. Handlers attached via `globalThis.<name> = fn` are not used (never
  verified in Max).
- Never name a handler after a message the box handles itself (`size`, `open`, `read`,
  `hidden`, `presentation_rect`, …): v8ui swallows `size <float>` with "missing arguments for
  message size" (aliasing B1). `tools/js-build.mjs` rejects the names in its `RESERVED` list.
- v8 supports CommonJS `require`, **not** ESM `import` at runtime (the bundle takes care of it);
  use `v8`, not legacy `js`, for new code.
- Code that must run in stock Live (Max 9.1.5) must not rely on 9.2-only v8 APIs (timers,
  `fetch`, `MaxFFT`); use `Task` for scheduling.
- Declare `inlets`/`outlets` at top level; `autowatch = 1` only during development (a release
  ships without it).
- No DOM, no Node APIs (Node lives in `node.script`, a different object). Max 9.2's v8 has
  native fetch/WebSocket, but keep devices offline unless a device needs it.
- `---` device-local names are not substituted inside JS strings: receive such names by
  message from the patch.
- Pure logic goes into modules without Max globals so it can be unit-tested in Node; keep
  the thin Max-facing layer (`post`, `outlet`, `Dict`, `Buffer`, `LiveAPI`) separate.
- Tests send real values (no `int 60` message-box shortcuts).
