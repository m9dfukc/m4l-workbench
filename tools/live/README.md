# Optional Live automation (spike)

Claude runs checks of our devices inside Live without the user's hands: relaunch Live on an
empty Set with Main at −inf dB, load the device from Live's Places, read the Max console, compare
the parameters with the `.amxd`, record the device silently and check the take. Rules and
conditions: `CLAUDE.md` → Decisions → "Exception, Live test harness"; Claude's procedure: skill
`live-harness`. Background and choice of tool: `docs/research/notes/live-automation-mcp-2026-11-25.md`.

**Optional.** The workbench works without it. It is **off by default** (a fresh clone has no
`tools/live/local.json`); while off, every Live test is a `live-test` handover to the user and
the scripts here refuse to touch Live.

```bash
node tools/live/harness.mjs status
```

```bash
node tools/live/harness.mjs on
```

```bash
node tools/live/harness.mjs off
```

## Install (short)

Needs macOS, Ableton Live 12 Suite with Max for Live, Node ≥ 18. About 10 minutes.

1. With Live **quit**, outside Claude's sandbox: `node tools/live/harness.mjs install` — clones
   the harness at the pin next to this repo, links it into the Remote Scripts of the User
   Library Live uses (absolute link), adds every `devices/<name>/` to Live's Places, and prints
   the rest. `--dry-run` shows what it would do.
2. In Live: Settings → Link, Tempo & MIDI → a free Control Surface slot = **AbletonOSC** (Input
   and Output None); **Language English** (restart Live); Record, Warp & Launch → **Bit Depth
   32-bit float**; Count-In **None**.
3. In macOS: Privacy & Security → **Accessibility** ("Gerätesteuerung und Datenzugriff") → add the
   **inner "Claude Code" app** that `install` names (not `/Applications/Claude.app`; step 4 below).
4. `node tools/live/harness.mjs on`, then with Live open: `node tools/live/harness.mjs run doctor`
   and `node tools/live/harness.mjs run roundtrip` (both must pass).

**Uninstall:** `harness.mjs off`; delete the `AbletonOSC` link in `<User Library>/Remote Scripts`
and the Control Surface slot; remove the Place in Live's browser (right-click → Remove from
Sidebar); delete the clone.

The numbered "One-time setup" below is the same by hand, with the reasons and what went wrong
on the first install (2026-11-25).

The harness is [eladefrati/ableton-live-test-harness](https://github.com/eladefrati/ableton-live-test-harness)
(MIT), an AbletonOSC fork that runs as a Remote Script in Live and listens on 127.0.0.1 only.
It is **not vendored**: it must be a working tree that Live runs from. Pinned commit (also
`PIN` in `harness.mjs`):

| Pin | Date | Read before pinning |
|---|---|---|
| `ad756c1e` | 2026-11-23 | 2026-11-25: Python side binds 127.0.0.1, no `exec`/`eval`/subprocess; Node side deletes only Live's own Temp Projects made since its relaunch and its temp folder, moves Live's recovery data into the prefs `Crash` folder, answers "Save changes?" with Don't Save |

Before moving the pin, read the new commits the same way and update this table.

## One-time setup by hand (details)

Order matters; Live quit for steps 2 and 6.

1. **Clone the harness at the pin** next to this repo (not inside it; `check-instrument.mjs`
   finds it there, else in `~/dev/`, or set `LIVE_HARNESS` to its `harness/` folder):

   ```bash
   git clone https://github.com/eladefrati/ableton-live-test-harness ~/Downloads/_Playground_/ableton-live-test-harness
   ```

   ```bash
   git -C ~/Downloads/_Playground_/ableton-live-test-harness switch --detach ad756c1e
   ```

2. **Link it into Live's Remote Scripts** as `AbletonOSC` (move an existing `AbletonOSC` folder
   out first; this replaces it, and it then answers on 127.0.0.1 only). The Remote Scripts
   folder is inside **the User Library Live actually uses** (Settings → Library → Location of
   User Library; here `~/Documents/Ableton/User Library`, not `~/Music/Ableton/…`). The link
   target must be an **absolute** path: a relative one is resolved from the Remote Scripts
   folder and dangles (seen 2026-11-25). Restart Live afterwards; it scans Remote Scripts at start.

   ```bash
   mkdir -p ~/Documents/Ableton/User\ Library/Remote\ Scripts
   ```

   ```bash
   ln -sfn /Users/m9dfukc/Downloads/_Playground_/ableton-live-test-harness ~/Documents/Ableton/User\ Library/Remote\ Scripts/AbletonOSC
   ```

   Check: `ls ~/Documents/Ableton/User\ Library/Remote\ Scripts/AbletonOSC/manager.py` prints the
   file.

3. **Live settings** (start Live):
   - Link, Tempo & MIDI → a free **Control Surface** slot → `AbletonOSC`, Input and Output
     **None**. Live shows "AbletonOSC: Listening for OSC on port 11000".
   - **Language: English** (Live's Settings; the harness finds Live's menus and dialogs by
     name). Live needs a restart after changing it.
   - Record, Warp & Launch → **Bit Depth: 32-bit float** (the check refuses otherwise; float
     takes show NaN and overs instead of clipping them).
   - Control bar → metronome menu → **Count-In: None** (Live's default).
   - Leave Live's Max application at the standalone Max 9.2.1 (as now).
4. **macOS permissions** for the app that runs Claude's commands. That is **not**
   `/Applications/Claude.app`: the desktop app starts Claude Code through a `disclaimer` helper,
   so macOS holds the inner bundle **"Claude Code"** (`com.anthropic.claude-code`, Anthropic team
   `Q6L2SF6YDW`) responsible [measured: process tree 2026-11-25]. Its path is versioned, here
   `~/Library/Application Support/Claude/claude-code/2.1.330/4262a1273231/claude.app`.
   - System Settings → Privacy & Security → **Accessibility** (macOS 27, German: "Gerätesteuerung
     und Datenzugriff") → "+" → Cmd+Shift+G → paste that path → Open → switch it on.
   - **Automation → System Events** was granted already (test below answered).
   - Test (outside the sandbox): `osascript -e 'tell application "System Events" to tell process
     "Finder" to get name of every menu bar item of menu bar 1'` lists Finder's menus; error
     -1719 means Accessibility is still missing.
   - Whether the grant survives a Claude Code update (new versioned path, same bundle id and
     team) is [open]; rerun the test after an update.

   The harness needs these to answer Live's dialogs when it relaunches or quits Live. Screen
   Recording is **not** needed (no captures without asking).
5. **Places:** quit Live, then add the device folder (Claude may run this once you have quit
   Live; it only edits Live's `Library.cfg`). With no Places yet, Live writes an empty
   `<UserFolderInfoList />` and `add-place.js` (at the pin) refuses with "doesn't have the one
   list of Places expected": expand it to `<UserFolderInfoList>` … `</UserFolderInfoList>` first
   (done 2026-11-25 for Live 12.4.16, `devices/aliasing` got `Id="10227"`), or add the first
   Place with Add Folder in Live's browser.

   ```bash
   node ~/Downloads/_Playground_/ableton-live-test-harness/harness/add-place.js ~/Downloads/_Playground_/m4l/devices/aliasing
   ```

6. **First run of the harness alone** (Live open on a new, empty Set):

   ```bash
   node ~/Downloads/_Playground_/ableton-live-test-harness/harness/doctor.js
   ```

   ```bash
   node ~/Downloads/_Playground_/ableton-live-test-harness/harness/checks/record-roundtrip.js
   ```

   The doctor names anything missing (permission, Control Surface, dialogs). The round trip adds
   two tracks, records MIDI from one into the other and deletes them again.

Optional: Claude's Bash sandbox blocks UDP to Live and starting apps, so every Live command
(`harness.mjs install|run`, `check-instrument.mjs` without `--offline`) asks for a run outside
the sandbox. To stop the prompts, add `node tools/live/*` to `sandbox.excludedCommands` in
`.claude/settings.json` yourself (Claude does not change its own sandbox settings); the switch
still keeps them away from Live while it is off.

## Running a check (Claude, skill `live-harness`)

0. `node tools/live/harness.mjs status` says **on**; otherwise stop (hand over with `live-test`).
1. Ask the user whether Live is free (no unsaved work: relaunch discards it).
2. Start Live on the harness's empty Set (Main at −inf dB):
   `node tools/live/harness.mjs run relaunch`
3. Run the check on the device's runtime state (test from a commit, as in `live-test`):

   ```bash
   node tools/live/check-instrument.mjs devices/aliasing/Aliasing.amxd --expect-post "aliasing_display: .* ready" --expect-post "aliasing_pages: .* ready"
   ```

4. Read `build/<device>/live/<stamp>/result.json` (state, Max version, console lines, every
   parameter against the `.amxd`, take health) and analyse `take.wav` with `m4l-analyze`. Log the
   run in `testlog/<device>/<date>.md` like any `live-test` entry, with "Tested by: harness".
5. Quit Live when done or when the user asks: `node tools/live/harness.mjs run quit`.

`node tools/live/check-instrument.mjs <device.amxd> --offline` prints the parameters the `.amxd`
declares without Live (used by the offline tests).

## What the spike has to show (spike checks L1–L6)

| # | Question | Pass |
|---|---|---|
| L1 | Setup: doctor clean, round trip passes | both PASS — **passed 2026-11-25** (relaunch 4.8 s, round trip 4/4 PASS, 0 ms timing error) |
| L2 | Load from Places and console from both logs: does `check-instrument` see the "ready" posts and real errors (try a device state with a known console error once)? | posts found; a planted error is reported — **posts found** (aliasing v0.3, 2026-11-25); error detection not yet shown on a real error |
| L3 | Is Live's parameter order the long names' code-unit order, and does the LOM give short names (harness claim)? | `parameters: N match the .amxd`, or a clear mismatch list — **yes, 173 of 173** |
| L4 | Silence: does Post FX record at full level with the device track at −inf and the recording track's monitoring Off, and does nothing reach Main? | take not silent; Main meter stays empty (user looks once) — **Post FX records at full level** (peak −7 dBFS); Main meter not yet watched |
| L5 | Does the take match a standalone-Max render of the same settings (Welch-PSD distance, `m4l-analyze`)? | distance in the range of two standalone renders — open (needs a matched standalone render) |
| L6 | Run time of one check, and does Live stay usable for the user afterwards (`quit.js`, next normal start without recovery dialog)? | under ~2 min; no dialog — **16–19 s** + 5 s relaunch; `quit.js` clean; next normal start open |

Measured in the first runs (testlog `t4-auto`, 2026-11-25), built into `check-instrument.mjs`:

- For a parameter with `parameter_exponent`, the LOM `value` is the control position mapped
  linearly onto min..max, `min + (max−min)·((v−min)/(max−min))^(1/exp)`; `value_string` shows the
  real value.
- `live.text` shows its two values in Live by the box attributes `automation` / `automationon`
  (default `val1`/`val2`), not by `parameter_enum` [sourced: `live.text.maxref.xml`; measured:
  aliasing before/after, testlog `t4-auto-2`]. A first reading ("the enum is fixed", from 40
  help-file boxes) was wrong: of 5000 Max-saved boxes, 2100+ carry named values.

Not covered by the harness: listening, A/B against Reaktor, the bundled Max 9.1.5 round, freeze,
CPU, how the face looks (captures only on request).
