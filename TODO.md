# TODO

Start here. Open items first, then the done log. Evidence markers as in `CLAUDE.md`.

## Next

- [ ] **aliasing t5 (user, in Live):** v0.3b, both faces side by side (`Aliasing.amxd` hybrid,
      `Aliasing B.amxd` option (b)) — handover 2026-11-25, `v0.3-design.md` §6b; the user picks the
      face that stays (then delete the other shell and its generator branch). Re-handed over after
      D46–D49 (user's first look: State drop-down, 918 px, menu dots, Clear). Includes the still open
      t3/t4 items: bundled Max 9.1.5 round, table storage, hot reload. Harness pre-check PASS (t5-auto).
- [x] aliasing t4 (v0.3, 9b1d5d7 + e0b2b59): the user looked at it in Live and sent screenshots and a
      critique instead of the checklist → face review, D33–D44, v0.3b (2026-11-25).
- [ ] **Live harness spike, rest (Claude + user):** L1, L3 done; first run on aliasing v0.3 (9b1d5d7)
      **PASS** in 19 s (testlog `t4-auto`: load, console, 173 parameters, silent take). Open: L2 on a
      real console error, L4 Main meter watched once by the user, L5 against a matched standalone
      render, L6 next normal Live start without a recovery dialog (user). The automation is **optional** (switch
      `node tools/live/harness.mjs on|off`, off on a fresh clone), codified as skill
      `live-harness`, hooked into `live-test` §1; `harness.mjs install` automates setup steps
      1, 2 and 5. Untested: `install` on a machine without the harness (only `--dry-run` here).
- [x] **aliasing:** the 9 `live.text` toggles showed "val1"/"val2" in Live; fixed 2026-11-25 by
      `automation`/`automationon` labels (generator + `check_shell.py` rule), Live now shows Off/On and
      1-Way/2-Way [measured: testlog `t4-auto-2`].
- [x] **aliasing:** `outputmode` Mouse Up on the toggle-mode `live.text` boxes (user, D38; v0.3b,
      `check_shell.py` rule).
- [ ] **aliasing review (user + Claude):** the v0.2 decisions A1–A33 (`docs/v0.2-build.md` §1) that
      v0.3 did not replace, and the mock-up's own decisions (`docs/mockup-v0.3/layout.md` §4–§5).
- [ ] aliasing v0.4: own presets (JSON + menu) incl. the v0.2 init sound (D1), `live.banks` for Push,
      CPU reading; remove the debug "ready" posts (A33) before a release.
- [ ] **aliasing (user, Reaktor):** optional simple-settings recording (R23: write ramp hi,
      In-Pitch 73, read −29.5, Size 0.08, LFOs off) to check Tri/Par Symm `W` and the anti-aliased
      ramp against `scripts/table_sim.py`; renders R1a, R1d, R7a–e from `renders.md`.

## User setup (hands-on, once)

- [x] Point Live at the standalone Max: done — Live 12.4.16 logs `Max: Version 9.2.1
      (b6a40ee953d)` since 2026-11-24 16:52 [measured: Live `Log.txt`]. Standalone Max is **9.2.1**.
- [x] max-gen-helper plugin installed (skill `max-gen-helper:gen-pitfalls` available, 2026-11-24).
- [x] Limiter on the test track/master for listening tests (user, 2026-11-24).
- [x] **Live test harness** set up 2026-11-25 (`tools/live/README.md` steps 1–6): clone at
      `ad756c1e` next to the repo, Remote Script link (absolute) in `~/Documents/Ableton/User
      Library`, Accessibility for the inner "Claude Code" app, Places entry for `devices/aliasing`;
      relaunch 4.8 s, doctor ok (32-bit float, 48 kHz), `record-roundtrip.js` PASS [measured: run
      output 2026-11-25].
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
| 1 | Live on Max 9.2 after the switch — any problems? (Log line `Max: Version`) — **answered:** v0.1 ran in Live with Max 9.2.1 (t1, testlog 2026-11-24) | development target |
| 2 | Does M4L in Live find `.gendsp`/`.js` next to the `.amxd`, and does a rewritten `.gendsp` hot-reload there (9.1.5 and 9.2), also inside 5 `poly~` instances? | the whole code-first loop |
| 3 | `@autoexport 1`: does gen~ re-export C++ when the `.gendsp` changes on disk, or only on edits in Max? What does the export folder contain? | host-test harness |
| 4 | Can standalone Max be launched from the command line with a test patch and run unattended (no dialogs), and does `; dsp setdriver NonRealTime` work by name? — **answered (yes/yes):** `tools/gen-export.sh`, `devices/aliasing/test/smoke/run_smoke.sh` (2026-11-25, Max 9.2.1; the driver is restored by name) | scripted renders |
| 5 | Do `post()` lines of a device appear in Live's `Log.txt`, or only errors? — partly: console errors of devices in Live go to `Max 9/Logs/MaxPlugLib.log` (t1); standalone Max's `Max.log` holds `post()` lines too (2026-11-25); `post()` in Live [open] (t3: the "v0.2 ready" lines) — **answered for MaxPlugLib.log:** in Live the device's `post()` lines appear there at level `info` ("aliasing_display: v0.2 ready" at 14:40:39 and 15:03:50) [measured: `MaxPlugLib.log` read 2026-11-25]; `tools/live/check-instrument.mjs` reads both logs | console without copy/paste |
| 6 | GenExpr: same-sample `poke`→`peek` order honoured (check exported C++); `poke` with fractional index; `peek` linear + wrap across the seam | table semantics |
| 7 | Do `Data`/`History` survive a sample-rate change or device reload in Live 12? | voice state |
| 8 | Live parameter resolution for very small speed changes (automation, MIDI map) — need coarse + fine controls? | "finest moves in speed" |
| 9 | v8: are handlers attached via `globalThis` called? (only when the TS layer comes) — not needed: js-build keeps top-level `function` handlers | TS build choice |
| 12 | jspainter engine and painted `live.*` in Live (Max 9.2.1 and bundled 9.1.5): paint, theme repaint, dots, map modes — standalone 9.2.1 runs jspainter on the **legacy (ES5) engine** [measured: smoke 2026-11-25] | aliasing v0.2 face |
| 10 | Does freezing include `require`d `.genexpr` files; does the frozen device run in a fresh set on stock Live 9.1.5? | release gate |
| 11 | Does a py2max-generated `.amxd` load in Live? (only if a generated shell is ever wanted) | generated shells |

## Done

- 2026-11-25: Max MCP and Ableton MCPs re-evaluated (`docs/research/notes/live-automation-mcp-2026-11-25.md`):
  no Max MCP; for Live the test harness eladefrati/ableton-live-test-harness (pinned `ad756c1e`,
  source read). Built as an **optional** Live automation: `CLAUDE.md` exception "Live test harness"
  (only while switched on), skill `live-harness` (hooked into `live-test`), `tools/live/`
  (`harness.mjs` status/install/on/off/run, `check-instrument.mjs`, README with install and spike
  checks L1–L6). Set up and run on aliasing v0.3 the same day (testlog `t4-auto`, `t4-auto-2`).
- 2026-11-25 (with the user): t3 report logged (v0.2 in Live 12.4.16 / Max 9.2.1, critique + 3
  screenshots, `testlog/aliasing/2026-11-25.md`); grilling rounds 1–3 → v0.3 design D1–D30
  (`devices/aliasing/docs/v0.3-design.md`); v0.3 built offline: DSP (8 write shapes, Freeze/Write/
  Clean, 9 × 12 mod matrix with Voice/Neighbour/Read Osc/Env, section switches, color limiter, follower
  outlet), display (zoom to Size with per-voice edges, filled band), painters (2 × 4 icon grid, matrix
  cells, title switches, v0.3 palette), pages (Sym labels, greying, panel colours from live.colors),
  mock-up v0.3 (Design canvas v17 + `docs/mockup-v0.3/`), shell generator + checker v0.3, canvas
  preview. Shell written to the device folder after the user approved the face, committed as 9b1d5d7.

- 2026-11-25: Google's Elephant-Goldfish Model evaluated, not installed; own skill
  `fresh-review` (+ read-only agent `fresh-reviewer`, reports in `docs/reviews/`, local) built
  instead.
- 2026-11-25 (unattended session, decisions A1–A33 for review in `devices/aliasing/docs/v0.2-build.md`):
  aliasing **v0.1b** (P1/P2: Write Pitch −64…130, init state at fs/3 + 4 Hz; commit a3f0466) and
  **v0.2** built: DSP (Drone/MIDI gate, tempo-synced pointers with note values, multiplier,
  detune and Resync, 2 LFOs, 4 mod slots, Drive → Band → Resonator → Clip, Tri ±, AA ramp; host
  test 39/39), face (6 ES5 jspainter painters, new v8ui display with lanes, zoom, drawing, table
  storage, tone curve with handles; page switcher), shell regenerated (968 px, 67 parameters),
  `scripts/check_shell.py`, Node vm tests, smoke test in standalone Max 9.2.1 (no errors, audio
  rendered) and a canvas preview. t2 (probe) not run, folded into t3.
- 2026-11-24: aliasing v0.1 built and tested in Live (t1), bug B1 fixed, redesign decided
  (R1–R24, approved mock-up), probe device for t2.
- 2026-11-24: aliasing GUI approved: interactive 1:1 HTML mock-up (834 × 169 px, dark/light,
  pages Mod/Tone/Out, display Line/2D/off) reviewed by the user; voice lines changed to a grey
  ramp on request. Layout, element → Max object map and presentation rects in
  `devices/aliasing/docs/gui.md` (open GUI checks G1–G7 there).
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
