# ProbeUI: painted `live.*` controls and table storage (checks G-UI1, G-UI5)

A throwaway **audio effect** (audio passes through untouched) that answers two questions before
the `aliasing` face is rebuilt (`devices/aliasing/docs/redesign-t1.md` R5, R10, R15):

1. **G-UI1:** do `jspainterfile` painters work on `live.dial` and `live.tab` in Live, with
   standalone Max 9.2.1 *and* with Live's bundled Max 9.1.5? Which JS engine runs them, do they
   repaint on a theme change, are the automation/modulation/macro states readable, and does all
   native parameter behaviour survive (map modes, context menu, double-click default, undo)?
2. **G-UI5 (new): blob storage:** can the device keep a drawn table (5 voices × 1024 floats =
   5120 values) with the Live Set, and does it come back bit-exact (or how close)?

Research background: `docs/research/notes/m4l-custom-ui-and-sync-2026-11-24.md` (A2, B4).
G-UI5 is defined here; add it to that note's check table when the results are logged.

## Files

| File | What |
|---|---|
| `make_probe.py` | Generator (python3, stdlib only) → `ProbeUI.amxd` from Live's `Max Audio Effect.amxd` |
| `ProbeUI.amxd` | Generated device (unfrozen). Re-generate rather than edit; it is a probe |
| `probe_dial_painter.js` | jspainter for the `live.dial` "Probe Dial" (plain ES5) |
| `probe_tab_painter.js` | jspainter for the `live.tab` "Probe Tab" (plain ES5) |
| `probe_store.js` | `v8` script: Scramble / Verify, store, restore, checksums (ES2020, hand-written, no TS) |

Regenerate (refuses to overwrite without `--force`; close the device in Max first, Max reloads
changed files and drops unsaved edits):

```sh
python3 -B devices/aliasing/test/probe-ui/make_probe.py --force
python3 tools/vendor/maxdevtools/maxdiff/amxd_textconv.py devices/aliasing/test/probe-ui/ProbeUI.amxd
```

(`tools/check.sh aliasing` does not pick this folder up: it only parses `devices/aliasing/*.amxd`
and `devices/aliasing/test/*.maxpat`.)

## How the face works

- **Probe Dial** (`live.dial`, float 0–1, Bipolar modulation): arc in a muted sage accent, value
  text, short name, and a status row `aut mod mac` that lights up when `isautomated`,
  `ismodulated`, `ismacroassigned` read 1. If those attributes are not readable the row says
  `state attrs: n/a`. The painter also sets `jspainterautomation = 1` and `automationpoint` to the
  top-right corner, so Live's own dots should appear there too. A 5 px square top-left is
  `live_control_selection` straight from `max.getcolor()`.
- **Probe Tab** (`live.tab`, enum Sine/Tri/Saw/Square): pill-shaped segmented control, waveform
  icons drawn as paths, selected segment filled with the accent.
- Both painters read theme colours with `max.getcolor()` inside `paint()`, which Max calls again on
  a theme change [sourced: Max user guide "Dynamic Colors"]; on such a repaint they post
  `repaint with new theme colour live_control_fg=…`.
- **Engine line.** On its first paint each painter posts one line:
  `probe_<dial|tab>_painter: ENGINE let=… const=… arrow=… template=… class=… destructuring=…
  optchain=… Symbol=… Promise=… globalThis=… stack=… | API max.version=… getcolor=… parentpaint=…
  isautomated=… … _parameter_range=… value=… size=…`. Syntax support is tested with
  `new Function(src)` inside `try/catch`, so the painters themselves stay ES5 and cannot fail on an
  old engine; `stack=v8` / `spidermonkey` comes from the `Error().stack` format. `arrow=1 class=1
  template=1` means a modern engine (v8); all 0 means legacy `js` (ES5).
- **Log.txt.** Every probe line is posted with `post()` *and* repeated with `error()` prefixed
  `[ProbeUI info, not an error]`, so it should also land in Live's `Log.txt` as
  `Message from Max: …` (whether plain `post()` lines reach Log.txt is [open]).

## How the table storage works

Max for Live has four parameter data types; **Blob** parameters "cannot be automated or
modulated, but can be stored in presets" and "may be any type of data you can store with a pattr
object: single values, lists, dictionaries, arrays or symbols" [sourced: Max 9.2 user guide
`parameter_mode.json` "Parameter Data Types"; same wording in the 9.1.5 copy; Max for Live
variant: `m4l/live_parameters.json`]. "Non-automatable parameters (Blob) are 'Stored Only' by
default" [sourced: `m4l-ref/parameters.maxref.xml`, Parameter Visibility]. Stored Only parameters
are saved with the Set and with presets, never automated.

The probe stores the same table twice, so one Set test compares both documented carriers:

| Variant | Object | Precedent (local, `m4l-boxref`) |
|---|---|---|
| **A** list | `pattr probetable`, Parameter Mode on, type Blob (3), Stored Only (1), long name **Probe Table**; receives a 5120-float list | Ableton/C74 devices: Waveshaper `pattr wave` (256 floats), Spectral Filter, Tapped Delay (Max 6), Step Arp (Factory Pack, Max 9.0.7) |
| **B** dict | `dict ---probedict`, Parameter Mode on, type Blob, Stored Only, long name **Probe Table Dict**; holds `{table:[5120], sum, wsum, first}` | Ableton's newest devices: Variations `dict ---presets_params` (Max 9.0.7), Performer, Vector Map/Delay/Grain/FM (Max 8.6) |

`parameter_enable` on `dict` is documented in both builds' refpages ("Enables use of this object
with Max for Live Parameters"). `pattr` takes lists and (`dictionary` method) dictionaries in both
builds [sourced: `max-ref/pattr.maxref.xml`, `max-ref/dict.maxref.xml`]. Not chosen: `live.*` UI
objects (no Blob type for them [hypothesis]), `dict @embed 1` (saves into the device file, not
per Set), a plain v8 `Dict` (not a parameter, not saved).

Flow (patch, generated): `live.thisdevice → t b b` sends `bufname ---probetab, dictname
---probedict` then `init` to `v8 probe_store.js ---probetab ---probedict` (the `---` names also
arrive as box arguments; JS strings are not substituted). **Scramble** fills `buffer~ ---probetab
@samps 1024 5` with random −1…1, reads it back (float32), posts `STORE n=5120 sum=… wsum=… first=…`,
sends the list to the pattr and `dictionary <scratch>` to the dict (which clones it). Both objects
echo; the script checks the echo (`ECHO list … (identical)`, `ECHO dict … (identical)`). When Live
recalls the Set, whatever the pattr/dict output is a restore: `RESTORE list -> buffer …`,
`RESTORE dict …`, then `COMPARE list vs dict: max|diff|=…, list sum - stored sum = …` (the dict
carries the sum computed at save time). If the dict does not output on recall, `init` reads it by
name (`RESTORE dict (read by name at init)`). The buffer is written from the list, or from the dict
if no list arrived. **Verify** posts `BUFFER now …`. The last line also shows on the face.

`sum` = plain sum, `wsum` = position-weighted sum (catches reordering), `first` = first 3 values.

## Handover checklist (user, in Live)

Safety: audio passes through unchanged, but keep the monitor down as usual.
Before each round: no unsaved Max work open; Live's log is
`~/Library/Preferences/Ableton/Live 12.4.16/Log.txt`
(`grep -a "ProbeUI" ~/Library/Preferences/Ableton/Live\ 12.4.16/Log.txt | tail -40`).

**Round 1: standalone Max 9.2.1** (Live Settings → File & Folder → Max Application = standalone
Max, restart Live; Log.txt shows `Max: Version 9.2.1`). **Round 2: bundled Max 9.1.5** (Max
Application back to the bundled one, restart Live; `Max: Version 9.1.5`). Do every step in both
rounds; use a fresh Set per round.

| # | Check | Step | Expected / report |
|---|---|---|---|
| 1.1 | G-UI1 load | Drag `ProbeUI.amxd` onto an audio track. Open the Max Console (device title bar → edit in Max → Window → Max Console), or read Log.txt | No red errors except the `[ProbeUI info…]` lines. **Copy both ENGINE lines and the INIT line** |
| 1.2 | G-UI1 paint | Look at the face | Arc dial with value + `aut mod mac` row (or `state attrs: n/a`); pill tab with 4 waveform icons. Screenshot. Stock look instead = painter not loaded (report console lines) |
| 1.3 | G-UI1 interaction | Drag the dial (also with Shift for fine), click each tab segment | Arc/value and selected pill follow; normal drag feel |
| 1.4 | G-UI1 theme | Live Settings → Theme & Colors: switch to a light theme and back | Text/track/swatch recolour without reload; console `repaint with new theme colour …` |
| 1.5 | G-UI1 automation | Draw an automation envelope for Probe Dial (Arrangement), play | `aut` lights; native dot top-right of the dial? Re-enable/"back to arrangement" state drawn? |
| 1.6 | G-UI1 modulation | Live 12 modulation on Probe Dial (e.g. clip envelope in Modulation mode, or an LFO device mapped to it) | `mod` lights; dial value moves |
| 1.7 | G-UI1 macro | Group into an Audio Effect Rack, map Probe Dial to a macro | `mac` lights; macro dot? |
| 1.8 | G-UI1 map modes | MIDI Map (Cmd-M) and Key Map (Cmd-K): click the dial and the tab | Both selectable/mappable, map overlay drawn over the painted control |
| 1.9 | G-UI1 native | Right-click the dial and the tab; double-click the dial; select the dial and type `0.25` + Enter; Edit → Undo after a drag | Context menu (Show Automation…); double-click → 0.50; typed value accepted; one undo step per drag |
| 1.10 | G-UI1 focus / off | Click the dial (focus), then switch the device off | Focus frame visible; painted controls dim |
| 5.1 | G-UI5 store | Press **Scramble** | Console: `STORE …`, `ECHO list … (identical)`, `ECHO dict … (identical)`; face status `stored …`. **Copy the STORE line** |
| 5.2 | G-UI5 save | Save the Set, close it (open another Set), reopen it | Console after reopen: `RESTORE list -> buffer …`, `RESTORE dict …`, `COMPARE …`, `INIT … list restored: yes, dict restored: yes`. **Copy these lines**; `n=5120`; sums match STORE (to about 1e-6) |
| 5.3 | G-UI5 verify | Press **Verify** | `BUFFER now …` equals the RESTORE line |
| 5.4 | G-UI5 undo | Scramble again, then Edit → Undo | Does Undo bring the previous table back (a RESTORE line with the old sum), or is Scramble not undoable? |
| 5.5 | G-UI5 duplicate (optional) | Duplicate the track | The copy posts RESTORE lines with the same sums |

Report per round: Max version, the ENGINE lines (dial + tab), INIT/STORE/ECHO/RESTORE/COMPARE
lines, a screenshot of the face (dark and light theme), and yes/no per row. Claude writes the
test log (`live-test` skill) and updates the research note's markers.

## [open] (nothing here has run in Max or Live)

- JS engine for jspainter scripts in 9.1.5 and 9.2.1; whether `max.getcolor` exists there.
- `isautomated` / `ismodulated` / `ismacroassigned` / `jspainterautomation` / `automationpoint`
  on `live.dial` and `live.tab` in 9.1.5 (documented only in the 9.2 guide; the strings exist in
  `live.guilib` of both builds [code: `strings`]). Max 9.2 also has a `sendjspainter` message that
  9.1.5 lacks.
- `jspainterfile` on `live.tab`: a common box attribute (`max-ref/jbox.maxref.xml`, both builds), but
  no Max-saved `live.tab` with it exists locally; `live.dial` has one (Ableton's Color Limiter,
  Creative Extensions, `livedial_override.js`).
- `_parameter_range` / `_parameter_exponent` / `_parameter_shortname` via `box.getattr` (used by
  Ableton's Color Limiter painter; the probe falls back to 0–1 and fixed names).
- Blob list of 5120 values in `pattr` (largest local precedent: 256), and whether Live writes the
  floats exactly; whether `dict` with Parameter Mode outputs on recall; whether writing to the
  dict by cloning marks the Set as changed; undo behaviour of both.
- Re-entrant pattr/dict echo into `v8` (handled by flags, but untested); `---` substitution in
  `v8` box arguments (backed up by the init message).
- Whether `post()` lines reach Live's Log.txt (the `error()` copies should).
