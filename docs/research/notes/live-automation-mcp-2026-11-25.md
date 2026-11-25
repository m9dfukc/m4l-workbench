# Automating the Live test loop: Max MCP, Ableton MCP or a test harness? (2026-11-25)

Question (user, 2026-11-25): is a Max MCP server worth it now, would an Ableton MCP server help,
and how far can the process be automated? Starting points: `Max for Live mit Claude bauen.md`
(tool data of 2026-11-19), `m4l-toolchain-dependencies-2026-11-24.md` §5 and §8 ("postpone every
MCP and the Live harness until a device exists"). A device now exists: aliasing v0.2, built and
smoke-tested in standalone Max, not yet loaded in Live (t3).

**Evidence markers** as in `CLAUDE.md`. Repo activity from the GitHub REST API on 2026-11-25
[measured: API]. Nothing was installed for this note.

## Summary

- **Max MCP: still no.** No Max-side MCP server has changed since the guide: ersatzben
  2026-07-10, signalcompose 2026-07-14, gluon 2026-06-10, miravassor 2026-05-25, DCsLostBoy
  (the only `.amxd` lifecycle) one commit of 2026-09-22 [measured: API]. A GitHub search for
  repos created since 2026-11-15 found no new Max MCP and no Node-free v8 bridge inside a
  device [measured: API search]. The guide's reasons hold (one tool call per object, fragile
  bridges, no `.amxd` save, no parameter metadata, no access to gen~ internals). What a Max MCP
  would give us (compile with audio on, console) we already get from the unattended
  standalone-Max runs (`run_smoke.sh`, `gen-export.sh`, `Max.log`). The one real gap, reading
  what a device shows inside Live, is better closed by a test hook in development builds (below).
- **Ableton MCP for building: no; for testing: a test harness, not an MCP.** The value on the
  Live side is the t-test loop (load, console, parameters, audio), which wants reproducible
  scripted checks with PASS/FAIL and a log, not a chat-driven tool box.
  **eladefrati/ableton-live-test-harness** does exactly that and is the recommended candidate
  for a spike; Producer Pal is the best general Ableton MCP but has no recording; bschoepke and
  Extensions-based servers are out (below).
- **What stays with the user:** listening and taste, A/B against Reaktor, the round on Live's
  bundled Max 9.1.5 (switching Max in Live's settings), the freeze, Reaktor renders.

## Candidates on the Live side

| Tool | State 2026-11-25 | For our loop | Verdict |
|---|---|---|---|
| [eladefrati/ableton-live-test-harness](https://github.com/eladefrati/ableton-live-test-harness) | MIT, created 2026-11-09, 0★, >100 commits, last `ad756c1e` 2026-11-23, one author, macOS only [measured: API] | Built for "coding agents" running in-Live acceptance tests of M4L devices; details below [sourced: README] | **Spike candidate.** Young and churning: pin a commit |
| [adamjmurray/producer-pal](https://github.com/adamjmurray/producer-pal) | MIT, 393★, pushed 2026-11-25, v2.5.0 stable, v2.6.0-rc1 [measured: API] | MCP + REST from an `.amxd`; its remote script loads M4L devices and presets by name, also from Places (v2.4/v2.5); clips, notes, automation, parameters [sourced: release notes]. No audio capture in the device; audio export/analysis are separate example skills [sourced: repo tree] | Best general Ableton MCP; for interactive set work later, not for the test loop |
| [bschoepke/ableton-live-mcp](https://github.com/bschoepke/ableton-live-mcp) | 238★, last push 2026-10-06 [measured: API] | Arbitrary Python inside Live, Agent Audio Tap [sourced: README] | No: high blast radius, idle since October |
| [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) and its many forks | 3 445★, last push 2026-09-22; a dozen new forks since 2026-11-19 [measured: API] | Set control for music making | No: nothing for tests |
| [ulm0/ableton-live-mcp](https://github.com/ulm0/ableton-live-mcp) and other Extensions | — | Need the Extensions SDK | Out: the SDK runs only in the **Live 12.4 Suite public beta** [sourced: [ableton.com/live/extensions](https://www.ableton.com/en/live/extensions), [SDK docs](https://ableton.github.io/extensions-sdk)]; the user runs the release 12.4.16 |

## The test harness in detail [sourced: README, `harness/README.md`, `skills/verify-ableton/SKILL.md`, ADR-0002]

- A fork of AbletonOSC (MIDI Remote Script), symlinked into Live's Remote Scripts as
  `AbletonOSC`, selected in a Control Surface slot; exposes the LOM over OSC on 127.0.0.1:11000.
  Node ≥ 18 client, no npm packages.
- `relaunch.js` quits Live and starts it on a fresh copy of `sets/empty.als`: one MIDI track,
  nothing on Main, **Main at −inf dB, "so runs are silent"; recordings take the tracks' Post FX,
  before Main**. It answers "Save changes?" with Don't Save, moves recovery data aside so Live
  does not ask to recover, and stops at any unknown dialog. `quit.js` likewise.
- Loads a build from Live's **Places** by name (`add-place.js <folder>`, with Live quit), sets
  parameters by name over the LOM, places clips, records the Arrangement (`recordArrangement`,
  with timed `during` parameter changes), reads recorded audio as `Float32Array`s (`audio.js`,
  `wav.js`); checks bit depth and sample rate before recording.
- `log.js` / `cli.js max-log [since]`: Max console messages from **Live's `Log.txt`**. Our t1
  found device errors in `Max 9/Logs/MaxPlugLib.log` while Live runs the standalone Max 9.2.1
  (`CLAUDE.md` Status), so our checks must read both [hypothesis: Log.txt alone may miss them].
- `device-checks.js` runs table-driven cases for **MIDI** devices (compares notes); audio
  effects get `audio.js`; for an **instrument** like aliasing we write our own loop on the same
  primitives (MIDI clip → instrument → record its Post FX on an audio track) [sourced: "Checks
  of audio or a control signal have their own loop"].
- **Test hook (ADR-0002):** a development build reports `/hook/<topic>` over UDP/OSC to
  127.0.0.1:11002 (status line, in-device check results) and takes commands through one
  automated menu parameter; release builds leave it out. This replaces a Max MCP as the way to
  read what a device shows in Live.
- Optional and heavier: `device-ui.js` presses controls with **real mouse events** (takes the
  pointer, asks per run unless `clickHost` is set), window captures and videos of Live (Screen
  Recording permission).
- Requirements: macOS, Live 12 (used with 12.4), **Live's language English** (it finds menus and
  dialogs by name), Count-In None, Accessibility + Automation permission for the app that runs
  the commands (dialogs), Screen Recording only for captures. The `verify-ableton` skill tells the
  agent to ask whether Live is free before any run.

## What could run without the user (aliasing, sketch) [hypothesis]

| Check | How | Replaces in t3 |
|---|---|---|
| Loads, console clean, "ready" posts present | relaunch → load from Places → `max-log` + `MaxPlugLib.log` since start | "copy the Max console" |
| Parameter inventory | LOM `device.parameters` (names, ranges, defaults) against the shell spec of `scripts/check_shell.py` (67 parameters) | Parameter inspector spot checks |
| Audio sanity, Drone and MIDI gate | record N s at fixed settings, `m4l-analyze` health (NaN/inf, silence, peak, DC) and Welch-PSD distance against the standalone/host render of the same settings | "does it sound at all, does it blow up" |
| Parameter sweeps | `during` changes per page (Mod/Tone/Out) while recording; no NaN, bounded peak | part of the listening pass |
| Save and reopen | harness `save-reopen` pattern (Save As into temp) | state survives reload (open check 7) |
| Device panel picture (optional) | window capture → Claude looks at it | painter/stock-look check (open check 12), not theme or taste |

Not automatable here: listening judgement, A/B against Reaktor, the 9.1.5 round (Live's Max
setting needs a restart and lives in Live's binary preferences), freeze, CPU reading (no LOM
source found for this note) [open].

## Fit with the workbench rules

Adopting the harness changes decisions in `CLAUDE.md`: today the user operates Live and Claude
never drives it. A rule like the standalone-Max exception would be needed: Claude may relaunch
Live on the harness's empty set **after the user confirmed Live is free**, runs are silent
(Main at −inf), never the user's Sets, no real mouse clicks unless asked. The OSC API at the pin
has no getter for Main's volume, so our check makes the recording silent at the track level as
well: device track at −inf (Post FX is tapped before the mixer [hypothesis, spike check L4]) and
the recording track's monitoring Off. Harness commands talk UDP on localhost and start Live,
so they run outside the sandbox (like `git`). The harness wants run logs committed under
`tests/live/logs/`; ours are local-only (`testlog/`), so we keep our convention.

**Decision (user, 2026-11-25):** prepare the spike. Done the same day: the `CLAUDE.md` exception
"Live test harness", `tools/live/README.md` (pin `ad756c1e` after reading its source, one-time
setup, spike checks L1–L6), `tools/live/check-instrument.mjs`.

## Sources

- GitHub REST API, 2026-11-25: repo metadata of every repo named above; search queries for repos
  created since 2026-11-15 (`max mcp`, `maxmsp`, `max for live`, `ableton mcp`, `ableton extension`,
  `m4l mcp`).
- eladefrati/ableton-live-test-harness @ `ad756c1e`: `README.md`, `harness/README.md`,
  `skills/verify-ableton/SKILL.md`, `docs/adr/0002-test-hook.md`,
  `harness/checks/example-transpose-check.js`.
- adamjmurray/producer-pal: `README.md`, release notes v2.4.0, v2.5.0-rc1, v2.5.0, v2.6.0-rc1, repo tree.
- Ableton: [Extensions page](https://www.ableton.com/en/live/extensions),
  [Extensions SDK docs](https://ableton.github.io/extensions-sdk),
  [Introducing Extensions SDK](https://www.ableton.com/en/blog/introducing-extensions-sdk).
- Earlier notes: `Max for Live mit Claude bauen.md`, `m4l-toolchain-dependencies-2026-11-24.md`.
