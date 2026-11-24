# Max as a port target for Reaktor ensembles: gen~, RNBO, MSP, poly~/mc

Date: 2026-11-24. Scope: the **Max side** of porting the Reaktor User Library "Aliasing Synth"
(5 voices, one audio table written and read at different speeds, HP+FM, LP+FM, notch) to a
code-first Max for Live instrument. The Reaktor internals and the toolchain dependencies are
covered by other reports.

Evidence markers: **[sourced]** = primary or forum source cited; **[inference]** = conclusion
drawn from sources; **[untested]** = code or recipe not run; **[open]** = must be checked in
Max/Live on this machine. "Local" sources are files of the installed Max 9.2.0
(`/Applications/Max.app`), the RNBO package 1.4.5 bundled with it, and the Live 12 Suite
content, all read without changing them.

## Executive summary

**Recommendation:** Put the **whole voice DSP in GenExpr text** (table write, table read,
oscillators, the HP/LP/notch chain with audio-rate FM) as one `.genexpr` function library,
hosted as `gen~ @gen aliasvoice` inside **`poly~ aliasvoice 5 @steal 1`**, which is the same
pattern Ableton uses in its own Poli instrument (`poly~ poligen 6 @steal 1` with `gen~`
inside) [sourced, local]. Each voice keeps its table in a gen~-local **`Data`** (no buffer~
naming problems, each poly~ instance has its own copy) [sourced]. Note allocation, voice
stealing and muting come from `poly~`/`thispoly~`; `live.*` parameters and v8 logic stay in
the thin `.amxd` shell, as the user's guide recommends. **mc.gen~ + mc.noteallocator~** is
the second choice (same GenExpr, one patcher, busy map instead of mute). **RNBO is not
recommended as the primary target**: in M4L it compiles on load unless exported to a Max
external, saving RNBO patchers needs an RNBO licence, and its patcher JSON is the least
LLM-friendly format; but `rnbo~` can host the same `gen~` code later for VST/web/C++ export
[sourced]. Numerics are the main port risk: gen~ computes in 64-bit doubles, while Reaktor
Core processes in 32-bit floats by default [sourced]; for an instrument whose sound *is* its
errors, the phase accumulators and the table storage need an optional float32 emulation and
an A/B test against the original (see Q4).

---

## Q1. The Max DSP landscape relevant for the port

### gen~ (Gen DSP)

- **What it is.** `gen~` compiles an embedded Gen patcher or GenExpr code to native machine
  code; the patcher can be loaded from a `.gendsp` file via the first argument or `@gen`
  [sourced: local refpage `msp-ref/gen~.maxref.xml`]. Everything inside is a 64-bit float:
  "All operations in gen~ use 64-bit doubles" and "everything is a 64-bit floating point
  number" [sourced: local user guide `gen/_gen_overview`].
- **Per-sample processing.** Gen patchers can "operate on a per-sample level, even with
  feedback loops"; many operators take durations in samples [sourced: `_gen_overview`].
  Feedback needs `History` (Z⁻¹) or `Delay` [sourced: `_gen_overview`, refpage
  `gen_dsp_history`].
- **Update-rate optimisation.** Calculations that do not need sample rate, "such as
  arithmetic on the outputs of param operators", run at the vector rate [sourced:
  `_gen_overview`, Technical notes]. Consequence for the port: a `Param` that sets a speed
  changes in steps at vector boundaries unless it is smoothed inside the code [inference].
- **GenExpr / codebox.** Codebox holds GenExpr; `require("mylib")` loads `mylib.genexpr` from
  the Max search path, required files can require others, each file loads once [sourced:
  local `gen/gen_genexpr`]. The user's guide notes that **nested `require` only works from
  Max 9.2.0**, while Live 12.4 ships Max 9.1.5 [sourced via guide → max-gen-helper]. A
  GenExpr call to an unknown function name falls back to a `.gendsp` abstraction of that name
  [sourced: `gen_genexpr`]. Abstractions are saved `.gendsp` patchers; their `Param`s act as
  named inlets, set from the parent with `setparam` [sourced: `_gen_overview`].
- **Declarations.** `Param`, `History`, `Data`, `Buffer`, `Delay` (order rules and the usual
  LLM pitfalls are already in the user's guide).
  - `Data name(len, chans)`: "A locally stored array of 64-bit values", default 512 samples,
    1 channel [sourced: refpage `gen_dsp_data`]. "Local to the Gen patcher, and cannot be
    read outside of it" [sourced: `_gen_overview`].
  - `Buffer name("buffer~name")`: a shared reference to an MSP `buffer~`; it "converts from
    the bit resolution of the MSP buffer~ object (currently 32-bit floats) for all read and
    write operations, and may be less efficient" [sourced: `_gen_overview`]. Setting the gen~
    attribute of that name "changes the MSP buffer~ referenced" [sourced: `_gen_overview`],
    i.e. a message `tbl <buffername>` rebinds it.
  - `Delay`: max length in samples (default = samplerate), interpolation modes as below,
    `@feedback 1` gives a minimum delay of 1 sample [sourced: refpage `gen_dsp_delay`].
- **Table operators** (attribute defaults read from the local refpages
  `Gen/docs/refpages/dsp/*.maxref.xml`) [sourced]:

  | Operator | Default `@index` | Default `@interp` | Default `@boundmode` |
  |---|---|---|---|
  | `peek` | samples | none | ignore (out of range → 0) |
  | `sample` | phase (0..1) | linear | ignore |
  | `wave` | wave (phase between start/end) | linear | wrap |
  | `lookup` | lookup (-1..1) | linear | clamp |
  | `nearest` | – | none (no interpolation) | – |
  | `poke` | samples | – | ignore (no write) |

  `@interp` accepts `none`/`step`, `linear`, `cosine`, `cubic`, `spline` (4-point
  Catmull-Rom), `spline6` (6-point B-spline); `@boundmode` accepts ignore, wrap, fold,
  mirror, clip, clamp [sourced: refpages `gen_dsp_peek`, `gen_dsp_sample`]. `poke` has an
  overdub inlet with `@overdubmode accum` (default) or `mix`; `splat` is the interpolating
  overdub write [sourced: refpage `gen_dsp_poke`, `_gen_overview`].
- **Other operators the port needs** (all present in the local refpage set): `phasor`
  ("A non-bandlimited sawtooth-waveform signal generator") [sourced: `gen_dsp_phasor`],
  `triangle` (ramp/triangle with movable peak, i.e. saw ↔ triangle ↔ inverted saw)
  [sourced: `gen~_operators`], `train`, `cycle`, `noise`, `mix`, `interp` (same mode list as
  above) [sourced: `gen_dsp_interp`], `dcblock`, `slide`, `latch`, `sah`, `change`, `delta`,
  `counter`, `accum`, `mtof`, `fixdenorm`, `samplerate`, `vectorsize`, `voice`, `voicecount`,
  `mc_channel`, `mc_channelcount` [sourced: local directory listing of
  `Gen/docs/refpages/dsp`].
- **Denormals.** `fixdenorm` is only needed for exported code; since Max 6 the audio thread
  flushes denormals to zero, and `delay`/`history` apply `fixdenorm` to their inputs by
  default [sourced: `gen_dsp_fixdenorm`].
- **`voice` / `voicecount`.** Inside a `poly~` they return the voice index / count (like
  `thispoly~`), otherwise 1 [sourced: `gen_dsp_voice`, `gen_dsp_voicecount`].
- **Code export.** `exportcode` exports the Gen patcher as C++; `@exportfolder`,
  `@autoexport` exist [sourced: refpage `gen~`]. Not available with a Max-for-Live-only
  licence [sourced: local `m4l/live_limitations`].
- **Compile cache.** `@nocache 0` (default) caches compiles "to save on load time" [sourced:
  refpage `gen~`]. Old forum reports that every `gen~` in a `poly~` compiles separately and
  slowly (Wakefield: still "re-compiled when loaded") predate this [sourced:
  [forum: gen~ in poly~ load time](https://cycling74.com/forums/gen-in-poly-take-a-long-time-to-load)];
  whether 5 voices load fast enough in Live is **[open]**.

### MSP

- Band-limited oscillators: `saw~` ("anti-aliased sawtooth"), `rect~`, `tri~` [sourced: local
  refpages]. `phasor~` is meant for "sample-accurate control and timing"; "for smoother
  sounding sawtooth generation, use the bandlimited saw~" [sourced: refpage `phasor~`].
  `cycle~` uses "an internal 64-bit 16K cosine wavetable" or a `buffer~` [sourced: `cycle~`].
- Filters: `svf~` is Chamberlin's state-variable filter with LP/HP/BP/notch outlets
  [sourced: `svf~`]; `lores~` is "an inexpensive lowpass" with resonance 0..1 [sourced];
  `filtercoeff~` computes `biquad~` coefficients at signal rate from frequency/gain/Q
  [sourced].
- `buffer~` stores 32-bit floats in memory [sourced via `_gen_overview` quote above]; its
  `@format` attribute only concerns the file on disk [sourced: refpage `buffer~`].

### poly~, mc, mc.poly~

- `poly~` loads one copy of an abstraction per voice; messages starting with `note` or
  `midinote` go to the first free voice; `thispoly~` marks busy/free (accepts a signal such
  as the `adsr~` output) and muted voices skip signal processing [sourced: local user guide
  `polyphony`].
- `@steal` "sends the data from the note or midinote messages to instances that are still
  marked busy; this can result in clicks"; off by default [sourced: refpage `poly~`].
- `@parallel` (multi-threaded voices) "is disabled when Max is hosted by the Live
  application" [sourced: refpage `poly~`].
- `up N` / `down N` resample the loaded patcher (powers of two), with resampling filters on
  by default [sourced: refpage `poly~`].
- `mc.poly~` keeps each voice on its own channel instead of summing; `mcs.poly~` collapses
  I/O to one multichannel cable [sourced: `polyphony`, `mc/mc_poly_without_polytilde`].
- MC without poly~: `mc.noteallocator~` (MIDI-driven) and `mc.voiceallocator~`
  (message-driven) maintain a **busy map**; wrapper objects with `@usebusymap 1` switch off
  processing of idle channels [sourced: `mc/mc_poly_newfeatures`].
- `mc.gen~` "contains individual instances of gen~ via the MC Wrapper", so it gets all
  wrapper features (busy map); one `.gendsp` loaded into `mc.gen~` is copied to all channels
  [sourced: `mc/mc_gen`, `mc/mc_gen_instances`].
- `mc.plugin~`/`mc.plugout~` carry multichannel I/O to/from Live [sourced:
  `mc/mc_maxforlive_interface`].

### v8 / js

"The JavaScript engine in Max always executes code in the low priority thread" [sourced:
local user guide `javascript`]. So v8 is for UI, presets, parameter mapping, never for
anything that must be sample- or note-accurate.

### RNBO

- `rnbo~` is a subpatcher with its own object family; RNBO patches export to C++, Web Audio
  (JS), VST/AU, Max externals, Raspberry Pi; it supports "sample accurate events, host
  transport sync, MPE & MIDI support, automatic polyphony"; "Gen also works inside of RNBO"
  [sourced: local user guide `rnbo`]. RNBO is "a paid add-on to Max" [sourced: same].
- Polyphony: `@polyphony` on the root patcher or any RNBO subpatcher; root always uses the
  `simple` voice controller, subpatchers can use `@voicecontrol user` with `mute`/`target`;
  simple stealing replaces the oldest voice [sourced:
  [RNBO polyphony](https://rnbo.cycling74.com/learn/rnbo-polyphony)]. Stealing can be
  disabled or customised in codebox [sourced:
  [voice stealing modes](https://rnbo.cycling74.com/learn/voice-stealing-modes)]; users
  report clicks on stealing [sourced:
  [forum](https://cycling74.com/forums/rnbo-clicks-when-voice-stealing)].
- `rnbo~` has `@exposevoiceparams` / per-voice parameter attributes, `export` messages for
  `cpp-export`, `web-export`, `vst-au-export`, `max-export`, and a "Restart the Buildserver"
  message [sourced: local refpage `RNBO/docs/refpages/max/rnbo~.maxref.xml`].
- RNBO `gen~` can load a `.gendsp` and expose gen params as RNBO params [sourced: local
  refpage `rnbo_gen~`].
- RNBO buffers: setting `size`/channels "might block audio processing" [sourced: local
  refpage `rnbo_buffer~`]. The earlier CA-synth study in the user's guide adds that RNBO
  buffers cannot be resized at runtime freely and cannot be passed as function arguments
  [sourced via guide].
- **rnbo~ inside a Max for Live device:** works. Since Live 11.3.1 "the version of Max that
  comes bundled with Live fully supports RNBO" [sourced:
  [RNBO and Max for Live](https://rnbo.cycling74.com/learn/rnbo-and-max-for-live)]. But "the
  internal RNBO patcher must be generated and compiled before the rnbo~ object can process
  audio", so the device loads slower; best practice is "to export your RNBO patch to a Max
  external before sharing your Live device" [sourced: same]. CDM: "RNBO patches will compile
  and run without a Max and RNBO license", while saving edited RNBO patches needs a full Max
  + RNBO licence [sourced: [CDM 2023](https://cdm.link/2023/05/rnbo-in-javascript-and-ableton-live/)].
  Exported Max externals are per-platform binaries (and need signing/notarisation on macOS
  for distribution) **[inference/open]**.
- Export licensing: code generated from a patcher is dual-licensed (Cycling '74 licence for
  Max-generated code or GPLv3); free commercial use for entities under $200k annual
  revenue/funding; RNBO engine source is MIT [sourced:
  [forum announcement](https://cycling74.com/forums/updated-license-terms-for-max-generated-code-for-export);
  the support FAQ pages returned HTTP 403 to the fetcher, so the current text is **[open]**].
- Numerics: RNBO C++ uses 64-bit doubles by default; `RNBO_USE_FLOAT32` forces "32-bit
  floats instead of 64-bit double values" [sourced:
  [Minimal Export](https://rnbo.cycling74.com/learn/minimal-export)].

---

## Q2. gen~ vs RNBO vs plain MSP for this port

| Criterion | gen~ (GenExpr) | RNBO | plain MSP |
|---|---|---|---|
| Per-sample table write+read in one tick, explicit order | Yes; order is the statement order in GenExpr, not definable in a visual patcher (Wakefield) [sourced: [forum](https://cycling74.com/forums/gen-gods-poke-and-peek-in-same-sample)] | Yes via codebox / gen~ inside RNBO [sourced: `rnbo` guide] | No: `poke~`/`index~` run per vector; order within a sample not controllable [inference] |
| Audio-rate FM of filters, single-sample feedback | Native (`History`) [sourced] | Native (codebox, `gen~`) | Only via signal-rate coefficient objects; feedback ≥ 1 vector [inference] |
| Polyphony | None built in; needs `poly~`, `mc.gen~`, or a hand-made allocator [sourced: Wakefield: "there isn't a general solution", [forum](https://cycling74.com/forums/implementing-poly-object-in-gen-codebox)] | Built in (`@polyphony`) [sourced] | `poly~`/mc |
| Per-voice tables | `Data` is per gen~ instance → automatically per voice [sourced: Data is local] | per-voice `data`/`buffer~` inside a polyphonic subpatcher **[open]** | `buffer~` names must be made unique per voice and per device [inference] |
| Numeric type | 64-bit everywhere; `Buffer` storage 32-bit [sourced] | 64-bit in Max **[open]**; C++ export can be 32-bit via `RNBO_USE_FLOAT32` [sourced] | 64-bit signal path (Max ≥ 6) [sourced: forum, Pask: Max "processes audio in 64-bit", [thread](https://cycling74.com/forums/comparing-gen-and-reaktor-core-level)]; `buffer~` 32-bit |
| Note timing | Notes arrive as Max messages → vector-quantised [inference] | "sample accurate events" [sourced] | vector-quantised |
| Load in M4L | compile on load, cached (`@nocache 0`) [sourced] | compile on load unless exported to an external [sourced] | instant |
| Text-as-source for an LLM | `.genexpr` plain text, small C-like grammar (rank 1 in the user's guide) | codebox text is fine, but the surrounding RNBO patcher JSON is undocumented (rank 6 in the guide) | patcher JSON only |
| C++ export for host tests | `exportcode` → C++ + genlib [sourced]; needs full Max licence [sourced] | C++ export, float32 switch [sourced]; needs RNBO licence | none |
| Licence needed to author in M4L | Saving Gen/MC patches needs a full Max licence, M4L-only users can only run them [sourced: `m4l/live_limitations`] | RNBO licence to save; RNBO only as add-on to standalone Max [sourced: CDM, search summary of C74 support] | M4L licence |

Further notes:

- **Same-sample write and read.** Wakefield: "Poking & peeking the same sample should be
  possible, though the order is obviously important"; GenExpr can make the order explicit,
  a patcher cannot. Max Gardener recommends a one-sample offset via `History` as the robust
  alternative [sourced: [forum](https://cycling74.com/forums/gen-gods-poke-and-peek-in-same-sample)].
  For the Aliasing Synth both orders are candidate behaviours of the original; implement
  both behind a compile-time constant and decide by A/B [inference].
- **Data sizes.** `Data` has "the size of its initial definition, or the size of the
  buffer~ object which was copied to it (whichever is smaller)"; `Buffer` always has the
  size of the referenced `buffer~` "(which may change)" [sourced: `_gen_overview`]. The
  original reportedly uses 1024-sample tables ×5 voices (see Q3) — tiny either way.
- **Data lifetime.** Forum posts (2013–2019) say Data and History are cleared when gen~
  recompiles, and that a sample-rate change triggers recompilation; users re-initialise with
  `change(samplerate)` or a History flag [sourced: search summary of
  [Gen~ Data object storage](https://cycling74.com/forums/topic/gen-data-object-storage),
  [fill data array only once](https://cycling74.com/forums/fill-data-array-only-once-at-gen~-init)].
  For this instrument a cleared table is harmless (it is rewritten continuously), but the
  current behaviour in Max 9.2 / Live is **[open]**.
- **buffer~ sharing between voices.** If a `Buffer` is used instead of `Data`: the `---`
  prefix is replaced per device at initialisation [sourced: local `m4l/live_symbols`], but a
  forum user got an error using `---` inside Gen; the suggested workaround is a message from
  the parent patch that rebinds the gen-internal name to the outer `---name` buffer~
  [sourced: search summary of [Using the "---" identifier in Gen](https://cycling74.com/forums/using-the-unique-identifier-in-gen)].
  A single `buffer~ ---atab 1024 5` (5 channels) with `channel = voice() - 1` would give
  one shared object for all voices plus a free waveform display [inference, untested].
- **CPU.** No published poly~ vs mc.gen~ benchmark was found; old gen~-vs-MSP benchmarks
  conflict [sourced: search summary of [Gen~ efficiency comparison](https://cycling74.com/forums/gen-efficiency-comparison)].
  C74 claims RNBO patches are "almost always" more CPU-efficient than equivalent Max patches
  and that "a single Max external will always load much faster than a large poly~ object"
  [sourced: [RNBO and Max for Live](https://rnbo.cycling74.com/learn/rnbo-and-max-for-live)].
  Five voices of table + 3 filters is a small load; measure rather than optimise early
  [inference].
- **Editing gen~ inside poly~.** gen~ "will only compile for the current voice"; save the
  voice patcher or run poly~ with one voice while editing [sourced:
  [fors-fm/lode README](https://github.com/fors-fm/lode)]. With `@gen` files edited as text
  and `gencheck`, this mostly disappears, but whether hot reload of a changed `.gendsp`
  reaches all 5 poly~ instances is **[open]**.

---

## Q3. Reaktor → Max mapping

Reaktor facts in this table come from the Reaktor 5.5 manuals (Application Reference, Core
Reference) or forum posts as marked; the other report covers Reaktor in depth. Facts about
the Aliasing Synth itself come from a third-party reimplementation thread
([scsynth.org](https://scsynth.org/t/replicating-aliasing-synth-a-gem-in-reaktors-user-library/9054)):
5-channel table of 1024 frames per voice, separate write and read phasors per voice, "in the
original synth, writeSig=readPos" (the written signal is the read position, i.e. a feedback
loop), phasors shaped as asymmetric triangles (saw ↔ triangle ↔ inverted saw), serial HP
then LP with audio-rate FM, a notch, and a saturator credited with "most of the 'fat'
character" [sourced, but unverified against the ensemble → **[open]**].

| Reaktor | Max / gen~ | RNBO | Notes / risk |
|---|---|---|---|
| Audio signal (Primary, per sample) | gen~ signal inside the voice; `in`/`out` | `~` objects / codebox~ | gen~ is 64-bit, Reaktor Core 32-bit by default [sourced: Core Ref. p. 133]; Primary assumed 32-bit **[open]** |
| Event signal, event order | Max messages outside gen~; inside gen~ use `change`/`delta`/`latch` on signals | events are sample-accurate [sourced] | Reaktor events are ordered and timestamped [sourced: App. Ref. 9.2]; Max messages into gen~ land on vector boundaries [inference] |
| Control rate (LFOs etc. send events at the Control Rate, saved with the ensemble) [sourced: App. Ref. p. 70–71] | emulate with a sample counter + `latch` at `samplerate/controlrate` inside gen~ | same in codebox | Staircase modulation may be part of the sound; read the ensemble's control rate **[open]** |
| Audio Table: write `In` at cell `WX` when `W` > 0; read at `RX` → `Out` automatically [sourced: App. Ref. p. 289–290] | `Data atab(1024)`; `poke(atab, x, wi)`; `peek(atab, ri, interp="linear", boundmode="wrap")` | `data`/`buffer~` + `poke~`/`peek~` or codebox | Fractional write index: Reaktor cell selection (truncate vs round) **[open]**; gen `poke` with fractional index **[open]** → make it explicit with `floor()`/`round()`; `splat` = interpolating write as an alternative error flavour |
| Audio Table interpolation: off or linear in X (Y, XY); Wrap also interpolates last→first, Clip does not [sourced: App. Ref. 11.2.4] | `@interp none` / `linear`; `@boundmode wrap` / `clamp` | `@interp`, `@boundmode` on peek~ | gen `wrap` + `linear` should interpolate across the seam like Reaktor Wrap **[open]** |
| Audio Table range clips incoming values (Min/Max) [sourced: App. Ref. 11.2.3] | `clamp(x, lo, hi)` before `poke` | `clip` | Easy to forget; affects the writeSig=readPos feedback |
| Same-sample read/write collision | statement order in GenExpr [sourced]; alternative 1-sample offset via `History` | codebox order | Reaktor's module order within a sample **[open]** (Reaktor report); keep both orders switchable |
| Event Table (event-triggered read via `R`) [sourced: App. Ref. p. 289] | `Data` + `peek` on `change()` triggers, or `coll`/`dict` outside DSP | `data` / `list.*` | – |
| Ramp / phasor oscillators (Primary) | `phasor` (non-band-limited) [sourced] or own accumulator with `History` + `wrap` | `phasor~` [sourced] | The accumulator **precision** decides the "careless speed" errors (Q4) |
| Asymmetric triangle "phasor" (per scsynth thread) | `triangle(phase, duty)` [sourced: gen~ operators] | `triangle~` | Exact Reaktor shape and its corner behaviour **[open]** |
| Sine / Saw / Pulse oscillators | naive: `cycle`, `phasor`, `phasor < pw`; band-limited only in MSP (`saw~`, `rect~`, `tri~`) [sourced] | `saw~`/`rect~` are anti-aliased [sourced]; `phasor~` is not | Aliasing is the desired sound: use **naive** gen versions unless the original uses band-limited Reaktor oscillators **[open]** |
| Multi 2-pole / HP & LP 1/2/4-pole with FM input | own TPT/ZDF SVF or biquad in GenExpr with per-sample coefficients | `svf~`, `biquad~` + `filtercoeff~`, or codebox | `svf~` is Chamberlin (unstable towards Nyquist) [sourced: refpage, inference]; Reaktor's exact topology, cutoff law (pitch vs Hz), FM scaling and Nyquist clipping **[open]** |
| Notch | SVF notch output or biquad notch in GenExpr; MSP `svf~` notch outlet [sourced] | `svf~` notch | – |
| Saturator | `tanh` + `dcblock` | `tanh`, `dcblock~` | Reaktor saturator curve **[open]** |
| Core macro / Core cell | GenExpr function in a `require`d `.genexpr`, or a `.gendsp` abstraction [sourced] | codebox function / `gen~` | Functions cannot see `Param`/`History` by name; pass them as arguments (guide) |
| Core FP Precision property (default / 32 / 64 bit) [sourced: Core Ref. p. 133–134] | no type switch; emulate float32 (Q4) | `RNBO_USE_FLOAT32` only in export [sourced] | – |
| Denormal Cancel (Core) [sourced: Core Ref. 5.5] | not needed in Max; `fixdenorm` only for exported code [sourced] | `fixdenorm` | – |
| Voice (Reaktor instrument voices, voice allocation) | `poly~ … 5 @steal 1` + `thispoly~`; or `mc.noteallocator~` + `mc.gen~ @bz 1` | `@polyphony 5` | Reaktor stealing mode/unison **[open]**; poly~ stealing may click [sourced] |
| Voice Combiner (sum of voices) | `poly~` sums its outputs; `mc.poly~` → `mc.mixdown~`/`mc.op~` [sourced] | voices summed at `out~` | Sum before or after the filter chain? Determines CPU and sound **[open]** |
| Note Pitch / Gate (velocity) | `notein` or `midiin` → `midiparse` → `poly~ midinote p v`; inside voice `in 1` → `mtof` | `notein`, `mtof` | Pitch-bend/MPE via `mpeevent` possible [sourced: `polyphony`] |
| Sample & Hold (event-triggered) | `latch` / `sah` in gen~ [sourced] | `latch~`, `sah~` | – |
| Smoother / event → audio | `slide` or one-pole with `History` in gen~; MSP `line~` | `slide~`, `rampsmooth~` | gen `Param` updates per vector [sourced] → always smooth speed params inside gen~ |
| Panel knob / fader | `live.dial` / `live.numbox` → gen~ `Param` | `param` → `rnbo~` | Live parameter resolution for "finest moves in speed" **[open]**; consider coarse+fine knobs |
| Snapshots | Live device presets; `pattrstorage` in Parameter Mode stores its whole state [sourced: `m4l/live_limitations`] | RNBO presets (`@autosave` snapshot attribute) [sourced: rnbo~ refpage] | Morphing between snapshots needs explicit pattr interpolation |
| Ensemble sample rate (saved with the ensemble) [sourced: App. Ref. p. 70] | `samplerate` from Live; fixed at host rate | host rate | Table aliasing patterns depend on SR: decide whether speeds are in Hz or in samples/sample **[open]** |

---

## Q4. Numerics

**Facts.**

- Reaktor Core: "By default all processing in Reaktor Core is done in 32 bit floats", "at
  minimum", with 64-bit floats "occasionally" used for intermediate results; per-module and
  per-macro FP Precision property (default / 32 / 64 bit) [sourced: Reaktor 5.5 Core
  Reference p. 133–134]. Core signals *and memory storage* are 32-bit by default [sourced:
  same page]. Reaktor 6 is a 64-bit application [sourced: title of an NI support article
  referenced in an [NI forum thread](https://community.native-instruments.com/discussion/comment/168818)];
  that concerns the binary, not the float width.
- Reaktor Primary modules: float width not documented in the sources read **[open]** (the
  Reaktor report should settle it); [inference] 32-bit.
- gen~: 64-bit doubles everywhere; `Data` 64-bit, `Buffer` storage 32-bit [sourced].
- MSP: 64-bit signals since Max 6 [sourced: forum, Pask]; `buffer~` memory 32-bit [sourced].
- RNBO: 64-bit by default, 32-bit in exported C++ with `RNBO_USE_FLOAT32` [sourced].

**Where 32 vs 64 bit changes this instrument** [inference]:

1. **Phase/position accumulators.** A table position near 1024 stored as float32 has a
   resolution of 2⁻¹³ ≈ 1.2·10⁻⁴ samples (24-bit mantissa); increments smaller than half of
   that are lost and larger ones are rounded. In 64-bit the same position resolves to
   ≈ 2·10⁻¹³. If the original accumulates read/write positions in 32-bit, "finest moves in
   speed" produce quantised, position-dependent speed errors that a double accumulator will
   not reproduce. This is the most likely audible difference.
2. **Table storage.** If the written signal is the read position (writeSig=readPos), the
   value stored is a float32-rounded position; with interpolation, the reconstructed values
   then carry those rounding errors. A 64-bit `Data` stores them exactly.
3. **Filter states** with FM: 32-bit states add noise and different limit-cycle behaviour
   at low cutoffs. Probably less audible than 1 and 2.

**How to reproduce float32 in gen~** [untested]:

- **Storage for free:** write the table through a `Buffer` bound to a `buffer~` — every read
  and write converts to 32-bit float [sourced]. The conversion is presumably an IEEE
  double→float cast (round-to-nearest-even) [inference].
- **Arithmetic emulation:** a GenExpr helper applied after every state update
  (accumulators, filter states), e.g.

  ```c
  // float32 rounding emulation, normal range only [untested]
  f32(x) {
      ax = abs(x);
      e = floor(log2(ax));          // binary exponent
      q = exp2(e - 23);             // one ULP of float32 at that exponent
      y = round(ax / q) * q;        // gen round: ties away from zero, IEEE: ties to even
      return (ax < 1.1754943508222875e-38) ? 0 : sign(x) * y;
  }
  ```

  Caveats: `log2` near exact powers of two can be off by one (re-check `ax / exp2(e)` in
  [1, 2)); gen `round` rounds halves away from zero [sourced: gen~ operators "Numeric
  round"], IEEE rounds ties to even, so exact ties differ; subnormals are flushed. Cost: a
  `log2`, an `exp2` and a division per call; for ~10 states × 5 voices this is acceptable
  [inference].
- **Validation path:** export the gen~ voice to C++ (`exportcode`) and build two host
  variants: (a) as is (double), (b) with `f32()` on; compare both against renders of the
  original Reaktor ensemble with identical speeds. RNBO's `RNBO_USE_FLOAT32` export is an
  alternative fully-32-bit reference build [sourced flag; workflow inference].

**Interpolation modes:** Reaktor Audio Table offers off / linear (X, Y, XY) [sourced]; gen
`peek` default none, `sample` default linear, plus cosine/cubic/spline/spline6 [sourced].
Map Reaktor "off" → `peek @interp none` (or `nearest`) and "X" →
`@interp linear` with `@boundmode wrap` when the table wraps. Whether Reaktor's "off"
truncates or rounds the read index is **[open]** and changes the error pattern; implement
with an explicit `floor()` or `round()` on the index rather than relying on defaults.

---

## Q5. Max for Live specifics for this instrument

- **Device type:** Max Instrument (the Live 12 template `Max Instrument.amxd` ships at
  `…/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/`) [sourced: local
  file]. MIDI from Live arrives at `midiin`/`notein`; M4L uses Live's MIDI, not the system
  drivers [sourced: `m4l/live_limitations`, `m4l/live_midieffects`].
- **Polyphony patterns in real devices:** scanning the 335 `.amxd` files in Live 12 Suite
  and the installed packs: Ableton's **Poli** uses `poly~ poligen 6 @steal 1` with
  `gen~ poligen` and `thispoly~` inside, plus `---` sends; **Bass** uses `poly~` for
  oversampling (`poly~ redfilter up 2` around a `gen~ @t zdfLadder`) and `poly~ Bass_LFO
  down 8`; no bundled device uses `mc.noteallocator~`/`mc.voiceallocator~` or `rnbo~`
  [sourced: local scan of `~/Music/Ableton/Factory Packs/Max for Live Essentials/Max
  Instrument/{Poli,Bass}.amxd`]. So poly~ + gen~ is the proven M4L pattern [inference].
- **poly~ in Live:** `@parallel` is disabled under Live [sourced]. Muting idle voices is the
  main CPU lever "in the context of a custom Max for Live synthesizer" [sourced:
  `polyphony` guide].
- **MC in M4L:** user-initiated MC connections need a standalone Max authorisation; runtime
  and scripted connections work [sourced: `m4l/live_limitations`].
- **Parameters, automation, modulation:** `live.*` objects are stored with the Set; Live
  can modulate parameters in unipolar, bipolar, additive or absolute mode (Clip Modulation
  Range) [sourced: `m4l/live_parameters`]. `pattr` only persists if Parameter Mode is on
  [sourced: `m4l/live_limitations`]. Whether Live's parameter path keeps enough resolution
  for "finest moves in speed" (automation, MIDI mapping, push encoders) is **[open]**;
  design a coarse + fine speed pair or an exponential/fine-tune range.
- **Device-local names:** `---` is replaced by a unique number at initialisation, for
  `buffer~`, `send`/`receive`, `coll`, `table` [sourced: `m4l/live_symbols`]; the number
  changes between loads [sourced: search summary of [buffers name conflicting](https://cycling74.com/forums/buffers-name-conflicting-in-instatiations-of-same-device)].
  `send~`/`receive~` between devices are not supported [sourced: `m4l/live_limitations`].
  With `Data` per voice none of this is needed.
- **Sample rate:** gen~ exposes `samplerate`; Data/History may be cleared on the recompile
  that a sample-rate change triggers (old forum evidence) [sourced]; behaviour in Live 12 is
  **[open]**. Musically more important: the aliasing pattern of a fixed 1024-sample table
  depends on the host rate (Q3 last row).
- **Timing:** Live's transport is the clock for unnamed `transport` objects [sourced:
  `m4l/live_timing`]; notes reach `poly~` as messages, so note-on time is vector-quantised
  in M4L (RNBO would be sample-accurate) [inference]. For a drone/pad instrument this is
  acceptable.
- **Latency:** an instrument without lookahead needs no Defined Latency (the user's guide
  covers the patcher-inspector field) [inference].
- **Freezing:** a frozen device bundles dependencies (subpatchers, JS, externals); files
  inside the frozen device win over files on disk [sourced: `m4l/live_freezing`]. Whether
  freezing picks up `require`d `.genexpr` files (not only `.gendsp`) is **[open]** — test
  the frozen device on a clean machine or with the source folder renamed.
- **Max version:** Live 12 bundles Max 9 (here 9.1.5); a different Max can be set in Live's
  File & Folder settings, Live restart required [sourced: search summary of
  [Live 12 manual: Max for Live](https://www.ableton.com/en/live-manual/12/max-for-live/)
  and [Recommended Max versions](https://help.ableton.com/hc/en-us/articles/209772305)].
  Target 9.1.5 compatibility (no nested `require`) unless Live is switched to 9.2.0.
- **Licences for authoring:** saving patches that use Gen or MC needs a standalone Max
  licence; with only an M4L licence they can be run but not authored [sourced:
  `m4l/live_limitations`]. Which licences this machine holds (Max, RNBO) is **[open]**.

---

## Q6. Real-world examples

Local (installed, readable):

- Ableton **Poli** and **Bass** (Max for Live Essentials pack): poly~ + gen~ voice pattern,
  poly~ oversampling of a gen~ ZDF ladder [sourced: local scan].
- Max 9.2 gen examples in `/Applications/Max.app/Contents/Resources/Examples/gen/`:
  `gen~.interpolation.maxpat`, `gen~.chopper.maxpat` / `gen~.slicer.maxpat` (buffer
  read/write), `gen~.buffer.sort.maxpat`, `gen~.bitcrush.maxpat`, `gen~.moogladder.maxpat`
  + `moogLadderFilter.genexpr`, `poly.moogladderx2.maxpat` (poly~ oversampling) [sourced:
  local listing; contents not reviewed].
- RNBO package ships GenExpr files used by its build server
  (`RNBO/server/node_modules/@rnbo/genexpr_js/genexprs/*.genexpr`, e.g. `slide`, `chorus`,
  `gigaverb`) [sourced: local listing].

Online:

- [fors-fm/lode](https://github.com/fors-fm/lode) — MIT M4L synth + device template; DSP in
  a single gen~ codebox, `poly~` for polyphony and voice muting, `dict ---parameters` for
  UI config [sourced].
- [SHARING: poly object in gen codebox](https://cycling74.com/forums/implementing-poly-object-in-gen-codebox)
  — voice allocator written in GenExpr with `Data` arrays (Ernest/Yofiel); Wakefield's
  simpler allocator and caveats (one event per sample, chords) [sourced].
- [Yofiel synth and gen~ DSP library](https://cycling74.com/projects/yofiel-synth-and-gen~-dsp-library),
  [Husserl2](https://cycling74.com/projects/husserl2-polyphonic-synthesizer-download) — gen~
  polysynths (audio path in gen~) [sourced: search summaries only, not reviewed].
- [Comparing gen and Reaktor core level](https://cycling74.com/forums/comparing-gen-and-reaktor-core-level)
  — early (Max 6) thread; Joshua Kit Clayton: Reaktor users gain less from gen~ because
  Reaktor "is focused on high level objects, which are already compiled in C" [sourced].
- [Building Blocs - Reaktor to Max/Msp](https://cycling74.com/forums/building-blocs-reaktor-to-maxmsp)
  — a partial Reaktor (Skrewell) → gen~ port attempt; outcome unclear [sourced: search
  summary only].
- [scsynth.org: Replicating Aliasing Synth](https://scsynth.org/t/replicating-aliasing-synth-a-gem-in-reaktors-user-library/9054)
  — SuperCollider reimplementation (code in PlaymodesStudio/oceanodeSynthdefs) with table
  size, writeSig=readPos, filter chain [sourced]. The most useful external reference for the
  algorithm; a SuperCollider render could serve as a second reference next to Reaktor.
- RNBO: [RNBO and Max for Live](https://rnbo.cycling74.com/learn/rnbo-and-max-for-live)
  (example project needs the RNBO Synth Building Blocks package) [sourced].
- Oopsy (gen~ → Electrosmith Daisy) shows that exported gen~ C++ runs outside Max; external
  `Buffer`s are not supported there, `Data` is the workaround [sourced: search summary of
  Electrosmith forum threads].

No documented, complete Reaktor → gen~/M4L port of a table-based synth was found.

---

## Q7. Recommendation

### Layer assignment

| Layer | Holds | Why |
|---|---|---|
| **gen~ voice (`aliasvoice.genexpr` → `aliasvoice.gendsp`)** | write phasor, read phasor (asymmetric triangle shapes), `Data atab(1024)`, write/read with explicit order and index rounding, optional `f32()` emulation, HP+FM, LP+FM, notch, saturator, DC block, parameter smoothing, control-rate emulation | Per-sample, single-sample feedback, explicit ordering, text source, C++ export for host null tests [sourced capabilities; choice inference] |
| **poly~ `aliasvoice 5 @steal 1`** (thin `.maxpat` wrapper: `in 1` → `midinote` handling, `thispoly~`, `gen~ @gen aliasvoice`, `out~`) | voice allocation, stealing, muting, summing | Proven Ableton pattern; `Data` automatically per voice [sourced; inference] |
| **`.amxd` shell** | `midiin`/`notein` → `poly~`, `live.*` parameters → gen~ `Param`s (via `target 0` broadcast), `plugout~`, limiter during development | Thin shell per the user's guide |
| **v8 (from TS)** | snapshot/preset logic, coarse+fine parameter mapping, UI text | Low-priority thread is fine for this [sourced] |
| **Host tests** | gen~ `exportcode` C++ + small driver (render WAV per parameter set), compared to Reaktor renders and to the scsynth reimplementation | Reproducible A/B of the numerics question |
| **RNBO (later, optional)** | `rnbo~` with `@polyphony 5` hosting the same `aliasvoice.gendsp` via RNBO `gen~`, for VST/web export or a float32 reference build | Keeps the door open without paying the M4L costs now [sourced capabilities] |

Fallbacks: **mc.gen~ + mc.noteallocator~ `@bz 1`** if poly~ editing/reload is painful (one
patcher, per-channel gen~ instances, busy map) [sourced features]; **one gen~ with a
5-voice loop** (allocation in v8 or a GenExpr allocator) if exact voice-sum order or a
single C++ export of the whole instrument becomes important [inference].

### Open questions to test in Max/Live

1. Which Max does Live use here (9.1.5 bundled vs 9.2.0)? Which licences are authorised
   (standalone Max for Gen authoring and `exportcode`; RNBO)? **[open]**
2. Does a changed `aliasvoice.gendsp` (from `gencheck --write-gendsp`) hot-reload into all
   5 poly~ instances, in Max and inside a Live device? **[open]**
3. Load time of 5 × gen~ in poly~ in Live (compile cache). **[open]**
4. Same-sample `poke`→`peek` vs `peek`→`poke` order in GenExpr: does the generated code
   honour statement order (inspect exported C++)? **[open]**
5. gen `poke` with fractional index: truncation, rounding, or ignore? **[open]**
6. `peek @interp linear @boundmode wrap`: interpolates across the seam (last→first)? **[open]**
7. A/B: double vs `f32()` accumulators vs `Buffer`-stored table against Reaktor renders at
   identical speeds; is the difference audible/measurable? **[open]**
8. Ensemble sample rate and control rate of the original; behaviour at Live's 44.1/48 kHz;
   whether speeds should be Hz or samples/sample. **[open]**
9. Do Data/History survive a sample-rate change or a device reload in Live 12? **[open]**
10. Live parameter resolution for very small speed changes (automation, MIDI map, Push);
    need for coarse+fine controls. **[open]**
11. Are filters per voice or after the voice combiner in the original? (Reaktor report.)
    **[open]**
12. Does freezing include `require`d `.genexpr` files, and does the frozen device run on a
    machine without the source folder? **[open]**
13. CPU of 5 voices in Live (Live CPU meter, gen~ `@cpumeasure 1`), poly~ vs mc.gen~. **[open]**
14. If RNBO is considered: does an exported-to-external RNBO device need signing for
    distribution, and is in-Max `rnbo~` 64-bit? **[open]**

---

## Sources

Local (read-only, this machine):

- Max 9.2.0 refpages: `/Applications/Max.app/Contents/Resources/C74/docs/refpages/msp-ref/`
  (`gen~`, `mc.gen~`, `poly~`, `thispoly~`, `buffer~`, `saw~`, `rect~`, `tri~`, `phasor~`,
  `cycle~`, `svf~`, `lores~`, `filtercoeff~`, `mc.noteallocator~`)
- Gen operator refpages: `/Applications/Max.app/Contents/Resources/C74/packages/Gen/docs/refpages/dsp/`
  (`peek`, `poke`, `sample`, `wave`, `lookup`, `interp`, `data`, `buffer`, `phasor`,
  `delay`, `history`, `fixdenorm`, `voice`, `voicecount`)
- Max 9.2.0 user guide: `/Applications/Max.app/Contents/Resources/C74/docs/userguide/content/`
  (`gen/_gen_overview`, `gen/gen~_operators`, `gen/gen_genexpr`, `polyphony`, `rnbo`,
  `javascript`, `mc/*`, `m4l/live_limitations`, `m4l/live_symbols`, `m4l/live_timing`,
  `m4l/live_parameters`, `m4l/live_freezing`, `m4l/live_midieffects`)
- RNBO 1.4.5 package: `/Applications/Max.app/Contents/Resources/C74/packages/RNBO/`
  (`package-info.json`, `LICENSE.txt`, `docs/refpages/max/rnbo~.maxref.xml`,
  `docs/refpages/rnbo/{rnbo_buffer~,rnbo_gen~,rnbo_param,rnbo_voice,rnbo_saw~,rnbo_rect~,rnbo_phasor~,rnbo_svf~,rnbo_peek~,rnbo_poke~,rnbo_codebox~}.maxref.xml`)
- Ableton devices: `~/Music/Ableton/Factory Packs/Max for Live Essentials/Max Instrument/Poli.amxd`,
  `…/Bass.amxd`; Live template `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max Instrument.amxd`
- User guide: `Max for Live mit Claude bauen.md` (this workbench)

Reaktor manuals (downloaded to scratch, read as text):

- Reaktor 5.5 Application Reference: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Reaktor_5_Application_Reference_English_01.pdf (ch. 3 Sample/Control Rate; ch. 9.2 Event Signals; ch. 11 Table Modules, 11.2.3, 11.2.4)
- Reaktor 5.5 Core Reference: https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/Reaktor_5_Core_Reference_English.pdf (p. 89 OBC precision; 5.5 Denormal Values; p. 133–134 Float Signals / FP Precision)

Online:

- RNBO and Max for Live: https://rnbo.cycling74.com/learn/rnbo-and-max-for-live
- RNBO polyphony: https://rnbo.cycling74.com/learn/rnbo-polyphony
- RNBO voice stealing modes: https://rnbo.cycling74.com/learn/voice-stealing-modes
- RNBO Minimal Export (`RNBO_USE_FLOAT32`): https://rnbo.cycling74.com/learn/minimal-export
- CDM, RNBO in JavaScript and Ableton Live (2023): https://cdm.link/2023/05/rnbo-in-javascript-and-ableton-live/
- Updated licence terms for Max-generated code: https://cycling74.com/forums/updated-license-terms-for-max-generated-code-for-export
- RNBO export licensing FAQ (HTTP 403 to fetcher, not read): https://support.cycling74.com/hc/en-us/articles/10730637742483-RNBO-Export-Licensing-FAQ
- Can I use RNBO in Max for Live (HTTP 403, not read): https://support.cycling74.com/hc/en-us/articles/10536073075219-Can-I-use-RNBO-in-Max-for-Live
- Forum, poke and peek in the same sample: https://cycling74.com/forums/gen-gods-poke-and-peek-in-same-sample
- Forum, gen~ in poly~ load time: https://cycling74.com/forums/gen-in-poly-take-a-long-time-to-load
- Forum, comparing gen and Reaktor Core: https://cycling74.com/forums/comparing-gen-and-reaktor-core-level
- Forum, poly object in gen codebox: https://cycling74.com/forums/implementing-poly-object-in-gen-codebox
- Forum, Gen~ Data object storage: https://cycling74.com/forums/topic/gen-data-object-storage
- Forum, fill data array only once at gen~ init: https://cycling74.com/forums/fill-data-array-only-once-at-gen~-init
- Forum, Gen~ efficiency comparison: https://cycling74.com/forums/gen-efficiency-comparison
- Forum, RNBO clicks when voice stealing: https://cycling74.com/forums/rnbo-clicks-when-voice-stealing
- Forum, using the "---" identifier in Gen: https://cycling74.com/forums/using-the-unique-identifier-in-gen
- Forum, buffers name conflicting between device instances: https://cycling74.com/forums/buffers-name-conflicting-in-instatiations-of-same-device
- Forum, Building Blocs - Reaktor to Max/Msp: https://cycling74.com/forums/building-blocs-reaktor-to-maxmsp
- NI forum, Core constants / 64-bit cells: https://community.native-instruments.com/discussion/comment/168818
- scsynth.org, Replicating Aliasing Synth: https://scsynth.org/t/replicating-aliasing-synth-a-gem-in-reaktors-user-library/9054
- fors-fm/lode: https://github.com/fors-fm/lode
- Yofiel synth and gen~ DSP library: https://cycling74.com/projects/yofiel-synth-and-gen~-dsp-library
- Husserl2: https://cycling74.com/projects/husserl2-polyphonic-synthesizer-download
- Live 12 manual, Max for Live: https://www.ableton.com/en/live-manual/12/max-for-live/
- Ableton, Recommended Max versions: https://help.ableton.com/hc/en-us/articles/209772305
