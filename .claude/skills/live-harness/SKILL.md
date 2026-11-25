---
name: live-harness
description: Run a device of this workbench in Ableton Live automatically, without the user's hands - relaunch Live on an empty test Set, load the device from Places, read the Max console from both logs, compare Live's parameters with the .amxd, record it silently and check the take - through the optional Live automation (eladefrati/ableton-live-test-harness, tools/live/). Also for its switch, setup and trouble (status, on/off, install, AbletonOSC missing, Accessibility error -1719, Places). Use before a live-test handover when the automation is on, and whenever the user says "teste das automatisch in Live", "lass den Harness laufen", "Live-Automation an/aus", "läuft der Harness?". Not for listening, A/B against Reaktor or anything the user must hear or judge (live-test).
---

# Live automation (optional)

The workbench works without it: when it is off, every Live test is a `live-test` handover. When
it is on, Claude runs the mechanical part of a Live test itself and hands the user only what needs
ears and eyes. Rules: `CLAUDE.md` → Decisions → "Exception, Live test harness". Setup and the
spike checks L1–L6: `tools/live/README.md`.

## 1. Is it on?

```bash
node tools/live/harness.mjs status
```

- `off` (or no `tools/live/local.json`, the default on a fresh clone): **stop here**. Do not
  start, drive or quit Live; use `live-test`. Offer to switch it on only if the user asked for
  automation; switching on is the user's call (`node tools/live/harness.mjs on`).
- `miss` lines: setup is incomplete; show the user `tools/live/README.md` "Install" and, with
  their OK, run `node tools/live/harness.mjs install` (outside the sandbox).
- `warn` on the pin: the clone moved. Do not run it until the new commits are read (README, pin table).

## 2. Before touching Live

- Ask the user whether Live is free **before the first relaunch of a session**, and whenever
  `run doctor` says the open Set was not made by the harness. A relaunch discards unsaved work.
- Know the state you test: a commit, or exactly what the working tree adds (as in `live-test`
  §1). Another session may be changing the device folder; do not test a half-written state.
- Run `tools/check.sh <device>` first; never test a state with failing offline checks.

## 3. Run

All harness commands talk UDP to Live or start apps: run them **outside the sandbox**.

```bash
node tools/live/harness.mjs run relaunch     # Live on the harness's empty Set, Main at -inf dB
node tools/live/harness.mjs run doctor       # read-only: Live, AbletonOSC, dialogs, bit depth, rate
node tools/live/check-instrument.mjs devices/<name>/<Name>.amxd [--set "Long Name=value" ...] [--expect-post "<regex>" ...]
node tools/live/harness.mjs run quit         # when done, or when the user asks
```

`check-instrument.mjs` (instrument devices; options in its header) prints PASS/FAIL lines and
writes `build/<device>/live/<stamp>/result.json` + `take.wav`: git state and runtime hashes, Max
version, console lines since the load (Live's `Log.txt` and `MaxPlugLib.log`), every visible
parameter against the `.amxd` (name, range, enum items, initial value), take health (non-finite,
silence, peak above the safety clip, DC). Exit 0 PASS, 1 findings, 2 could not run.

Then analyse `take.wav` with `m4l-analyze` where the question needs it (PSD distance against a
standalone-Max or host render of the same settings).

## 4. Record and hand over

- Log the run like any test: `testlog/<device>/<date>.md`, one `##` section, "Tested by: harness
  (check-instrument)", the result.json path, findings verbatim, interpretation kept apart.
- Then the `live-test` handover covers only what the run cannot: listening, A/B against Reaktor,
  how the face looks, the bundled Max 9.1.5 round, CPU, freeze. Say which items the run already
  answered.

## Never

- Run anything in Live while the switch is off, or in a Set the user did not call disposable.
- Use `device-ui.js` (real mouse clicks) or window captures/videos unless the user asks for it.
- Play audio audibly: the check keeps the device track at −inf and the recording track's
  monitoring Off and refuses otherwise; do not work around that.
- Move the pin, edit `Library.cfg` by hand, or change Claude's own sandbox/permission settings.

## Trouble

| Symptom | Cause, fix |
|---|---|
| AbletonOSC not in Live's Control Surface list | Remote Script link missing or dangling (a relative link resolves from Remote Scripts); `harness.mjs status`, then `install`; restart Live |
| `osascript … Hilfszugriff (-1719)` / doctor: "System Events can't name its app" | Accessibility missing for the **inner "Claude Code" app** (not `/Applications/Claude.app`): README step 4 |
| `add-place.js`: "doesn't have the one list of Places expected" | Live's empty `<UserFolderInfoList />`; `harness.mjs install` expands it (backup in `build/live/`) |
| check refuses: bit depth | Live → Settings → Record, Warp & Launch → 32-bit float (the user) |
| check: build in 0 or 2 Places folders | `install` (Live quit), or remove the duplicate Place in Live's browser |
| relaunch stops at a dialog | read the printed message; ask the user; never click it away blindly |
