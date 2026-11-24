# TODO

Start here. Open items first, then the done log. Evidence markers as in `CLAUDE.md`.

## Next

- [ ] **aliasing:** start the port in a new session with the `reaktor-port` skill: inventory
      from the original 2008 ensemble + screenshots (`docs/research/notes/aliasing-synth-sources-2026-11-24.md`
      already has a first one), capture list for the user, reference renders, signal-flow doc,
      port decisions (voice layer: `poly~` + gen~ recommended; precision; control-rate emulation),
      then the first GenExpr voice with a host test.
- [ ] **aliasing:** time-boxed spike: local read-only parser (`tools/local/`, gitignored) for the 2008 `.ens` record stream
      (modules, type IDs, names, values, ports) + type-ID table from test instruments the user
      saves in Reaktor 6 (one known module each). Plan: `docs/research/notes/reaktor-file-parsers-2026-11-24.md`.

## User setup (hands-on, once)

- [ ] Point Live at the standalone **Max 9.2**: Live Settings → File & Folder → Max Application
      → Browse → `/Applications/Max.app`, restart Live. Claude confirms via the `Max: Version`
      line in Live's `Log.txt`.
- [ ] Install the max-gen-helper plugin in Claude Code (decided 2026-11-24; skill
      `gen-pitfalls` + a guard hook that asks before Max files outside the repo are changed):
      `/plugin marketplace add mforhm/max-gen-helper`, then `/plugin install max-gen-helper@mforhm`.
- [ ] Limiter on the test track/master for listening tests.
- [ ] Read Cycling '74's "Gen Code Export Licensing FAQ" (the research agent got HTTP 403) before
      any exported gen~ C++ is committed or published.

## aliasing: to capture in Reaktor (user)

From the research notes; the `reaktor-port` session turns this into a precise capture list.

- [ ] Settings snapshot: sample-rate display (file suggests Fixed 48 kHz), Control Rate (file
      suggests 400 Hz), BPM, voices / unison / assign mode.
- [ ] Audio Table Properties: size, units, Min/Max, interpolation, clip/wrap, stored contents.
- [ ] Ramp oscillator mode of each pointer (Standard / Anti-Aliased / Hi-Res); whether the
      triangle pointer is band-limited.
- [ ] All knob ranges and defaults, the "size bar" range; identity of the unnamed "S" and "M" boxes.
- [ ] "Z" feedback-delay markers (Debug Structure → Show Module Sorting).
- [ ] Whether two identical renders null (determinism).
- [ ] Optional: save the full dogsonacid thread from a browser (blocked for automated fetches).
- [ ] Licence: ask Dietrich Pank about publishing the port before any public release.

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

- 2026-11-24: Workbench set up from the user's Rings workbench template: CLAUDE.md, rules
  (`gen.md`, `max-patch.md`, `v8-js.md`), skills (`live-test`, `reaktor-port`, `m4l-release`;
  kept `grill-me`/`grilling`/`handoff`/`research`), git repo, `.gitattributes` + maxdiff
  textconv, vendored gencheck/maxdiff/references (`tools/vendor/VENDOR.md`), uv tools project
  (`m4l-analyze`), `tools/check.sh` (verified on a throwaway device). Research notes on the
  toolchain, Reaktor and porting, Max port targets, and the Aliasing Synth sources.
- 2026-11-24: `m4l-boxref` replaces the hand-built reference device: it finds real Max-saved
  boxes (e.g. 5 239 `live.dial`, 1 304 `live.menu`, 539 `gen~`, 227 `poly~`, some saved by Max
  9.2.0) in ~7 300 patch files of the local Max/Live installation [measured].
