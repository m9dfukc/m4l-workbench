# M4L custom UI options and tempo sync for a one-gen~ instrument

Date: 2026-11-24 · Scope: Live 12.4.16, Max 9.2.0 (development), Live's bundled Max 9.1.5 (release
target) · Device context: `devices/aliasing/` (feedback items F3, F4, F6, F12–F15, F19 in
`devices/aliasing/docs/feedback-t1.md`; layout in `devices/aliasing/docs/gui.md`).

## Question

A. Which ways exist to give an M4L device a more modern face than stock `live.tab` / `live.text` /
`live.slider`, without losing what Live parameters give (automation, undo, MIDI map, Push, saving
with the Set), and which of them run on Max 9.1.5?
B. How does tempo, beat position and transport state get into a single `gen~` at signal rate, which
sync options do Ableton's own devices offer, and how can "synced rate + fine" and phase lock to
the song position be expressed in GenExpr?

## Summary

- **`jspainterfile` is the strongest option not yet on our list** [sourced: Max user guide
  "Custom UI Objects"]: a JS `paint()` (mgraphics) replaces the drawing of an existing UI object,
  including `live.dial` / `live.slider` / `live.gain~`, while the object keeps its parameter,
  mouse handling, automation, undo and Push behaviour. Its automation-dot / focus API
  (`jspainterautomation`, `isautomated`, `ismodulated`, …) is documented only in the 9.2 guide → **[open] on 9.1.5**.
- Stock `live.*` restyling goes further than our v0.1 used: `live.tab` / `live.text` / `live.menu`
  take PNG/**SVG pictures** with `remapsvgcolors` (theme-following icons), `rounded`, LCD
  appearances; `live.numbox` has slider/bipolar/LCD looks [sourced: refpages]. `live.dial`
  appearance 4 "Free" exists only in 9.2 → do not use for releases [sourced: refpage diff].
- Theme colours: dynamic colours on objects; in JS `max.getcolor("live_lcd_bg")` read inside
  `paint()` (re-called on theme change) [sourced: user guide "Dynamic Colors"].
- One big `v8ui` face needs **twin `live.*` parameters**; any value the patch sets on an
  "Automated and Stored" parameter goes into Live's undo history [sourced: Production
  Guidelines]. Undo granularity of a drag routed through a twin is **[open]**.
- `ParameterListener` (JS class, `jsparamlistener.mxo` present in both Max builds) observes and
  sets named parameters without patch cords, with `setvalue_silent` against feedback loops [sourced: JS API].
- `param_connect` links one parameter-aware UI object to one `gen~` Param (bidirectional, same
  patcher only) [sourced: user guide "Connecting Parameters"]: could replace most of the shell's
  dial→`gen~` cords. It does not make a `v8ui` drive several parameters.
- Newer visibility modes "Visible" / "Visible (Not Stored)" expose a parameter to Push without
  automation and can opt out of undo (`parameter_visible_undoable`); present in 9.1.5 [sourced].
- `jweb` (Chromium) has no parameter mode, renders on top in onscreen mode, spawns CEF helper
  processes; Push 3 standalone support is unknown → not recommended [mixed, see A5].
- Ableton's bundled M4L devices (LFO, Shaper, Envelope Follower, Expression Control, Drum Synths,
  …) are **encrypted** (`ciph` chunk) and could not be inspected [measured: this note, A6].
- Signal-rate sync: `plugphasor~` (0–1 per beat, sample-synchronised to Live) and
  `phasor~ <notevalue> @lock 1` are the signal sources; `plugsync~` and `transport` are
  message-rate only [sourced: refpages]. `gen~` has no transport operators; time enters via an inlet.
- Ableton LFO: Hz/Sync time mode, Phase, Offset, Jitter, Smooth, Hold, R (retrigger), Depth;
  Shaper greys out R in Sync (synced = locked to the song) [sourced: Live 12 manual].
- Proposed gen~ design [hypothesis]: one locked master ramp in, tempo derived in gen~ from its
  per-sample increment, divisions via `rate`/multiply-and-wrap, Fine as a phase offset (keeps the lock)
  or a ratio with re-lock on bar (A/B by ear).

Related notes (not repeated here): transport/timing basics and `---` names in
`max-port-targets-gen-rnbo-2026-11-24.md` (§ Timing); `v8` vs `js` engine in
`m4l-toolchain-dependencies-2026-11-24.md`.

---

## Part A — custom UI in M4L

### A1. Restyled `live.*` objects

Attribute lists from `/Applications/Max.app/Contents/Resources/C74/docs/refpages/m4l-ref/*.maxref.xml`
[sourced]; values unchanged in the 9.1.5 copy unless noted (diffed against
`…/Ableton Live 12 Suite.app/Contents/App-Resources/Max/Max.app/Contents/Resources/C74/docs/refpages/`).

| Object | Look-related attributes |
|---|---|
| `live.dial` | `appearance` 0 Vertical · 1 Tiny · 2 Panel · 3 Large · **4 Free (9.2 only; absent in 9.1.5)**; `needlemode` Automatic/Unipolar/Bipolar (since 8.6.0); `showname`, `shownumber`, `triangle`; colours `activedialcolor`, `activefgdialcolor`, `activeneedlecolor`, `dialcolor`, `fgdialcolor`, `needlecolor`, `panelcolor`, `textcolor`, `tricolor`, `tribordercolor`, `focusbordercolor` |
| `live.tab` | `appearance` 0 Default · 1 LCD; `mode`, `button`, `multiline`, `spacing_x/y`, `rounded`, `livemode` (Live-10 margins, 8.0); **`usepicture` + `pictures` (PNG or SVG)**, `usesvgviewbox`, **`remapsvgcolors`** (SVG recoloured with `textcolor`, 8.0); colour pairs off/on, active/inactive, LCD |
| `live.text` | `appearance` 0 Default · 1 Label (square button + text right) · 2 LCD; `text`/`texton`, `rounded`, `usepicture`/`pictures`/`remapsvgcolors`, `transition`, `outputmode` |
| `live.menu` | `appearance` 0 / 1 LCD (8.0); `usepicture`/`pictures`/`remapsvgcolors`; `hltcolor`, `tricolor` |
| `live.numbox` | `appearance` 0 Standard · 1 Triangle · 2 Slider · 3 Bipolar · 4 LCD; `activeslidercolor`, `tricolor2` |
| `live.slider` | `orientation`, `relative`, `showname`, `shownumber`, `slidercolor`, `modulationcolor`, `trioncolor` |
| `live.drop` | file-drop parameter; `legend`, `decodemode` |

- **Colours:** `live.*` objects default to dynamic colours that follow Live themes, including
  inactive colours; set a colour back to default to restore it; `live.colors` reports theme
  colours for anything else; Ableton Sans is bundled and should be the UI font [sourced:
  `reference/m4l-production-guidelines.md` §Live Color Themes, §Fonts]. Dynamic colours can be set
  by message (`elementcolor "…"`); the `themecolor` object lists/observes them; in v8/v8ui
  `max.getcolor(id)` returns RGBA and should be called in `paint()`, which Max calls again on a
  theme change; ids differ from `themecolor` display names [sourced: user guide
  `docs/userguide/content/dynamic_colors.json`, present in the 9.1.5 copy too].
- What our F3 complaint was about (9 pt text clipping in 44×15 tabs) is a sizing/appearance issue,
  not a hard limit: icon tabs (`usepicture` + SVG + `remapsvgcolors`) remove text clipping and stay
  theme-aware [hypothesis].

### A2. `live.*` + `jspainterfile` (custom drawing, native behaviour)

[sourced: `docs/userguide/content/custom_ui_objects.json`, example
`/Applications/Max.app/Contents/Resources/Examples/javascript/jspainter/` (overrides for dial,
slider, toggle, button, gswitch, ezdac~)]

- Set `@jspainterfile foo.js` on an existing UI object; `foo.js` implements `paint()` with
  mgraphics. `box.getvalueof()` (always an array) gives the value; `box.getattr(…)` the colours;
  `box.attrname_forstylemap("elementcolor")` maps style colours to the object's attribute names;
  `mgraphics.parentpaint()` draws the original look underneath/on top.
- 9.2 guide only: hidden jspainter attributes for parameter controls — `jspainterfocus`
  (focus border; 0 works only for live.gain/slider/dial), `hasfocus`, `jspainterautomation`
  (draw/hide automation, modulation and macro dots), `automationpoint x y`, `isautomated`,
  `ismodulated`, `ismacroassigned`; the guide's example applies them to `live.dial`.
  The 9.1.5 guide documents `jspainterfile`/`parentpaint` but none of these. String search: the
  dot attributes appear in the `live.gain~`/`live.meter~` externals of **both** builds; whether
  `live.dial` honours them on 9.1.5 is **[open]**.
- What stays native: the parameter (automation lanes, clip modulation, MIDI/key map, Push banks,
  undo, double-click to default) and mouse handling [hypothesis: jspainter replaces drawing only;
  the guide describes it as changing "the appearance"].
- Which JS engine runs jspainter scripts (legacy `js` or v8), hence ES5 vs ES2020 output, is
  **[open]** — check once; our TS build may need an ES5 target for these files.

### A3. One large `v8ui` face driving twin `live.*` parameters

- `v8ui`/`jsui` attributes [sourced: `max-ref/v8ui.maxref.xml`, identical in 9.1.5]: `border`,
  `embed`, `filename`, `jsarguments`, `nofsaa`, **`param_connect`**, **`parameter_enable`**,
  `parameter_mappable`. Mouse handlers `onclick`, `ondblclick`, `ondrag` (button 0 = drag end,
  usable as gesture end), a mouse-over handler; `mgraphics.redraw()` [sourced:
  `custom_ui_objects.json`].
- **Feedback-free sync.** Rule: the face outputs only on user gestures; values coming from the
  parameter only update the face's state and redraw. In patch cords that is the `set $1` idiom
  (the user guide's own pre-param_connect recipe uses `set` "to avoid creating a feedback loop")
  [sourced: `param_connect.json`]. In JS, `ParameterListener(name, fn)` observes a named
  parameter; `setvalue()` sets it and fires the callback, `setvalue_silent()` sets it without the
  callback, `getvalue()` reads it [sourced: https://docs.cycling74.com/apiref/js/parameterlistener/].
  `jsparamlistener.mxo` exists in `C74/jsextensions/max/` of both Max 9.2 and Live's 9.1.5
  [measured: file listing]. Whether `name` is the long name or the scripting name, and whether it
  works from `v8ui` in a device, is **[open]**.
- **Undo.** A `live.*` parameter set from inside the patch while "Automated and Stored" or "Stored
  Only" floods Live's undo history; the guidelines advise Hidden for parameters driven by other
  parameters [sourced: `reference/m4l-production-guidelines.md` §Undo History]. Hidden = not
  stored, not automatable, not on Push [sourced: `parameter_mode.json`]. A face that edits
  automatable twins therefore writes undo steps; whether a drag becomes one step or one step per
  value is **[open]** (test: drag in the face, check Edit → Undo). Visibility modes
  "Visible" / "Visible (Not Stored)" (Push-visible, not automatable) have "Undo When Visible"
  (`parameter_visible_undoable`) to leave undo [sourced: `m4l-ref/parameters.maxref.xml`; string
  present in the 9.1.5 binary]; the numeric `parameter_invisible` values for these modes are
  **[open]** (save one from the inspector and read it with `m4l-boxref`).
- **`param_connect`** [sourced: `param_connect.json`, refpages]: a bidirectional link between one
  parameter-aware UI object and one parameter of a supplier: Gen (`gen~`, codebox), `rnbo~`, ABL
  objects, `v8` attributes from `declareattribute`, `poly~` with `param` inside, `jit.gl.slab`.
  Path `<scriptingname>::<param>` (e.g. `gen~_AB::xyz`), set via inspector, Object Action menu or
  message. Limits: same patcher only (encapsulating the supplier breaks it), one parameter per UI
  object, multi-value UI objects use only their first value. Listed in "New in Max 9" →
  available in 9.1.5. Real use: Max's `ableton-dsp` demo patches connect `live.dial` /
  `live.menu` / `live.toggle` to `abl.device.*~` params this way [measured: scan, A6].
  For aliasing this could replace the `prepend <param>`→`gen~` wiring of all 25 controls
  [hypothesis]; it does not solve the multi-parameter `v8ui` face.
- **Variant A3b — one `v8ui` per control with `parameter_enable 1`.** Many plain Max UI objects
  (and `jsui`/`v8ui`) can own a Live parameter; JS provides it through `getvalueof()` /
  `setvalueof()` and calls `notifyclients()` after a user change [sourced: user guide
  `javascript.json`, `live_parameters.json`; https://docs.cycling74.com/apiref/js/jsthis/]. No twin
  needed, but automation/modulation dots, focus frame and value text must be drawn by hand, and
  the dot-state attributes are only documented for jspainter [hypothesis]. Undo per
  `notifyclients()` **[open]**.
- No `jsui`/`v8ui` box with `parameter_enable 1` exists in any readable patch shipped with Max 9.2
  or Live (7,795 `jsui`, 57 `v8ui` boxes scanned) [measured: A6] — Cycling '74/Ableton do not
  showcase this pattern locally.

### A4. Other image-based controls

- `pictctrl`, `pictslider`, `dial`, `slider`, `multislider`, `textbutton`, `umenu`, `tab`, … all
  have `parameter_enable` [sourced: grep of `max-ref/*.maxref.xml`], so they can be Live
  parameters with bitmap skins; they do not follow Live themes and lack Live's automation
  affordances [hypothesis].
- `panel` (shapes, rounded corners, gradients, shadows) and `fpic` (image) are decoration only
  [sourced: refpages]. `live.line` / `live.comment` for dividers and labels (already used).

### A5. `jweb` (Chromium Embedded Framework)

- Max embeds CEF; `jweb` shows a page; `@rendermode` offscreen (composited) vs onscreen ("slightly
  more efficient" but "always render on top of other objects"); page ↔ Max via the MaxBridge
  API: `window.max.bindInlet`, `window.max.outlet`, `getDict`/`setDict`, `executejavascript`
  [sourced: `docs/userguide/content/web_browser.json`]. Max ships CEF helper apps (`Max Helper
  (Renderer|GPU|Plugin).app`) [measured: `/Applications/Max.app/Contents/Frameworks/`].
- `jweb` has **no `parameter_enable`** [sourced: `max-ref/jweb.maxref.xml`], so every control
  still needs a twin `live.*` parameter (A3's undo and sync questions apply in full).
- Push: Push shows parameters as `live.banks` banks; "Push is the UI", the device face is not
  shown; third-party externals are unsupported on Push 3 standalone [sourced: CDM, Kirn 2023].
  Whether `jweb`/CEF runs on Push 3 standalone (Linux) is **[open]**; treat as unsupported.
- Windows: a forum thread reports no scrolling in `jweb` inside M4L on Windows [sourced, user
  report: https://cycling74.com/forums/jweb-and-max-for-live-no-scrolling-on-windows]. CPU and
  memory per device instance (one renderer per jweb), focus/keyboard capture in Live, and
  whether HTML/CSS/JS assets are collected by Freeze are **[open]** / [hypothesis: assets loaded
  by URL from the page are not seen by Freeze's dependency scan].

### A6. What Ableton's own devices do (local inspection)

- All 22 Max devices bundled with Live 12.4.16 under
  `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Builtin/Devices/` — LFO, Shaper,
  Envelope Follower, Align Delay, Shaper MIDI, Envelope MIDI, Expression Control (+ Legacy), MPE
  Control, Note Echo, MIDI Monitor, Drum Synth DS × 9, MIDI Tools Euclidean and Velocity Shaper —
  start `ampf … meta … ciph`: **encrypted**, no patcher JSON readable [measured: header dump +
  JSON scan, `$TMPDIR` scripts, 2026-11-24]. No Max for Live Essentials / "Building Max Devices"
  pack is installed in App-Resources; Factory Packs under `~/Music/Ableton` were not read
  (out of the allowed scope). PitchLoop89/Granulator are not in App-Resources.
- Readable references: Live's templates (`Misc/Max Devices/*.amxd`), and Max's
  `C74/packages/Max for Live/patchers/` example devices (saved by Max 6.0.7): plain `live.*`
  faces; sync via `phasor~ 4n @lock 1` (Tremellow) or `phasor~ @frequency 1 0 0 bars.beats.units
  @lock 1` plus a `live.menu` of note values `1nd 1n 1nt 2nd 2n 2nt 4nd 4n 4nt … 64n 128nd`
  (Flange-o-tron, Cyclotron) [measured].
- `param_connect` occurs only in `C74/packages/ableton-dsp/extras/Ableton DSP Objects.maxpat` and
  `C74/media/demos/abl-demo-parent.maxpat` (`live.dial`/`live.menu`/`live.toggle` →
  `abl.device.echo~_AA::feedback`, `abl.device.limiter~_AA::ceiling`, …) [measured].
- `jsui` faces with `presentation 1` exist only in Max's own UI patchers and examples, none
  parameter-enabled; `v8ui` only in tours/Jitter Tools (`mousethru.js`) [measured].

### A7. Recommendation table (all ratings [hypothesis])

| Option | Look | Effort | Automation / undo / Push | CPU | Risk on 9.1.5 |
|---|---|---|---|---|---|
| A1 Restyled `live.*` (SVG icon tabs, LCD/label appearances, dynamic colours, Ableton Sans) | native Live, cleaner than v0.1; limited | low | all native | lowest | low (avoid `live.dial` appearance 4) |
| A2 `live.*` + `jspainterfile` | free drawing per control (arcs, pills, icons, muted accents) | medium (one painter per control type, shared TS module) | all native; dots via `parentpaint` | low–medium (paint on change only) | medium: dot/focus API undocumented for 9.1.5, engine (ES5?) open |
| A3 One `v8ui` face + twin `live.*` (cords+`set` or `ParameterListener`) | anything, one coherent canvas | high (hit-testing, text entry, focus, map highlights, dots by hand) | automation via twins; undo granularity open; Push via twins + `live.banks` | medium (one large repaint per change) | medium: `ParameterListener` naming open |
| A3b `v8ui` per control, `parameter_enable 1` | anything per control | high | parameter native, dots/focus by hand; undo open | medium | medium |
| A5 `jweb` face + twins | web-grade | high + bridge protocol | as A3, plus no parameter mode | highest (Chromium process) | high: Push standalone, Windows, Freeze unknown |
| A4 `pictctrl`/`pictslider` | bitmap skins | medium (asset pipeline) | native parameter | low | low, but not theme-aware |

Suggested direction for aliasing: **A1 + A2 for all controls, `v8ui` only for the table display**
(F6/F9/F12 interactions: Size drag, line/2D toggle drawn in the display, with Size as one
automatable twin set from the display, written once per gesture). Test A2 on 9.1.5 first (G-items
below); fall back to A1 where a painter misbehaves.

---

## Part B — tempo sync inside a one-`gen~` instrument

### B1. Sources of tempo / position / transport state

| Object | Rate | What it gives | Notes |
|---|---|---|---|
| `plugphasor~` | **signal** | 0→1 ramp per beat, "sample-synchronized to the beat of the Ableton Live sequencer"; zero signal when the transport is stopped | [sourced: `msp-ref/plugphasor~.maxref.xml`] |
| `phasor~ <time> @lock 1` | **signal** | ramp locked to the Max/Live transport; frequency given as notevalues (`4n`, `1n`, `8nt`, `4nd`), ticks or bars.beats.units (`4.0.0`); frequency 0 when the transport is off; "Scheduler in Audio Interrupt must be enabled" for accurate timing; `@phaseoffset`, signal reset in the right inlet | [sourced: `msp-ref/phasor~.maxref.xml`, help patch] |
| `plugsync~` | message (continuous while the scheduler runs, or on `bang`) | 9 outlets: transport state, bar, beat, beat fraction, time signature, tempo **as samples per beat**, beats (1 PPQ, fractional), sample count, validity flags (2 beats, 4 timesig, 8 tempo, 16 transport) | [sourced: `msp-ref/plugsync~.maxref.xml`] |
| `transport` (unnamed) | message | bars, beats, units, PPQ, tempo, time signature, state, ticks; in a device bound to Live's transport, can report but not control it | [sourced: `max-ref/transport.maxref.xml`, `transport.json`, `m4l/live_timing.json`] |
| `translate` | message | converts note values ↔ ms/Hz/ticks against the transport; `@listen 1` re-outputs on tempo/time-signature change | [sourced: `max-ref/translate.maxref.xml`] |
| `rate~` / gen `rate` | signal | time-scales an input phase by a multiplier (<1 → several ramps per input cycle), with sync modes | [sourced: `msp-ref/rate~`, gen~ operators] |
| `live.param~ <name>` | signal | a parameter's value at signal rate (automation as an audio-rate ramp) | [sourced: `m4l-ref/live.param~`, `m4l/live_automation.json`] |
| `timepoint`, `metro @quantize` | message | events at transport positions | [sourced: `max-ref/timepoint`, `reference/m4l.md`] |

- `gen~` has no tempo/transport operator; `samplerate`, `phasor`, `rate`, `delta`, `latch`,
  `sah`, `wrap` exist [sourced: `docs/userguide/content/gen/gen~_operators.json`]. Time must enter
  as a signal inlet or a Param.
- Sample accuracy: only signal sources (`plugphasor~`, locked `phasor~`) are sample-accurate;
  message sources land per signal vector unless SIAI is on, and even then are delayed by a vector
  when going signal→message [sourced: `sample_accurate_messages.json`, `scheduler.json`]. Whether
  M4L forces SIAI/Overdrive is not stated in the local docs **[open]**. Behaviour of
  `plugphasor~`/locked `phasor~` at loop-brace jumps and tempo automation is **[open]**.
- Ableton's own LFO/Shaper could not be inspected (encrypted, A6). Ableton/C74's older example
  devices use `phasor~ … @lock 1` with a note-value `live.menu` [measured, A6].

### B2. Sync options in Ableton devices

| Device | Options [sourced: Live 12 manual] |
|---|---|
| **LFO** (M4L) | Rate with Time Mode Hz / Sync; ×10 (Hz); **Phase** 0–100 %; **Offset** (centre); **Jitter**; **Smooth**; **Hold** (freeze, resumes from held value); **R** retrigger (restarts from Phase); Depth; 9 waveforms (Sine, Up, Down, Triangle, Square, Random, Bin, Stray, Glider), Shape, Steps (≤24); Map/Multimap (8); Mod vs Remote; Bipolar/Unipolar |
| **Shaper** (M4L) | Rate Hz / Sync; Loop / 1-Shot (T button) / Manual; Phase; **R greyed out in Sync** (synced = song-locked); Offset, Jitter, Smooth, Depth |
| **Envelope Follower** | Delay in time or tempo-synced divisions |
| **Auto Pan-Tremolo** (native) | time modes Rate, Time, Synced, **Dotted, Triplet, 16th**; Phase Offset only in beat-division modes |
| **Auto Filter** (native) | LFO Rate + Mode, Phase, Phase Offset (tempo-synced modes only), Steps, S&H/Smooth |
| **Echo** (native) | Sync toggle: Rate in divisions vs Freq in Hz; Phase |

The manual does not list the LFO's synced division values [sourced: absence]; read them off the
device in Live if we want parity **[open]**.

### B3. Synced rate, fine and phase lock in gen~ terms [hypothesis throughout]

Shell: `plugphasor~` → `gen~` inlet `beat` (or `phasor~ 4.0.0 @lock 1` → `bar4` for a 4-bar
master); `plugsync~` outlet 0 (play state) and 5 (samples per beat) → Params `playing`, `spb`
for the stopped case.

```
// beat-rate from the master ramp itself (no message jitter)
History prev(0);
inc = beat - prev;  prev = beat;
inc = inc < 0 ? inc + 1 : inc;              // beats per sample while playing
bps = playing ? inc : 1 / max(spb, 1);      // fallback tempo when stopped
// synced pointer frequency for a division d (in beats, e.g. 0.25 = 1/16, 1/6 = 1/16T, 0.375 = 1/16D)
f_sync = bps * samplerate / d;
```

- **Free vs synced per pointer:** `f = mode ? f_sync * ratio : f_free`; `ratio` covers ×2^k
  octaves so a synced pointer can sit in the audio range (1/64 at 120 BPM = 32 Hz).
- **Fine in sync mode**, two meanings to A/B: (a) **phase offset** (0–1 of the division) — keeps
  the lock, like Ableton's "Phase Offset only in synced modes"; (b) **ratio detune** (±cents) —
  the pointer drifts and is re-locked at the next bar/division boundary (audible jump).
- **Phase lock to song position:** derive the pointer phase from the master instead of
  integrating: `ph = wrap(master * (L / d) + phase_offset, 0, 1)` with `L` the master length in
  beats (16 for `phasor~ 4.0.0`). Exact for divisions that divide `L` (all straight and triplet
  values up to 4 bars); dotted values (0.75 beat → 16/0.75) jump once per master cycle.
  Alternative: integrate freely and `latch`-reset on master wrap (`delta(master) < 0`).
- **Retrigger options:** on note (gate rising edge, already in the voice logic), on bar
  (master wrap), on transport start (`playing` 0→1). When stopped, `plugphasor~`/locked
  `phasor~` output zero/stand still, so a drone needs a free-running fallback (above) — the
  sound must not stop with the transport.
- Same scheme serves the Mod-page LFOs (F15): division menu + dotted/triplet as separate enum or
  combined list (`live.menu` of note values, like the C74 examples), Phase, Offset, Jitter
  (per-cycle `noise` latched at wrap, cf. `phasor~ @jitter`), Smooth, Hold, Retrigger mode
  enum (off / note / bar / transport).

### B4. Open checks (for the `live-test` handover)

| # | Check |
|---|---|
| G-UI1 | `jspainterfile` on `live.dial` and `live.tab` in Live with stock Max 9.1.5: paints, theme change repaints, automation/modulation dots via `parentpaint`, `jspainterautomation` honoured or ignored; engine (ES5 vs ES2020) |
| G-UI2 | Undo: drag a `v8ui` face that sets an automatable `live.dial` twin — one undo step per gesture or per value? Same for `notifyclients()` from a parameter-enabled `v8ui` |
| G-UI3 | `ParameterListener` from `v8ui` inside a device: which name resolves (long vs scripting), `setvalue_silent` behaviour |
| G-UI4 | `param_connect` `live.dial` → `gen~` Param inside a device (load, save, automation, 9.1.5) |
| G-SY1 | `plugphasor~` vs `phasor~ 4n @lock 1` inside `gen~`: alignment (null against each other), behaviour on stop, loop brace, tempo automation |
| G-SY2 | Derived tempo (`inc`) stability vs `plugsync~` samples-per-beat |

## Sources

Local (read-only):
- `/Applications/Max.app/Contents/Resources/C74/docs/refpages/max-ref/{v8ui,jsui,jweb,pictctrl,pictslider,panel,fpic,themecolor,transport,translate,timepoint}.maxref.xml`
- `/Applications/Max.app/Contents/Resources/C74/docs/refpages/m4l-ref/{live.dial,live.tab,live.text,live.menu,live.numbox,live.slider,live.drop,live.colors,live.param~,parameters}.maxref.xml`
- `/Applications/Max.app/Contents/Resources/C74/docs/refpages/msp-ref/{plugsync~,plugphasor~,phasor~,rate~,sync~}.maxref.xml`
- Same refpages in Live's Max 9.1.5: `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Max/Max.app/Contents/Resources/C74/docs/refpages/` (diffs: `live.dial` appearance "Free", `jweb`, `phasor~` lock text)
- User guide (compiled MDX): `/Applications/Max.app/Contents/Resources/C74/docs/userguide/content/{custom_ui_objects,param_connect,parameter_mode,dynamic_colors,web_browser,javascript,transport,scheduler,sample_accurate_messages,new_in_max9}.json`, `…/content/m4l/{live_userinterfaces,live_parameters,live_timing,live_limitations,live_automation}.json`, `…/content/gen/gen~_operators.json`
- `/Applications/Max.app/Contents/Resources/Examples/javascript/jspainter/`, `/Applications/Max.app/Contents/Resources/C74/jsui/jsui_live_barslider.js` (`max.getcolor` example)
- `/Applications/Max.app/Contents/Resources/C74/help/msp/{phasor~,plugphasor~}.maxhelp`
- `/Applications/Max.app/Contents/Resources/C74/packages/Max for Live/patchers/Max Audio Effect/{Tremellow,Flange-o-tron,Cyclotron}/*.amxd`
- `/Applications/Max.app/Contents/Resources/C74/packages/ableton-dsp/extras/Ableton DSP Objects.maxpat`, `/Applications/Max.app/Contents/Resources/C74/media/demos/abl-demo-parent.maxpat`
- `C74/jsextensions/max/jsparamlistener.mxo` in both Max builds
- `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Builtin/Devices/**.amxd` (encrypted)
- Repo: `reference/m4l-production-guidelines.md`, `reference/m4l.md`, `.claude/rules/max-patch.md`, `.claude/rules/v8-js.md`, `devices/aliasing/docs/feedback-t1.md`, `devices/aliasing/docs/gui.md`, `devices/aliasing/gen/aliasing.genexpr`

Web:
- Live 12 manual, Max for Live devices (LFO 33.2.3, Shaper 33.2.4, Envelope Follower, Expression Control): https://www.ableton.com/en/live-manual/12/max-for-live-devices/
- Live 12 manual, Audio Effect Reference (Auto Filter, Auto Pan-Tremolo, Echo, Delay LFO modes): https://www.ableton.com/en/live-manual/12/live-audio-effect-reference/
- Max JS API, ParameterListener: https://docs.cycling74.com/apiref/js/parameterlistener/
- Max JS API, jsthis (`notifyclients`, `getvalueof`, `setvalueof`, `declareattribute`): https://docs.cycling74.com/apiref/js/jsthis/
- LOM DeviceParameter (no gesture/undo API listed): https://docs.cycling74.com/apiref/lom/deviceparameter/
- P. Kirn, "Making Max for Live devices work on Push and Push 3 standalone", CDM, 2023: https://cdm.link/making-max-for-live-devices-work-on-push-and-push-3-standalone/
- Forum (user report): https://cycling74.com/forums/jweb-and-max-for-live-no-scrolling-on-windows
- Ableton help "Push (standalone) Max for Live Device compatibility" (HTTP 403 to the fetcher, not read): https://help.ableton.com/hc/articles/8506527153308

## Results (added 2026-11-25)

- **G-UI1, partly [measured: `devices/aliasing/test/smoke/run_smoke.sh`, standalone Max 9.2.1,
  2026-11-25]:** jspainter scripts run on Max's **legacy JS engine** (SpiderMonkey-style stack;
  `let`, arrow functions, template strings, classes rejected; `const` accepted), not v8. So
  painters must be ES5. On `live.dial` in 9.2.1: `max.getcolor`, `mgraphics.parentpaint`,
  `box.attrname_forstylemap`, `_parameter_range` exist; `jspainterautomation` can be set;
  `isautomated` / `ismodulated` / `ismacroassigned` read 0. Live and the bundled 9.1.5 are still
  [open] (aliasing test t3).
- G-UI5 (Blob storage) and G-SY1/G-SY2 (tempo sources) are still [open]; aliasing v0.2 uses a
  `dict` Blob parameter, `plugsync~` for state/tempo and `phasor~ 1.0.0 @lock 1` for bars.
