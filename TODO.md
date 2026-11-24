# TODO

Start here. Open items first, then the done log. Evidence markers as in `CLAUDE.md`.

## Next

- [ ] **aliasing:** true-to-scale HTML mock-up of the GUI (169 px height, ~800–850 px, display in
      the centre, paged right area) for the user's review — `devices/aliasing/docs/port-decisions.md` §3.
- [ ] **aliasing v0.1 core:** GenExpr voice loop (`gen/aliasing.genexpr`, 5 voices, `Buffer`
      `---atab` 5×1024, pointers, Sync/Activate/MIDI gate, Size, Smooth, pan, safety stage),
      host test from exported C++, TS toolchain (esbuild + `tsc --noEmit`) for the `v8ui`
      display, shell `Aliasing.amxd`; then `live-test`. Decisions: `port-decisions.md`.
- [ ] **aliasing (user, Reaktor):** captures C4 (Audio Table properties) and C6 (Ramp Osc mode)
      from `devices/aliasing/docs/captures.md`; renders R1a, R1d, R7a–e from `renders.md`.

## User setup (hands-on, once)

- [x] Point Live at the standalone Max: done — Live 12.4.16 logs `Max: Version 9.2.1
      (b6a40ee953d)` since 2026-11-24 16:52 [measured: Live `Log.txt`]. Note: standalone Max is
      now **9.2.1** (CLAUDE.md still says 9.2.0).
- [x] max-gen-helper plugin installed (skill `max-gen-helper:gen-pitfalls` available, 2026-11-24).
- [x] Limiter on the test track/master for listening tests (user, 2026-11-24).
- [ ] Read Cycling '74's "Gen Code Export Licensing FAQ" (the research agent got HTTP 403) before
      any exported gen~ C++ is committed or published.

## aliasing: to capture in Reaktor (user)

Superseded by `devices/aliasing/docs/captures.md` (needed: C4, C6) and `renders.md` (needed:
R1a, R1d, R7a–e); the parser covers ranges, defaults, snapshots and wiring. Still open here:

- [ ] Optional: save the full dogsonacid thread from a browser (blocked for automated fetches).
- [ ] Before a public release: tell/ask Dietrich Pank (nice to have, port-decisions Q21).

## Open checks in Max/Live

Answer these with the first `live-test` sessions; each needs a log reference when closed.

| # | Check | Why |
|---|---|---|
| 1 | Live on Max 9.2 after the switch — any problems? (Log line `Max: Version`) | development target |
| 2 | Does M4L in Live find `.gendsp`/`.js` next to the `.amxd`, and does a rewritten `.gendsp` hot-reload there (9.1.5 and 9.2), also inside 5 `poly~` instances? | the whole code-first loop |
| 3 | `@autoexport 1`: does gen~ re-export C++ when the `.gendsp` changes on disk, or only on edits in Max? What does the export folder contain? | host-test harness |
| 4 | Can standalone Max be launched from the command line with a test patch and run unattended (no dialogs), and does `; dsp setdriver NonRealTime` work by name? | scripted renders |
| 5 | Do `post()` lines of a device appear in Live's `Log.txt`, or only errors? | console without copy/paste |
| 6 | GenExpr: same-sample `poke`→`peek` order honoured (check exported C++); `poke` with fractional index; `peek` linear + wrap across the seam | table semantics |
| 7 | Do `Data`/`History` survive a sample-rate change or device reload in Live 12? | voice state |
| 8 | Live parameter resolution for very small speed changes (automation, MIDI map) — need coarse + fine controls? | "finest moves in speed" |
| 9 | v8: are handlers attached via `globalThis` called? (only when the TS layer comes) | TS build choice |
| 10 | Does freezing include `require`d `.genexpr` files; does the frozen device run in a fresh set on stock Live 9.1.5? | release gate |
| 11 | Does a py2max-generated `.amxd` load in Live? (only if a generated shell is ever wanted) | generated shells |

## Done

- 2026-11-24: aliasing port prepared: local read-only `.ens` parser (`tools/local/`, decodes the
  full module tree 326/326, wiring, ranges, snapshots, table data; type-ID table from structure +
  screenshots, no test instruments needed), `devices/aliasing/docs/` `inventory.md`,
  `signal-flow.md`, `captures.md`, `renders.md`, `port-decisions.md` (grilling Q1–Q21: "inspired
  by", drone with 5 voices in one gen~, per-sample, float32 table `buffer~` shared with a `v8ui`
  display, own filters/presets, esbuild).

- 2026-11-24: Workbench set up from the user's Rings workbench template: CLAUDE.md, rules
  (`gen.md`, `max-patch.md`, `v8-js.md`), skills (`live-test`, `reaktor-port`, `m4l-release`;
  kept `grill-me`/`grilling`/`handoff`/`research`), git repo, `.gitattributes` + maxdiff
  textconv, vendored gencheck/maxdiff/references (`tools/vendor/VENDOR.md`), uv tools project
  (`m4l-analyze`), `tools/check.sh` (verified on a throwaway device). Research notes on the
  toolchain, Reaktor and porting, Max port targets, and the Aliasing Synth sources.
- 2026-11-24: `m4l-boxref` replaces the hand-built reference device: it finds real Max-saved
  boxes (e.g. 5 239 `live.dial`, 1 304 `live.menu`, 539 `gen~`, 227 `poly~`, some saved by Max
  9.2.0) in ~7 300 patch files of the local Max/Live installation [measured].
