# Push compatibility of an M4L instrument: tethered Push and Push 3 Standalone (2026-11-25)

Question: is a Max for Live **instrument** like `devices/aliasing/` compatible with (1) Ableton Push
2/3 in **Control Mode** (tethered to Live on a Mac) and (2) **Push 3 in Standalone Mode** (Live and
Max running on Push's own Intel/Linux hardware)? What works, what does not, and what must the
device do to show its parameters well on Push?

Device context: unfrozen shells `Aliasing.amxd` / `Aliasing B.amxd`, built for Max 9.2 / Live 12.4;
stock Live 12.4.16 ships Max 9.1.5. Objects: `gen~` (`.gendsp`, 140 Params, `Data`), two `buffer~`,
`v8` (page script), `v8ui` (table display, mgraphics, Task at 30 fps, `Buffer`, `Dict`),
`jspainterfile` painters (legacy ES5 engine) on `live.dial/tab/text/numbox/menu/slider`,
`live.thisdevice`, `live.colors`, `live.meter~`, `plugsync~`, `phasor~ @lock 1`, `notein`, `ctlin`,
`borax`, `click~`, a `dict` Blob parameter (Stored Only); the sample drop `live.drop` + `sfinfo~` +
`buffer~ read` (built the same day, D50–D54, after this note was started). 137 automatable parameters (count from `bootstrap_shell.py --face hybrid`), no
`live.banks`. No externals, `jweb`, `node.script`.

**Evidence markers** as in `CLAUDE.md`, plus the ones this task asked for: **[sourced]** (URL or
local path), **[user report]** (forum post), **[inference]** (= the project's [hypothesis]),
**[open]** (needs a hardware test), **[measured]** (a local file check done for this note).
"[inference: decompiled]" marks conclusions read from an unofficial decompilation of Live 12's
control-surface scripts (`gluon/AbletonLive12_MIDIRemoteScripts`), which is Ableton's code but
not an Ableton publication.

Not repeated here: custom UI options, `jspainter` engine and dot API, Visible modes in general,
`jweb` (`m4l-custom-ui-and-sync-2026-11-24.md` §A2–A5); production-guideline checklist
(`reference/m4l-production-guidelines.md` §Push Support, §OS Compatibility, release checklist).

## Summary

- **Push never shows a device's GUI.** Push shows parameters in **banks of 8 encoders** (plus,
  since Live 12.3, up to 7 usable buttons); anything that lives only in the GUI (the `v8ui` table,
  drawing, page tabs) is unreachable from Push in both modes [sourced: CDM 2023 "no way to create
  custom UIs"; Ableton help article: Ableton's own modulators are "limited control" on standalone
  because only automatable parameters can be controlled].
- **Without `live.banks` the device shows no parameters on Push** ("No parameter mapped"), in
  Control Mode too [user report ×2; CDM 2023; Ableton forum moderator 2018: "In L10, you need to
  use the live.banks object."]. Max-saved patchers with parameters carry an empty default bank,
  so Push takes the Max-banks path and finds 8 empty slots instead of falling back to "first 8
  parameters" [inference: decompiled + saved JSON]; our generator-written shells carry no bank block
  at all, so what Push shows for them today is [open] (§2.1, P1). **Define banks for aliasing**
  either way: 137 parameters in Live's default order are not usable from Push.
- **Push 3 Standalone runs Max 9:** Push 2.3.5 / Live 12.3.5 (2026-01-26) "Updated the bundled Max
  version to build 9.0.10"; Push 2.4 / Live 12.4 (2026-05-05) lists "Updated the bundled version
  of Max to 9.1.4" under **"Push 3 Standalone Mode Only"**; Push 2.4.5 (2026-08-26) "Updated Max
  9.1.5 to 3db35fa" [sourced: Push 12 release notes]. Our local Live 12.4.16 bundles Max 9.1.5
  (3db35fa476d) [measured: Info.plist]. So Push standalone is **not** on Max 8.6: `v8`, `v8ui`,
  Visible modes and `live.banks` button assignments belong to the Max version it runs.
- **No primary source says that `v8`/`v8ui`/`jspainter` run on Push 3 Standalone, nor that they
  don't.** Ableton's compatibility article (updated 2026-11-19) lists devices, not objects;
  Cycling '74 said in 2023 that JSUI "does build for the standalone version" and that devices not
  relying on Jitter, Java, Mira or third-party externals should work [sourced: C74's Joshua Kit
  Clayton quoted by CDM]. Any object that is missing on Push makes the **whole device fail to load**
  ("This device contains missing or incompatible Max objects") [sourced: Ableton help; user report].
  → **[open], test on hardware with a probe device before relying on it.**
- **`gen~` works on standalone** [sourced: C74 via CDM 2023 "gen-based devices"; user report:
  C74 forum "PUSH3 standalone + gen~"]. Push 3's processor is an Intel 11th Gen Core i3-1115G4
  [sourced: Ableton tech specs], i.e. x86-64, so gen~'s JIT has a native target [inference].
  No official CPU guidance per device exists [sourced: absence in help article, FAQ, manual].
- **Loading new audio files is not a standalone feature:** Ableton's own sampling devices have
  "sample import disabled" on Push standalone (DS-Sampler, Granulator III), and "Resolving missing
  media files is not possible on Push" [sourced: Ableton help]. The `live.drop` path is
  desktop-only; the Blob-stored table is the right carrier for Push — and the sample drop already
  writes a dropped file into that table, so a table made on the Mac travels with the Set [inference].
- **Getting the device onto Push:** pair Push and Live, copy devices/presets into the User
  Library inside the Push label; Sets go over after Collect All and Save [sourced: Push 3 manual
  §5.5.3, Push 3 Technical FAQ]. An unfrozen device that loads `.gendsp`/`.js` files from beside
  the `.amxd` needs those files too → **transfer a frozen copy** (freezing embeds subpatchers,
  audio, JS, …) [sourced: Max user guide "Freezing"; inference for the gendsp case].
- **Tethered (Control Mode) is the safe path:** everything runs in desktop Live; "up-to-date Max for
  Live devices, even if incompatible with Push in Standalone Mode, are expected to work in Ableton
  Live when using Push in Control Mode" [sourced: Ableton help]. Only the bank layout matters there.

### Per object / feature

| Object / feature in aliasing | Push tethered (Control Mode) | Push 3 Standalone |
|---|---|---|
| Device GUI (presentation, `v8ui` table, page tabs) | **not shown on Push**; works on the Mac screen [sourced: CDM 2023] | **not shown**; nothing GUI-only is reachable [sourced: CDM 2023, Ableton help "limited control"] |
| `live.*` parameters on Push without `live.banks` | **not supported**: "No parameter mapped" [user report; CDM 2023] | same [inference] |
| `live.banks` (8 encoders + `@buttons`, names, runtime edits) | works [sourced: refpage, help patch]; button assignments since Live 12.3 (its Max 9.0.9 build) [sourced: Live 12 notes] | works, Ableton's own devices use banks there [inference]; dynamic edits [open] |
| Visibility "Automated and Stored" | on Push via banks [sourced: parameter_mode guide] | same [inference] |
| Visibility "Visible" / "Visible (Not Stored)" | on Push **only when placed in a `live.banks` bank**, since Live/Push 12.4 (Max 9.1.3+) [sourced: Push 12 release notes, Max 9.1.3 notes] | same; "fixed param visibility getting stuck after saving" in 9.1.5 build [sourced] |
| "Stored Only" (Page, Mod Target, Display Mode, Blob `Table`) / "Hidden" (Clear) | not visible to Push [sourced: parameter_mode guide table] | same; Stored Only values still travel with the Set [inference] |
| `@active 0` on a parameter | shown greyed out on Push since Live 12.1.10 [sourced: Live 12 release notes] | same [inference] |
| `gen~` + `.gendsp`, `Data`, `buffer~` (internal) | works (desktop Live) [sourced: Ableton help, Control Mode] | **works** [sourced: C74 via CDM 2023; user report]; CPU headroom [open] |
| `v8` (page script) | works (desktop Max 9.1.5/9.2) [sourced: Max docs] | Max version on Push includes it (9.0.10 → 9.1.5) [sourced: release notes]; actually instantiating on Push Linux **[open]**, no source either way |
| `v8ui` (mgraphics, Task, `Buffer`, `Dict`) | works on the Mac screen [sourced: Max docs] | same as `v8` **[open]**; even if it loads, nothing is displayed; its Task keeps running headless [inference] |
| `jspainterfile` painters (legacy JS engine) | work on the Mac screen [measured: smoke test, earlier note] | legacy JS/JSUI builds for standalone [sourced: C74 via CDM 2023]; jspainter itself **[open]**; nothing is drawn on Push [inference] |
| Jitter / OpenGL | not used | Jitter GL disabled on standalone; GL devices crashed Push before 12.4 [sourced: Push 12 notes] |
| `live.thisdevice`, `live.colors`, `live.meter~` | work | no exclusion found [inference: work; colours/meter are GUI-only and harmless] |
| `plugsync~`, `phasor~ @lock 1` | work | no exclusion found [inference: work, Live's transport runs on Push] [open: tempo-follow edge cases] |
| `notein`, `ctlin`, `borax`, `click~` | work | no exclusion found [inference: work] |
| `dict` Blob parameter (table stored with the Set) | works (desktop) [sourced: parameter_mode guide] | stored in the Set, so it should travel with Set transfer [inference] **[open]** |
| planned `live.drop` + `buffer~ replace` + `sfinfo~` | works on the Mac screen; not usable from Push (no drop target on Push) [inference] | **not usable**: no GUI to drop on; Ableton disables sample import in its own devices; Mac file paths do not exist on Push [sourced: Ableton help; inference] |
| Third-party externals, `hi`, `serial`, Java, Mira | not used | **not supported** [sourced: C74 via CDM 2023; user report for `serial`] |
| `jweb`, `node.script` | not used | no statement found [open]; treat as unsupported (earlier note §A5) |

## 1. Official statements on Max for Live on Push 3 Standalone

### 1.1 Ableton help "Max for Live Devices on Push 3 (standalone)"

The HTML page (`help.ableton.com/hc/…/articles/8506527153308…`) returned **HTTP 403** to the
fetcher in three variants (en-us slug, de, bare id); web.archive.org is not reachable from here.
It was read through the Help Center's public JSON API
(`help.ableton.com/api/v2/help_center/en-us/articles/8506527153308.json`), title "Max for Live
Devices on Push 3 (standalone)", **updated 2026-11-19** [sourced]:

- Most Max for Live devices from the Core Library and Ableton Packs work on Push in Standalone
  Mode; some have limited parameter control; **third-party devices are not guaranteed**.
- Devices that show "missing or incompatible Max objects" are not supported on standalone; they
  are expected to work in Live with Push in Control Mode.
- Limitation classes: *limited control* (some parameters/modes can't be mapped, automated or
  controlled; Sets with existing mappings play back), *sample import disabled* (no new samples;
  presets referencing existing samples are fine), *playback only*, *does not work*.
- Modulators (LFO, Shaper, Envelope Follower, CV Tools …) are limited "because only automatable
  parameters can be controlled", so they cannot be mapped to new targets on Push.
- Sequencers: most built-in step sequencers accept no note entry on standalone (playback only).
- DS-Sampler and Granulator III: sample import disabled. Connection Kit devices (Arduino, Camera,
  OSC, Leap Motion, EV3, littleBits) and all "Inspired by Nature" devices do not work.
- **No list of unsupported Max objects** and no Max version in the article.

### 1.2 Push 3 Technical FAQ and tech specs

- "Due to the complexity of translating objects for Push 3, we cannot guarantee that all Max for
  Live devices (including self-built patches) will function as expected." Plug-ins (VST/AU) are not
  supported; freeze tracks with plug-ins before transfer. "By pairing Push 3 and Live, you can
  transfer your presets, samples, and devices over to Push 3." [sourced: FAQ via the JSON API,
  updated 2026-10-17; HTML page 403]
- Standalone processor: "Intel® 11th Gen Core™ i3-1115G4", 8 GB RAM, 256 GB SSD [sourced: tech
  specs]. That model is a 2-core/4-thread x86-64 laptop CPU [inference: Intel's published spec,
  not fetched]. "Arrangement View isn't currently supported on Push in Standalone Mode." [sourced]

### 1.3 Which Max runs on Push 3 Standalone

| Push / Live release (date) | Statement [sourced: Push 12 release notes, Live 12 release notes] |
|---|---|
| Live 12.0.5 (2024-06-05) | Live: "Updated the bundled Max to version 8.6.2" (desktop) |
| Live 12.1.5 (2024-12-12) | Live: "Updated the bundled Max build to 8.6.5" (desktop) |
| Live 12.2 (2025-06-11) | Live: "Updated the bundled Max version to the 9.0.7 official release build" — first Max 9 in Live; the Push notes of 2.2 name no Max version |
| Live 12.3 (2025-11-25) | Live: bundled Max 9.0.9, incl. "live.banks: support button assignments for parameter banks" |
| **Push 2.3.5** / Live 12.3.5 (2026-01-26) | Push notes: "Updated the bundled Max version to build 9.0.10", incl. a fix "on Push 3 … when disabling OpenGL in the context of Max for Live" |
| **Push 2.4** / Live 12.4 (2026-05-05) | Push notes, section **"Push 3 Standalone Mode Only"**: "Updated the bundled version of Max to 9.1.4" (+ "improved disabling of Jitter GL"); also "Max for Live parameters can now be displayed on Push when the new Parameter Visibility value in Max is set to Visible" (only when placed in a `live.banks` bank; not automatable) |
| **Push 2.4.5** / Live 12.4.5 (2026-08-26) | Push notes: "Updated Max 9.1.5 to 3db35fa" ("Parameters: fixed param visibility getting stuck after saving in Live") |
| Push 2.4.16 / Live 12.4.16 (2026-10-30) | newest; no Max line. Local desktop Live 12.4.16 bundles Max **9.1.5 (3db35fa476d)** [measured: `…/Max.app/Contents/Info.plist`] |

- Conclusion: Push 3 Standalone has run Max 9 at least since Push 2.3.5 (2026-01-26) and runs
  9.1.4 or later since Push 2.4 (2026-05-05) [sourced]. That it is the same 9.1.5 build as desktop
  Live 12.4.16 is [inference] (the Push notes name the same build `3db35fa`).
- Max 9 point releases target the standalone too: the Max 9.1.3 forum announcement lists "bug fixes
  for Jitter, ABL objects, Max for Live on Push 3 Standalone" [sourced: C74 forum announcement].
- Desktop Max 9.1.5 contains `v8`/`v8ui` (compiled into the Max binary; `v8ui_default.js`,
  `v8ui.svg` present) and the legacy SpiderMonkey engine (`libmozjs185.dylib`) that runs `js`,
  `jsui` and jspainter [measured: listing of Live's bundled `Max.app`]. Whether the Linux build on
  Push ships both engines is not documented → **[open]**.

### 1.4 Object-level statements (all from 2023, Max 8 era)

CDM, P. Kirn, "Inside the new Ableton Push…" (2023-05-23), quoting Cycling '74's Joshua Kit
Clayton [sourced, secondary report of a primary statement]:
- Will not work: `hi`, `serial`; "The majority of devices which do not rely upon Jitter, Java, Mira,
  or third party externals" should work; third-party externals (incl. RNBO-built ones at the time)
  unsupported; "JSUI does build for the standalone version"; gen-based devices supported;
  "there's currently no way to create custom UIs".
- CDM, "Making Max for Live devices work on Push and Push 3 standalone" (2023-09): externals not
  supported ("compiling to externals also won't work"); without `live.banks` "just an error message
  on your Push", also in controller mode; parameters to map "do need to be automated and stored"
  (true before the 12.4 Visible modes); platform detection on Push via `gestalt` (C74 tip); the
  author found `live.banks` the main sticking point [sourced: CDM].
- Ableton's M4L production guidelines: devices should ideally work on "Mac, PC and Push 3
  Standalone"; externals must be compiled separately for "Push 3 Linux" [sourced:
  `reference/m4l-production-guidelines.md` §OS Compatibility].
- User reports: a `serial` object made Push 3 refuse to load a project ("missing or incompatible
  Max objects"); dynamic UDP ports crashed Push 3 standalone; gen~ "fine"; devices with externals
  fail [user report: C74 forum search results for Push 3 standalone; "PUSH3 standalone + gen~"].
- Nothing found on `v8`, `v8ui`, `jspainter`, `jweb`, `node.script`, file access, `dict` or Blob
  parameters on standalone in any Ableton or C74 source (help article, FAQ, Push manual, Live and
  Push release notes, Max 9.1.0/9.1.3 notes, C74 forum search) [sourced: absence].

### 1.5 Getting a device onto Push 3 Standalone

- Pairing: Push in Standalone Mode on the same Wi-Fi; "Show Push" in Live's Library settings; the
  Push label appears in Live's browser with Push's Sets and User Library [sourced: Push 3 manual
  §5.5.1]. Samples and presets dragged "into the User Library folder within the Push label" go to
  the User Library on Push; before a Set transfer Live reminds you to freeze plug-in tracks and use
  Collect All and Save [sourced: §5.5.3]. A Set opened from Push is a separate copy [§5.5.2].
- Max devices: the FAQ says devices can be transferred [sourced]; guides and users drag the
  `.amxd` into the Push User Library and load it from Browse → Max for Live [user report:
  pushpatterns.com 2025-10-26; Elektronauts 2025-01: a device "was not found" until copied into the
  same User Library folder on Push].
- Freezing a Max device embeds "subpatchers, audio files, image files, Javascript code, or
  third-party Max external objects" [sourced: Max user guide `m4l/live_freezing.json`]. An
  unfrozen aliasing device needs `aliasing.gendsp`, `aliasing_pages.js`, `aliasing_display.js`
  and the painter `.js` files beside it → transfer the **frozen** copy (our release flow already
  freezes) [inference]. Whether Collect All and Save collects an unfrozen device's side files is
  not documented [open].
- Media: "Resolving missing media files is not possible on Push"; changed paths unlink samples
  [sourced: help "Presets on Push 3 (standalone)", updated 2026-09-18].

### 1.6 CPU

- No Ableton or C74 statement gives CPU guidance for Max devices on standalone [sourced: absence].
  Live 12.2: "The DSP load of some devices has been slightly reduced on Windows and Push in
  Standalone Mode" [sourced: Push 12 notes]. Live 12's Performance Impact indicators and the
  maxdevtools `cpu-reporter` device exist for measuring [sourced: maxdevtools README].
- For aliasing (5 voices, one gen~, 140 Params, Data tables, 30 fps v8ui Task) a CPU reading on the
  Push itself is the only reliable figure [open]. Headless `v8ui`/painter work should be small
  if Max does not paint without a window [inference, open].

## 2. Push banks

### 2.1 Without `live.banks`

- Since Live 10, a Max device without `live.banks` shows "No parameter mapped" on Push [user report:
  Ableton forum 2018, moderator [jur]: "In L10, you need to use the live.banks object."; C74 forum
  "live.dial / Push 2 in Max for Live"; CDM 2023].
- Why [inference: decompiled]: Push's `create_device_bank` uses `MaxDeviceParameterBank` whenever
  `device.get_bank_count() > 0`; that class reads only `get_bank_parameters(i)`, returns 8 empty
  slots when there are no banks, and names the bank "Main". Only when the count is 0 does Push fall
  back to the generic `DeviceParameterBank` (parameters 1… in chunks of 8, names "Bank 1"…). Max
  writes `patcher.parameters.parameterbanks = {"0": {"index": 0, "name": "", "parameters":
  ["-"×8], "buttons": ["-"×8]}}` into every saved patcher with parameters — found in C74's own
  help/clipping files that contain no `live.banks` object [measured: JSON scan of
  `C74/packages/…` and `C74/help/…`]. So the count is 1 and the bank is empty. **Checked by the main
  session (2026-11-25):** neither `Aliasing.amxd` nor `Aliasing B.amxd` (both written by
  `bootstrap_shell.py`) nor Live's `Max Instrument.amxd` template contains a `parameterbanks` block;
  38 of 225 Factory-Pack `.amxd` files do (e.g. Granulator II with named banks, GranulatorInput II with
  one empty `"-"` bank) [measured: JSON/byte scan]. Whether Max adds the empty default bank to a
  generated shell at load, so that Push shows "No parameter mapped" rather than the generic
  "Bank 1…" chunks, is [open] (P1).
- The older "Automapping Index" (`_parameter_mapping_index`, "Defines the order in which parameters
  are automatically associated to the controls on a control surface like Push, APC40") is still in
  the 9.2 and 9.1.5 refpages [sourced: `m4l-ref/paraminspector.maxref.xml`]; users used it for
  Push 2 order in the Live 9 era [user report: leico.github.io 2017]. Since Live 10 it is
  superseded by `live.banks` [user report: Ableton moderator 2018]. The "Order" attribute is recall
  order only [sourced: parameter_mode guide].

### 2.2 `live.banks` facts

- Messages `new <i> <name> [p0 … p7] [@buttons …]`, `edit <i> <name|-> [slot param …] [@buttons
  …]`, `delete`, `getcount`, `getname`, `getparameters`; `-` = empty slot; up to 8 encoder slots
  per bank; creating bank n on an empty device makes grey dummy banks 0…n-1; double-click opens the
  Parameter Banks window (editor only, disabled in Live); banks are saved with the device and can
  be changed at runtime "to reveal or hide particular parameters within a bank depending on device
  state" [sourced: `m4l-ref/live.banks.maxref.xml`]. No maximum bank count is documented [sourced:
  absence; open].
- "after adding a new parameter object to a device, you need to save the device before the
  parameter is available for mapping with live.banks" [sourced: `help/m4l/live.banks.maxhelp`].
- **Buttons:** `@buttons` assigns parameters to the buttons above the display; "The first display
  button is not available for parameters on Push, since it is already in use as the bank exit
  button" → 7 usable buttons [sourced: help patch]. Per-parameter "Control Surface Button Mode":
  Toggle (default), Trigger, Cycle (through enum values) [sourced: `parameters.maxref.xml`].
  "live.banks: support button assignments for parameter banks" came with Live 12.3's Max 9.0.9
  build [sourced: Live 12 notes]; Max 9.1.0 added "live.banks: changes are correctly displayed on
  Push after save" [sourced: Max 9.1.0 notes]; Push 2.3 fixed shifted button
  mappings and trigger behaviour [sourced: Push 12 notes].
- Which parameters can sit in a bank: "Automated and Stored", and since Max 9.1.3 / Live 12.4 also
  "Visible" / "Visible (Not Stored)" (not automatable, optional "Undo When Visible" off); "Stored
  Only" and "Hidden" are invisible to control surfaces [sourced: parameter_mode guide,
  `paraminspector.maxref.xml`, Push 2.4 notes].
- **Best of / Main bank:** the LOM's `get_bank_parameters(-1)` is the "Best of" bank [sourced: LOM
  MaxDevice]; Push prepends a "Main" bank when that is non-empty [inference: decompiled]. No
  `live.banks` message or saved key for it is documented [open: test whether Push shows a Main
  bank for an M4L device with banks].
- **Names:** bank names come from `live.banks`; Live's generic script strips non-ASCII characters
  from Max bank names [inference: decompiled `_Generic/Devices.py`]. Which parameter name Push
  shows (Long Name or Short Name), and how many characters fit in one of the 8 display columns, is
  not documented [open]. Old Max 5 docs: short names "generally in a range of 5 to 7 characters"
  [sourced: legacy Max 5 parameters refpage — about device labels, not Push]. Renaming parameters
  at runtime does not reach Push reliably [user report: C74 forum "Dynamic Strings on Push Display"].
- **Enums:** shown as text; "Enumeration Icons" lets an Enum parameter show images "on the Ableton
  Push controller" [sourced: parameter_mode guide]. Push 12.4 betas fixed M4L parameters moving
  "too fast" / "in very small increments" on Push [sourced: Push beta notes] → encoder feel of
  2001-step floats is [open].
- Bank paging: Push shows banks on the lower display buttons; devices with "more than eight pages"
  get an arrow to scroll further [sourced: Live 12 manual §36.10, Push 2].
- **9.2 → 9.1.5:** `live.banks`, `parameters` and `paraminspector` refpages are byte-identical in
  Max 9.2 and Live's 9.1.5 [measured: `diff -q`]; `live.banks.mxo` and `live.push.mxo` exist in the
  9.1.5 bundle [measured]. Button assignments need Live ≥ 12.3 (Max 9.0.9 build); Visible modes need
  Max ≥ 9.1.3 (Live ≥ 12.4) [sourced]. A bank layout saved in 9.2 should load in 9.1.5 [inference]
  [open: confirm in the bundled-Max round].
- `@active 0` parameters "are now greyed out on Push" since Live 12.1.10 [sourced: Live 12 notes].

## 3. `v8`, `v8ui`, `jspainter` on Push 3 Standalone (the key question)

- **Max version:** Push 3 Standalone runs Max 9.0.10 (since Push 2.3.5, 2026-01-26), 9.1.4 (since
  Push 2.4, 2026-05-05, stated under "Push 3 Standalone Mode Only") and 9.1.5 build 3db35fa (since
  Push 2.4.5, 2026-08-26) [sourced: https://www.ableton.com/en/release-notes/push-12/]. `v8`/`v8ui`
  exist in Max since 9.0, `jspainter` long before; Max 9.1.3 added "jspainter: Max for Live mapping
  overlay / automation dots" [sourced: Max 9.1.3 notes]. So there is **no version gap** of the kind
  "Push runs Max 8.6, `v8` does not exist there".
- **Platform build:** no Ableton or C74 page says whether the Linux build on Push includes the V8
  engine or the jspainter hook. The only engine-related statement is 2023's "JSUI does build for
  the standalone version" (legacy engine) [sourced: CDM quoting C74]. Ableton's article (2026-11-19)
  names no excluded objects [sourced].
- **Consequence if one is missing:** the device does not load at all on standalone ("missing or
  incompatible Max objects") [sourced: Ableton help; user report], so a missing `v8` would take the
  whole instrument down, not only the page script.
- **If they load:** Push shows no device GUI, so `v8ui` drawing and painters do nothing useful;
  only the `v8` page script's side effects on parameters matter [inference].
- **Mitigation if `v8` fails on Push:** move the page script to `js` (ES5 build, like the painters)
  or into patcher logic; drop `v8ui` from a "Push build" or replace it by `jsui` [inference].
- Verdict: **[open]** until a probe device has been loaded on a Push 3 in Standalone Mode.

## 4. `gen~` on Push 3 Standalone

- Supported: C74 named "gen-based devices" among what works (2023) [sourced: CDM]; a user reports
  devices with gen~ run fine [user report: C74 forum "PUSH3 standalone + gen~"]. gen~ compiles its
  code at load with a JIT; the Push CPU is x86-64 Intel [sourced: tech specs], so this is the same
  architecture as Intel Macs [inference]. No statement on compile time at load on Push [open].
- Authoring needs a full Max licence, running does not [sourced: CDM 2023; Max user guide
  "Max for Live Limitations"].
- RNBO: since Live 11.3.20 `rnbo~` is supported on Push standalone [sourced: CDM 2023]; not used.

## What aliasing needs

### A. `live.banks` (planned for v0.4, `TODO.md`)

1. Add one `live.banks` object to both shells and the bank layout below. Banks are saved in
   `patcher.parameters.parameterbanks` (`index`, `name`, `parameters`[8], `buttons`[8], `-` = empty)
   [measured: saved C74 patches]. Options: (a) the user builds them once in the Parameter Banks
   window and saves (the `.amxd` is the source of truth after bootstrap); (b) `bootstrap_shell.py`
   writes the block, then the user opens and saves once in Max so Max normalises it; diff with
   maxdiff. Ask before touching an `.amxd` that may be open (CLAUDE.md).
2. **Proposed layout** (137 automatable parameters; 9 core banks + 9 mod-matrix banks = 18 banks;
   Push pages past 8 with the arrow). Bank names ASCII only, short:

| # | Bank | Encoders 1–8 | Buttons 2–8 (mode) |
|---|---|---|---|
| 1 | Main | Write Pitch, Write Sym, Read Pitch, Read Spread, Size, Band Center, Drive, Output | Write Mode, Read Mode, Write Shape (Cycle), Read Shape (Cycle), Write State (Cycle), Gate, Sync (Trigger) |
| 2 | Write | Write Pitch, Write Rate, Write Mult, Write Div, Write Fine, Write Sym, Write State, Write Shape | Write Mode |
| 3 | Read | Read Pitch, Read Rate, Read Mult, Read Div, Read Fine, Read Spread, Read Shape, Size | Read Mode, Smooth |
| 4 | Band | Drive, Band Center, Band Width, Band Res, Band FM, Band Spread, Band Mode, Band Slope | Drive On, Band On |
| 5 | Reso/Voice | Res Freq, Res Feedback, Res Mix, Transpose, Width, Sync Rate, Resync, Gate | Res On, Res Track, Ramp AA, Sync (Trigger) |
| 6 | LFO 1 | LFO 1 Mode, Shape, Rate, Sync Rate, Phase, Spread, Retrig, – | – |
| 7 | LFO 2 | LFO 2 Mode, Shape, Rate, Sync Rate, Phase, Spread, Retrig, – | – |
| 8 | Env/Limit | Env Attack, Env Release, Env Gain, Limiter Gain, Saturation, Color, Limiter Release, Ceiling | Limiter On |
| 9–17 | M>WPitch, M>WSym, M>WGate, M>RPitch, M>RSpread, M>Size, M>BCenter, M>ResFreq, M>Output | the 8 sources of that target: LFO 1, LFO 2, Env, Velocity, Mod Wheel, Voice, Neighbour, Read Osc | – |

   - Covers all 65 non-matrix parameters once (Main repeats the eight most-played ones) and the 72
     matrix cells as 9 targets × 8 sources — the matrix maps exactly onto Push banks [inference].
     Whether a parameter may appear in two banks is [open] (native devices repeat parameters in
     their Best-of bank [inference]).
   - Main's choice (Write/Read pitch, Sym, Spread, Size, band centre, drive, output) is a proposal
     for the user to judge by ear [inference].
3. **Mode-dependent slots** (Pitch vs Rate, LFO Rate vs Sync Rate): keep both in the bank and set
   the inactive one `@active 0` from the page script so Push greys it out (Live ≥ 12.1.10)
   [sourced feature; open: whether `active` on a `live.dial` with a jspainter reaches Push].
   Alternative: `live.banks edit` at runtime to swap the slot [open: Push refresh].
4. **Clear** (now Hidden, momentary) → "Visible (Not Stored)", "Undo When Visible" off, button mode
   Trigger, on bank 1 or 2, so the table can be cleared from Push; keep `Page`, `Mod Target`,
   `Display Mode`, `Table` Stored Only (UI state, not for Push).
5. **Names on Push:** our long names put the source first ("LFO 1 > Write Pitch"), so a truncated
   slot still differs within a matrix bank, and the bank name carries the target [inference].
   Non-ASCII in enum items (`÷16 … ×16` in Sync Rate, `·` in the Page tab) may not render on Push
   [open]; bank names must be ASCII [inference: decompiled].
6. Consider Enumeration Icons for Write/Read Shape and LFO shapes (SVG/PNG) [sourced feature;
   optional].

### B. Standalone readiness

7. Treat **Push 3 Standalone as unsupported until tested**; release notes say "tested on macOS,
   Push 3 Control Mode; Standalone: [result]".
8. Build a **probe device** (repo test patch, not aliasing): `v8` (posts on load), `v8ui`, a
   `live.dial` with `jspainterfile`, small `gen~` with `Data` + `buffer~`, a `dict` Blob parameter,
   `plugsync~`, `live.banks` with one bank. Freeze it; load it on Push standalone. Outcome
   decides whether aliasing needs a `js` fallback.
9. Always transfer a **frozen** aliasing copy to Push (dependencies embedded) via the Push User
   Library; test a Set round trip (Mac → Push → Mac) with a written table (Blob) and non-default
   parameters.
10. `live.drop` + `sfinfo~` + `buffer~ read` (built, D50–D54): desktop-only feature; it never depends
    on a file path stored in the Set (the drop's parameter is Hidden) and writes the file into the Blob
    table, so the sound survives the transfer [code]. The objects themselves should load on Push:
    Granulator III has the same layering (a `live.drop` with ignoreclick behind its display, found by
    the main session's scan of the Factory Pack device) and Ableton lists it as "sample import
    disabled", not "does not work" [inference from sourced + measured]. On Push nothing can be dropped
    (no GUI); hiding the FIT | 1:1 pills there is not needed.
11. Measure CPU on Push (5 voices, worst-case settings), and load time (gen~ JIT) [open].

### C. Tests on hardware (user; `live-test` handover)

| # | Mode | Check |
|---|---|---|
| P1 | Tethered | Before `live.banks`: Push shows "No parameter mapped" (confirms §2.1) |
| P2 | Tethered | After `live.banks`: bank order and names, which name (long/short) per slot, truncation, enum text incl. `÷`/`×`, button modes, Main/Best-of bank presence, encoder feel of 2001-step floats, `@active 0` greying, Clear as Visible (Not Stored) |
| P3 | Tethered | Same with Live's bundled Max 9.1.5 (bundled-Max round) |
| P4 | Standalone | Probe device (B8): loads or "missing or incompatible Max objects"; console unavailable on Push → note behaviour only |
| P5 | Standalone | Frozen aliasing: loads, plays (Drone and MIDI), table restored from the Set, CPU meter, load time |
| P6 | Both | Set round trip Mac ↔ Push keeps parameters and table |

Needs a Push 2/3 (P1–P3) and a Push 3 with processor (P4–P6); if the user has neither, these
stay [open] and the release says so.

## Sources

Accessed 2026-11-25 unless noted.

Ableton (primary):
- Help "Max for Live Devices on Push 3 (standalone)", updated 2026-11-19 (HTML 403; read via the
  Help Center JSON API): https://help.ableton.com/hc/en-us/articles/8506527153308 ·
  https://help.ableton.com/api/v2/help_center/en-us/articles/8506527153308.json
- Help "Push 3 Technical FAQ", updated 2026-10-17 (HTML 403; JSON API):
  https://help.ableton.com/hc/en-us/articles/8483166334748-Push-3-Technical-FAQ ·
  https://help.ableton.com/api/v2/help_center/en-us/articles/8483166334748.json
- Help "Presets on Push 3 (standalone)", updated 2026-09-18 (JSON API):
  https://help.ableton.com/api/v2/help_center/en-us/articles/8896436237340.json
- Help "Supporting older Live versions with your Max for Live device", updated 2026-09-19 (JSON
  API): https://help.ableton.com/api/v2/help_center/en-us/articles/4406321223186.json
- Help Center search (to find the above):
  https://help.ableton.com/api/v2/help_center/articles/search.json?query=Max%20for%20Live%20Push%20standalone&locale=en-us
- Help "Optimizing CPU-Intensive Devices" — HTTP 403, not read: https://help.ableton.com/hc/articles/12911009486108
- Push with Live 12 release notes: https://www.ableton.com/en/release-notes/push-12/
- Push with Live 12 beta release notes: https://www.ableton.com/en/release-notes/push-12-beta/
- Live 12 release notes: https://www.ableton.com/en/release-notes/live-12/
- Push 3 manual (§1.3, §2, §5.5; no Max for Live section): https://www.ableton.com/en/push/manual/
- Push tech specs: https://www.ableton.com/en/push/tech-specs/
- Live 12 manual, Using Push 2 (§36.10): https://www.ableton.com/en/live-manual/12/using-push-2/
- Live 12 manual, Max for Live (§32.5 dependencies): https://www.ableton.com/en/live-manual/12/max-for-live/
- Ableton/maxdevtools (README; guidelines summarised locally): https://github.com/Ableton/maxdevtools
- Local: `reference/m4l-production-guidelines.md` (§Push Support, §OS Compatibility, checklist)

Cycling '74 (primary):
- live.banks reference: https://docs.cycling74.com/reference/live.banks
- LOM MaxDevice (`get_bank_count`, `get_bank_parameters`, best-of = -1): https://docs.cycling74.com/apiref/lom/maxdevice/
- Max 9.1.0 release notes: https://cycling74.com/releases/max/9.1.0
- Max 9.1.3 release notes: https://cycling74.com/releases/max/9.1.3
- Max 9.1.3 forum announcement: https://cycling74.com/forums/max-913-rnbo-143-released
- Legacy Max 5 parameters refpage (short-name length): https://docs.cycling74.com/legacy/max5/refpages/m4l-ref/parameters.html
- Local (Max 9.2): `/Applications/Max.app/Contents/Resources/C74/docs/refpages/m4l-ref/{live.banks,parameters,paraminspector,live.push}.maxref.xml`;
  `…/docs/userguide/content/{parameter_mode,mapping}.json`, `…/content/m4l/{live_limitations,live_freezing}.json`;
  `…/C74/help/m4l/live.banks.maxhelp`; saved `parameterbanks` in `…/C74/packages/Max for Live/clippings/Live UI Abstractions/Multi-Mapping.maxpat`,
  `…/C74/packages/ableton-dsp/help/*.maxhelp`, `…/C74/help/msp/gen~.maxhelp`
- Local (Live's Max 9.1.5): `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Max/Max.app/Contents/Info.plist`,
  `…/Resources/C74/docs/refpages/m4l-ref/` (diffed), `…/Resources/C74/externals/m4l/`, `…/Frameworks/libmozjs185.dylib`

Secondary (used to locate primary sources, or labelled):
- P. Kirn, CDM, "Inside the new Ableton Push…" (2023-05-23; quotes C74's Joshua Kit Clayton): https://cdm.link/inside-the-new-ableton-push/
- P. Kirn, CDM, "Making Max for Live devices work on Push and Push 3 standalone" (2023-09): https://cdm.link/2023/09/making-max-for-live-devices-work-on-push-and-push-3-standalone/
- Decompiled Live 12 control-surface scripts (unofficial; `_Generic/Devices.py`,
  `ableton/v2/control_surface/banking_util.py`, `…/device_parameter_bank.py`):
  https://github.com/gluon/AbletonLive12_MIDIRemoteScripts
- Cardamien/push3-max-lab (standalone part unverified by its author): https://github.com/Cardamien/push3-max-lab

User reports:
- Ableton forum, "MaxforLive 10/Push 2/parameters" (2018-02, moderator [jur]): https://forum.ableton.com/viewtopic.php?p=1735831
- C74 forum, "live.dial / Push 2 in Max for Live": https://cycling74.com/forums/live-dial-push-2-in-max-for-live
- C74 forum, "PUSH3 standalone + gen~": https://cycling74.com/forums/push3-standalone-gen
- C74 forum, "M4L Device's parameters seen by control surface": https://cycling74.com/forums/m4l-devices-parameters-seen-by-control-surface
- C74 forum, "Dynamic Strings on Push Display": https://cycling74.com/forums/dynamic-strings-on-push-display
- leico, "automapping index" (2017): https://leico.github.io/TechnicalNote/Live/automapping-index
- Elektronauts, "Max for Live devices that work with Push 3 Standalone", p. 8 (2024-12/2025-01): https://www.elektronauts.com/t/max-for-live-devices-that-work-with-push-3-standalone/198306?page=8
- Push Patterns, transfer guide (2025-10-26): https://www.pushpatterns.com/blog/how-to-transfer-max-for-live-devices-to-the-ableton-push-3-standalone
- Not readable: Isotonik transfer guide (HTTP 403), web.archive.org (not reachable from here).
